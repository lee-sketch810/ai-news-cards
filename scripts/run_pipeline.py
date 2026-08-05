"""
run_pipeline.py — GitHub Actions 전용 오케스트레이터.

기존에는 PC에서 돌아가는 Claude Code 세션이 news-collector / date-verifier /
news-scorer / card-writer 4개 sub-agent를 오케스트레이션했다. 그 세션이 며칠째
꺼져 있어서 사이트 업데이트가 멈췄던 것이 이번 작업의 발단이다.

이 스크립트는 그 역할을 로컬 PC 세션 없이 GitHub Actions(클라우드) 안에서
전부 끝내기 위한 대체 오케스트레이터다. 원래 파이프라인의 데이터 계약
(data/research/candidates-*.json → verified-*.json → data/planning/top10-*.json
→ data/cards-*.json)은 그대로 유지해서, 기존 스크립트(dedupe.py, verify_dates.py,
score_news.py, render_cards.py, build_analytics.py, build_threads.py)를 손대지
않고 그대로 재사용한다.

역할 대체 방식:
  - news-collector (WebSearch)  → Anthropic Messages API의 서버사이드 web_search
    도구 1회 호출로 8개 앵글을 모두 검색시키고, 구조화 출력용 커스텀 tool
    (submit_candidates)을 강제 호출하게 해서 JSON을 받는다.
  - date-verifier (WebFetch)    → LLM 없이 순수 Python(requests)으로 각 URL의
    article:published_time / JSON-LD datePublished / og:updated_time 메타태그를
    직접 파싱한다. 결정론적이고 비용이 들지 않으며, 실패하면 보수적으로 탈락시키는
    원래 설계 철학과도 맞는다.
  - news-scorer (Top10 선정)     → score_news.py는 그대로 쓰고, "카테고리당 최대
    절반" 규칙은 Python으로 결정론적으로 적용한다(LLM 호출 없음 — 더 안정적).
  - card-writer (카드 작성)      → 이건 실제 '품질'이 나오는 유일한 단계라서 LLM이
    반드시 필요하다. card-writer.md의 지시문을 system prompt로 그대로 이식하고,
    구조화 출력용 커스텀 tool(submit_cards)을 강제 호출하게 한다.

주의: web_search 도구 스키마·모델 ID는 Anthropic이 계속 갱신한다. 이 스크립트는
2026-08 시점 공식 문서 기준(web_search_20250305 / claude-sonnet-5 / claude-opus-5)
으로 작성했다. 처음 한 번은 반드시 GitHub Actions의 "Run workflow"(workflow_dispatch)
버튼으로 수동 실행해서 정상 동작을 확인한 뒤 매일 자동 스케줄에 맡길 것.

환경변수: ANTHROPIC_API_KEY (필수)
사용법: python scripts/run_pipeline.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

try:
    import anthropic
except ImportError:
    print("pip install anthropic 필요", file=sys.stderr)
    raise

ROOT = Path(__file__).resolve().parent.parent
KST = timezone(timedelta(hours=9))

MODEL_SEARCH = "claude-sonnet-5"   # 수집 단계 — 속도·비용 우선
MODEL_WRITE = "claude-opus-5"      # 카드 작성 단계 — 품질 우선 (card-writer.md와 동일)

client = anthropic.Anthropic()


def now_kst() -> datetime:
    return datetime.now(KST)


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=ROOT)


# ---------------------------------------------------------------------------
# Step 1 — 수집 (news-collector 대체): Claude web_search 도구
# ---------------------------------------------------------------------------

SUBMIT_CANDIDATES_TOOL = {
    "name": "submit_candidates",
    "description": "수집한 후보 기사 전체를 한 번에 제출한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "articles": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "url": {"type": "string", "description": "실제 기사 URL (검색결과 페이지 금지)"},
                        "snippet": {"type": "string"},
                        "source": {"type": "string", "description": "매체명"},
                        "category": {"type": "string"},
                        "snippet_date": {"type": ["string", "null"]},
                    },
                    "required": ["title", "url", "snippet", "source", "category"],
                },
            }
        },
        "required": ["articles"],
    },
}


def collect_candidates(queries: list[dict]) -> list[dict]:
    query_lines = "\n".join(f"- [{q['category']}] {q['query']}" for q in queries)
    prompt = f"""당신은 매일 한국어 AI 뉴스 카드 사이트를 위한 뉴스 수집 담당자입니다.
아래 8개 검색 앵글 각각에 대해 web_search 도구로 반드시 검색을 수행하세요
(앵글 하나당 최소 1회, 결과가 부실하면 추가 검색).

