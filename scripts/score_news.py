"""
score_news.py v2 — 실행가능성(actionability) 중심 점수 재설계 (P1 Pre-processing, Step 3)

v1의 문제
---------
v1 '실용성' 축은 명사 매칭이었다: tool/agent/automation/api/워크플로우...
그래서 "AI 에이전트 스타트업, 시리즈B 3억달러 유치" 같은 기사도 실용성 만점을 받았다.
실제로 기사를 읽어 팁을 뽑을 수 있느냐와 점수가 무관했다.

v2 핵심
-------
1. 축을 4개로 재편.  실행가능성 0.45 / 중요도 0.20 / 관련성 0.20 / 신선도 0.15
2. 실행가능성은 '형식 신호'로 측정한다 — how to / step by step / changelog /
   settings / template / 사용법 / 설정법처럼 "단계가 적혀 있을 법한 글"의 신호.
3. 결정적 신호는 키워드가 아니라 date-verifier가 본문에서 뽑아온 `actionable_facts`다.
   UI 경로·명령어·숫자·요구조건·프롬프트 문구가 실제로 몇 개 있는지가 팁 가능 여부를
   그대로 결정한다. 개수당 +12, 최대 +36.
4. `tip_eligible` 하드 플래그를 붙인다. actionable_facts가 2개 미만이면 팁 카드가 될 수
   없다. news-scorer는 이 플래그를 뒤집을 수 없다.
5. 거시 뉴스는 감점이 아니라 별도 레인(signal)으로 보낸다. 감점만 하면 결국 상위에
   섞여 올라와 팁 슬롯을 잡아먹는다.

사용법: python score_news.py --in verified.json --out scored.json [--today 2026-09-18]
"""
from __future__ import annotations
import argparse
import json
import re
from datetime import date as _date, datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

# ---------------------------------------------------------------------------
# 축 1. 실행가능성 — "이 글에 단계가 적혀 있는가"의 형식 신호
# ---------------------------------------------------------------------------
ACTIONABLE_KW = {
    # 글의 형식 자체가 how-to임을 알리는 신호 (가장 강함)
    "how to": 34, "step by step": 32, "step-by-step": 32, "tutorial": 30,
    "walkthrough": 28, "guide": 24, "checklist": 26, "recipe": 22,
    "사용법": 34, "설정법": 32, "따라 하기": 30, "가이드": 24, "체크리스트": 26,
    "꿀팁": 30, "활용법": 30, "방법": 20,
    # 제품 변경을 구체적으로 나열하는 문서
    "changelog": 32, "release notes": 32, "what's new": 28, "patch notes": 28,
    "업데이트 내역": 28, "릴리스 노트": 30,
    # 실제 조작 대상이 언급되는 신호
    "setting": 24, "settings": 24, "enable": 22, "disable": 22, "toggle": 24,
    "shortcut": 22, "command": 22, "config": 22, "install": 20, "opt out": 26,
    "설정": 24, "켜기": 20, "끄기": 20, "단축키": 22, "명령어": 22,
    # 복붙 가능한 산출물
    "template": 26, "prompt": 24, "example": 18, "snippet": 22, "boilerplate": 20,
    "템플릿": 26, "프롬프트": 24, "예시": 18,
    # 수치가 실려 있을 법한 신호
    "pricing": 22, "free tier": 26, "rate limit": 24, "quota": 22, "benchmark": 16,
    "요금": 22, "무료": 18, "한도": 24,
}

# ---------------------------------------------------------------------------
# 축 2. 중요도 — 업계 파급 (비중 축소: 0.3 -> 0.2)
# ---------------------------------------------------------------------------
IMPORTANCE_KW = {
    "release": 26, "launch": 26, "unveil": 24, "announce": 18, "gpt": 22,
    "claude": 22, "gemini": 22, "model": 16, "deprecat": 24, "sunset": 22,
    "출시": 26, "공개": 22, "발표": 18, "종료": 22,
}

# ---------------------------------------------------------------------------
# 축 3. 관련성 — 1인 실무자 / 교육·콘텐츠 제작자 독자층
# ---------------------------------------------------------------------------
RELEVANCE_KW = {
    "e-learning": 30, "education": 24, "instructional design": 30, "lms": 22,
    "productivity": 24, "solo": 22, "freelance": 22, "small business": 20,
    "content": 20, "video": 18, "writing": 18, "coding": 20, "developer": 18,
    "openai": 18, "anthropic": 20, "notion": 18, "obsidian": 16,
    "이러닝": 30, "교수설계": 30, "교육": 24, "생산성": 24, "콘텐츠": 20,
    "1인": 22, "실무": 24, "직장인": 20,
}

# ---------------------------------------------------------------------------
# 거시 신호 — 감점이 아니라 레인 분리용. 여기 걸리면 tier가 signal로 강등된다.
# ---------------------------------------------------------------------------
MACRO_KW = {
    "funding round", "series a", "series b", "series c", "raises $", "valuation",
    "ipo", "stock", "shares", "market cap", "acquisition talks", "lawsuit",
    "antitrust", "export control", "trade war", "geopolit", "tariff",
    "earnings", "revenue forecast", "데이터센터 투자", "투자유치", "지분",
    "주가", "소송", "규제안", "수출통제", "관세",
}