{query_lines}

규칙:
- 실제 기사 URL만 수집한다. 검색결과 페이지·홈페이지·플레이스홀더 URL 금지.
- 총 25건 이상 과다수집한다(중복·품질 필터링은 다음 단계가 처리). 아직 요약·평가하지 않는다.
- 각 기사는 검색결과 스니펫에 날짜가 보이면 snippet_date에 담고, 없으면 null.
- 8개 앵글을 모두 검색한 뒤, 반드시 submit_candidates 도구를 호출해서 결과를 제출한다.
  일반 텍스트로 답하지 말 것 — 마지막 행동은 항상 submit_candidates 호출이어야 한다."""

    tools = [
        {"type": "web_search_20250305", "name": "web_search", "max_uses": 20},
        SUBMIT_CANDIDATES_TOOL,
    ]
    messages = [{"role": "user", "content": prompt}]

    resp = client.messages.create(
        model=MODEL_SEARCH, max_tokens=8000, tools=tools, messages=messages,
    )

    submit = next((b for b in resp.content if getattr(b, "type", None) == "tool_use"
                   and b.name == "submit_candidates"), None)

    if submit is None:
        # 폴백: 검색은 했는데 submit_candidates를 안 불렀으면 한 번 더 강제로 요청
        messages.append({"role": "assistant", "content": resp.content})
        messages.append({"role": "user", "content": "지금까지 찾은 것을 전부 submit_candidates로 제출하세요."})
        resp2 = client.messages.create(
            model=MODEL_SEARCH, max_tokens=8000,
            tools=tools, tool_choice={"type": "tool", "name": "submit_candidates"},
            messages=messages,
        )
        submit = next((b for b in resp2.content if getattr(b, "type", None) == "tool_use"), None)

    if submit is None:
        print("경고: submit_candidates 호출을 받지 못함 — 후보 0건으로 진행")
        return []

    return submit.input.get("articles", [])


# ---------------------------------------------------------------------------
# Step 2 — 발행일 검증 (date-verifier 대체): LLM 없이 순수 HTTP + 정규식
# ---------------------------------------------------------------------------

UA = "Mozilla/5.0 (compatible; ai-news-cards-bot/1.0; +https://ai-news.wiselab.kr)"

DATE_PATTERNS = [
    re.compile(r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)', re.I),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']article:published_time["\']', re.I),
    re.compile(r'"datePublished"\s*:\s*"([^"]+)"', re.I),
    re.compile(r'<meta[^>]+property=["\']og:updated_time["\'][^>]+content=["\']([^"\']+)', re.I),
    re.compile(r'<meta[^>]+name=["\']publish-date["\'][^>]+content=["\']([^"\']+)', re.I),
    re.compile(r'<time[^>]+datetime=["\']([^"\']+)', re.I),
]


def fetch_published_date(url: str) -> str | None:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=12)
        if r.status_code >= 400:
            return None
        html = r.text[:200_000]  # <head> 근처면 충분, 대용량 페이지 방어
        for pat in DATE_PATTERNS:
            m = pat.search(html)
            if m:
                return m.group(1).strip()
    except requests.RequestException as e:
        print(f"  fetch 실패 ({url}): {e}")
    return None


def verify_publish_dates(articles: list[dict]) -> list[dict]:
    for art in articles:
        art["raw_published"] = fetch_published_date(art.get("url", "")) or art.get("snippet_date")
        time.sleep(0.3)  # 매너 있는 크롤링
    return articles


# ---------------------------------------------------------------------------
# Step 3 — Top10 선정 (news-scorer 대체): 결정론적 카테고리 균형
# ---------------------------------------------------------------------------

def select_top10(scored_articles: list[dict], k: int = 10) -> list[dict]:
    cap = max(1, k // 2)  # "한 카테고리가 절반을 넘지 않는다"
    by_score = sorted(scored_articles, key=lambda a: a.get("score", 0), reverse=True)
    selected: list[dict] = []
    cat_count: Counter = Counter()
    skipped: list[dict] = []
    for art in by_score:
        if len(selected) >= k:
            break
        cat = art.get("category", "기타")
        if cat_count[cat] >= cap:
            skipped.append(art)
            continue
        selected.append(art)
        cat_count[cat] += 1
    # 자리가 남았는데 전부 스킵된 것뿐이면(카테고리 다양성이 부족한 날) 채워 넣는다
    for art in skipped:
        if len(selected) >= k:
            break
        selected.append(art)
    return selected[:k]


# ---------------------------------------------------------------------------
# Step 4 — 카드 작성 (card-writer 대체): Claude 구조화 출력
# ---------------------------------------------------------------------------

CARD_WRITER_SYSTEM = """You write daily AI-news cards in native Korean. This is the product's quality core.

Canonical categories (assign each card to exactly one, by TOPIC — every item is AI
news, so never use a generic "AI" category or a geographic one like 국내/글로벌):
모델·연구 / 에이전트·자동화 / 도구·개발 / 교육·생산성 / 산업·투자 / 정책·규제

For each selected article, write one card object:
- category — one of the six canonical categories above, chosen by the article's topic.
- verified_date — absolute YYYY-MM-DD (given to you). NEVER a relative expression.
- verification_status — passed | yesterday (given to you, copy through).
- headline — catchy, accurate Korean headline (not a literal translation).
- summary — one Korean sentence: what happened.
- points — exactly 3 key Korean bullet points.
- insight — a UNIVERSAL "왜 중요한가" insight: an industry implication or general
  lesson for any practitioner. ABSOLUTELY NOT personalized — never "그래서 나에게",
  never address a specific user, never reference a specific person's projects.
- source_url — the given real URL, unchanged. source_name — the outlet.

After the cards, write ONE daily_insight that synthesizes the whole day:
- daily_insight.title — a short, punchy Korean headline naming the day's overarching theme.
- daily_insight.body — 2-3 Korean sentences reading ACROSS all the cards: what single
  current ties them together and why it matters. Not a list, not a summary of one story —
  a macro takeaway. Universal tone (no personalization).