SOURCE_AUTHORITY = {
    # 1차 출처(공식 문서/체인지로그)는 실행 정보 밀도가 높아 실행가능성에 가산한다.
    "docs.": 14, "help.": 14, "/changelog": 16, "/release-notes": 16,
    "anthropic.com": 12, "openai.com": 12, "blog.google": 10, "microsoft.com": 8,
    "github.com": 10, "developers.": 12,
}
# 종합 뉴스 와이어는 흐름에는 좋지만 실행 정보는 거의 없다.
WIRE_DOMAINS = ("apnews.com", "reuters.com", "bloomberg.com", "cnbc.com",
                "ft.com", "wsj.com", "nytimes.com", "yna.co.kr")

WEIGHTS = {"actionable": 0.45, "importance": 0.20, "relevance": 0.20, "freshness": 0.15}

FACT_KEYS = ("ui_path", "commands", "numbers", "requirements", "prompt_snippets")
MIN_FACTS_FOR_TIP = 2


def _axis(text: str, table: dict) -> int:
    s = text.lower()
    return sum(w for kw, w in table.items() if kw in s)


def _count_facts(art: dict) -> int:
    facts = art.get("actionable_facts") or {}
    return sum(len(facts.get(k) or []) for k in FACT_KEYS)


def _freshness(art: dict, today: _date) -> int:
    vd = art.get("verified_date")
    if not vd:
        return 0
    try:
        d = datetime.strptime(vd, "%Y-%m-%d").date()
    except ValueError:
        return 0
    delta = (today - d).days
    if delta <= 0:
        return 100
    if delta == 1:
        return 80
    if delta == 2:
        return 50
    return max(0, 50 - (delta - 2) * 20)


def score_article(art: dict, today: _date) -> dict:
    text = f"{art.get('title','')} {art.get('snippet','')} {art.get('body_excerpt','')}"
    url = (art.get("url") or "").lower()

    n_facts = _count_facts(art)
    fact_bonus = min(36, n_facts * 12)

    act = _axis(text, ACTIONABLE_KW) + fact_bonus
    act += sum(w for d, w in SOURCE_AUTHORITY.items() if d in url)
    if any(d in url for d in WIRE_DOMAINS):
        act -= 20  # 와이어 기사는 실행 정보 밀도가 낮다

    imp = _axis(text, IMPORTANCE_KW)
    rel = _axis(text, RELEVANCE_KW)
    fre = _freshness(art, today)

    # 본문에 숫자가 아예 없으면 팁으로 쓸 임계값/한도/시간이 없다는 뜻
    if not re.search(r"\d", text):
        act -= 15

    macro_hits = [k for k in MACRO_KW if k in text.lower()]

    clamp = lambda v: max(0, min(100, v))
    act_n, imp_n, rel_n = clamp(act), clamp(imp), clamp(rel)

    total = round(
        act_n * WEIGHTS["actionable"]
        + imp_n * WEIGHTS["importance"]
        + rel_n * WEIGHTS["relevance"]
        + fre * WEIGHTS["freshness"],
        1,
    )

    # 레인 결정. 팁 슬롯에 들어갈 수 있는지를 여기서 못 박는다.
    if n_facts >= MIN_FACTS_FOR_TIP and not macro_hits:
        lane = "tip"
    elif n_facts >= 1 and not macro_hits:
        lane = "tool"
    else:
        lane = "signal"

    art["signals"] = {
        "actionable": act_n,
        "importance": imp_n,
        "relevance": rel_n,
        "freshness": fre,
        "actionable_fact_count": n_facts,
        "macro_hits": macro_hits[:5],
    }
    art["score"] = max(0.0, total)
    art["lane"] = lane
    art["tip_eligible"] = lane == "tip"
    return art


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument("--out", dest="out_path", required=True)
    ap.add_argument("--today", dest="today", help="YYYY-MM-DD (KST) override")
    args = ap.parse_args()

    today = (datetime.strptime(args.today, "%Y-%m-%d").date()
             if args.today else datetime.now(KST).date())

    with open(args.in_path, encoding="utf-8") as f:
        data = json.load(f)

    arts = [score_article(a, today) for a in data.get("articles", [])]
    # 레인 우선 정렬: tip > tool > signal, 레인 안에서 점수순
    lane_rank = {"tip": 0, "tool": 1, "signal": 2}
    arts.sort(key=lambda a: (lane_rank[a["lane"]], -a["score"]))
    for i, a in enumerate(arts, 1):
        a["rank"] = i

    data["articles"] = arts
    data["scored_count"] = len(arts)
    data["lane_counts"] = {
        ln: sum(1 for a in arts if a["lane"] == ln) for ln in ("tip", "tool", "signal")
    }

    with open(args.out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    lc = data["lane_counts"]
    print(f"scored {len(arts)} articles. lanes: tip={lc['tip']} tool={lc['tool']} "
          f"signal={lc['signal']}")
    if lc["tip"] < 6:
        print(f"WARN: tip-eligible only {lc['tip']} (<6). "
              f"팁 슬롯을 줄여 발행하고 signal로 채우지 말 것.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