Rules:
- Native Korean, sales-copy-level naturalness. No translationese.
- No relative date words anywhere ("어제", "오늘", "N일 전") in card or insight text.
- You MUST finish by calling the submit_cards tool. Never answer in plain text."""

SUBMIT_CARDS_TOOL = {
    "name": "submit_cards",
    "description": "완성된 카드 전체와 오늘의 종합 인사이트를 제출한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "daily_insight": {
                "type": "object",
                "properties": {"title": {"type": "string"}, "body": {"type": "string"}},
                "required": ["title", "body"],
            },
            "cards": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string"},
                        "verified_date": {"type": "string"},
                        "verification_status": {"type": "string"},
                        "headline": {"type": "string"},
                        "summary": {"type": "string"},
                        "points": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 3},
                        "insight": {"type": "string"},
                        "source_url": {"type": "string"},
                        "source_name": {"type": "string"},
                    },
                    "required": ["category", "verified_date", "verification_status", "headline",
                                 "summary", "points", "insight", "source_url", "source_name"],
                },
            },
        },
        "required": ["daily_insight", "cards"],
    },
}


def domain_of(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


def write_cards(selected: list[dict]) -> dict:
    payload = [
        {
            "title": a.get("title"), "url": a.get("url"), "snippet": a.get("snippet"),
            "source": a.get("source") or domain_of(a.get("url", "")),
            "category_hint": a.get("category"),
            "verified_date": a.get("verified_date"),
            "verification_status": a.get("verification_status"),
        }
        for a in selected
    ]
    resp = client.messages.create(
        model=MODEL_WRITE,
        max_tokens=8000,
        system=CARD_WRITER_SYSTEM,
        tools=[SUBMIT_CARDS_TOOL],
        tool_choice={"type": "tool", "name": "submit_cards"},
        messages=[{"role": "user",
                   "content": "다음 Top10 기사로 카드를 작성하세요:\n" + json.dumps(payload, ensure_ascii=False, indent=2)}],
    )
    submit = next(b for b in resp.content if getattr(b, "type", None) == "tool_use")
    return submit.input


# ---------------------------------------------------------------------------
# 메인 파이프라인
# ---------------------------------------------------------------------------

def main() -> int:
    date = now_kst().date().isoformat()
    print(f"===== run_pipeline start ({date} KST) =====")

    research = ROOT / "data" / "research"
    planning = ROOT / "data" / "planning"
    research.mkdir(parents=True, exist_ok=True)
    planning.mkdir(parents=True, exist_ok=True)

    # Step 1: queries
    queries_path = research / "queries.json"
    run([sys.executable, "scripts/build_queries.py", "--out", str(queries_path)])
    queries = json.loads(queries_path.read_text(encoding="utf-8"))["queries"]

    # Step 1: collect
    print("-- collecting candidates via web_search --")
    articles = collect_candidates(queries)
    print(f"collected {len(articles)} raw candidates")
    if not articles:
        print("수집 0건 — on_collection_empty: 오늘은 발행을 보류합니다.")
        return 0

    candidates_path = research / f"candidates-{date}.json"
    candidates_path.write_text(
        json.dumps({"generated_at": now_kst().isoformat(), "date": date, "articles": articles},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    run([sys.executable, "scripts/dedupe.py", "--in", str(candidates_path), "--out", str(candidates_path)])

    # Step 2: verify dates
    print("-- verifying publish dates via HTTP fetch --")
    data = json.loads(candidates_path.read_text(encoding="utf-8"))
    data["articles"] = verify_publish_dates(data["articles"])
    candidates_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    verified_path = research / f"verified-{date}.json"
    run([sys.executable, "scripts/verify_dates.py", "--in", str(candidates_path),
         "--out", str(verified_path), "--window", "1"])
    verified = json.loads(verified_path.read_text(encoding="utf-8"))
    if verified["total_passed"] == 0:
        print("발행일 검증 통과 0건 — 오늘은 발행을 보류합니다.")
        return 0

    # Step 3: score + top10
    scored_path = planning / f"scored-{date}.json"
    run([sys.executable, "scripts/score_news.py", "--in", str(verified_path), "--out", str(scored_path)])
    scored = json.loads(scored_path.read_text(encoding="utf-8"))
    top10 = select_top10(scored["articles"], k=10)
    (planning / f"top10-{date}.json").write_text(
        json.dumps({"date": date, "selected": top10}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"top10 선정: {len(top10)}건 (검증통과 {verified['total_passed']}건 중)")

    # Step 4: write cards
    print("-- writing cards --")
    result = write_cards(top10)
    cards = result["cards"]
    for i, c in enumerate(cards, 1):
        c["rank"] = i
    cards_doc = {"date": date, "generated_at": now_kst().isoformat(),
                 "daily_insight": result["daily_insight"], "cards": cards}
    cards_path = ROOT / "data" / f"cards-{date}.json"
    cards_path.write_text(json.dumps(cards_doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"작성 완료: {len(cards)}장 -> {cards_path}")

    # Step 5: render + analytics + threads (순서 중요 — news-deployer.md와 동일)
    run([sys.executable, "scripts/render_cards.py", "--cards", str(cards_path)])
    run([sys.executable, "scripts/build_analytics.py"])
    run([sys.executable, "scripts/build_threads.py"])
    run([sys.executable, "scripts/build_analytics.py"])  # thread_ids 반영해 재임베드

    # Step 6 (best-effort): 주간 overview — 실패해도 파이프라인 전체를 막지 않는다
    try:
        run([sys.executable, "scripts/build_overview_input.py", "--window", "7"])
        _write_overview(date)
    except Exception as e:
        print(f"overview 갱신 실패(무시하고 계속): {e}")

    print("===== run_pipeline done =====")
    return 0


def _write_overview(date: str) -> None:
    overview_input_path = ROOT / "data" / "planning" / "overview-input.json"
    if not overview_input_path.exists():
        return
    payload = json.loads(overview_input_path.read_text(encoding="utf-8"))
    tool = {
        "name": "submit_overview",
        "description": "최근 N일 종합을 제출한다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"}, "lead": {"type": "string"},
                "themes": {"type": "array", "items": {
                    "type": "object",
                    "properties": {"k": {"type": "string"}, "v": {"type": "string"}},
                    "required": ["k", "v"]}, "minItems": 3, "maxItems": 4},
            },
            "required": ["title", "lead", "themes"],
        },
    }
    resp = client.messages.create(
        model=MODEL_SEARCH, max_tokens=2000,
        system="최근 일주일 AI 뉴스 종합을 자연스러운 한국어 프로즈로 작성한다. "
               "숫자·집계는 이미 계산되어 주어지며, 그대로 인용한다. 나열이 아니라 "
               "날짜를 관통하는 흐름을 짚는다. 반드시 submit_overview 도구를 호출한다.",
        tools=[tool], tool_choice={"type": "tool", "name": "submit_overview"},
        messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
    )
    submit = next(b for b in resp.content if getattr(b, "type", None) == "tool_use")
    out = {
        "updated": now_kst().isoformat(), "period": payload["period"],
        "title": submit.input["title"], "lead": submit.input["lead"],
        "themes": submit.input["themes"],
    }
    (ROOT / "public" / "data" / "overview.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"overview.json 갱신 완료 ({date} 기준)")


if __name__ == "__main__":
    raise SystemExit(main())
