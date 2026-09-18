"""
build_queries.py v2 — 실전 팁 원재료를 겨냥한 2티어 쿼리 세트 생성 (P1 Pre-processing, Step 1)

v1 대비 변경점
--------------
v1은 12앵글이 전부 'news' 앵글(release / announcement / regulation)이었다.
그 결과 수집되는 원문에 메뉴 경로·설정값·명령어·한도 같은 "실행에 필요한 구체 정보"가
애초에 들어있지 않아, card-writer가 팁을 쓰려 해도 쓸 재료가 없었다.
(2026-09-14~16 실측: 팁 24건 중 16건이 "확인한다/점검한다/비교한다"로 끝나고,
 숫자+UI경로를 동시에 가진 팁은 0건)

v2는 앵글을 두 티어로 나눈다.
  - tier="practice" (10앵글): 체인지로그 / 릴리스노트 / how-to / 설정 가이드 /
    프롬프트 / 요금·한도 변경 / 한국어 실무글. 팁 카드의 원재료.
  - tier="signal"   (4앵글): 정책·산업·모델 발표. '흐름' 카드 2슬롯 전용.

수집량 목표도 티어별로 분리한다. practice 티어에서 최소 20건을 못 모으면
그날은 팁 카드 수를 줄이되, signal 티어로 억지 채우지 않는다.

사용법: python build_queries.py [--out queries.json] [--date YYYY-MM-DD]
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

# ---------------------------------------------------------------------------
# 표준 카테고리 — 고정 enum 8종. 자유 조합 금지.
# (2026-09 실측: 139카드에 고유 카테고리가 108종까지 늘어나 필터 UI와 트렌드 집계가
#  사실상 무력화됐다. render_cards.py가 이 enum 밖의 값을 만나면 빌드를 실패시킨다.)
# ---------------------------------------------------------------------------
CATEGORIES = [
    "프롬프트·활용",
    "도구·기능",
    "자동화·에이전트",
    "보안·프라이버시",
    "비용·요금제",
    "교육·학습설계",
    "콘텐츠·제작",
    "흐름·정책",
]

# (angle, tier, category_hint, query_template)
ANGLES = [
    # ---------------- practice tier: 팁의 원재료 ----------------
    # 체인지로그/릴리스노트는 기능 이름과 설정 경로가 문장 안에 그대로 들어있다.
    ("changelog-major", "practice", "도구·기능",
     "ChatGPT Claude Gemini Copilot changelog release notes new feature {date}"),
    ("changelog-tools", "practice", "도구·기능",
     "AI tool product update changelog \"what's new\" {date}"),
    # how-to / 튜토리얼 — 단계가 명시된 글
    ("howto-general", "practice", "프롬프트·활용",
     "how to use AI step by step guide tutorial {date}"),
    ("howto-workflow", "practice", "자동화·에이전트",
     "AI workflow setup guide automate repetitive task tutorial {date}"),
    # 프롬프트 — 복붙 가능한 실제 문장이 실려 있는 글
    ("prompt-craft", "practice", "프롬프트·활용",
     "prompt that works system prompt example template {date}"),
    # 설정/프라이버시 — 토글 이름과 메뉴 경로가 나오는 글
    ("privacy-settings", "practice", "보안·프라이버시",
     "AI privacy setting opt out training data turn off how to {date}"),
    # 요금/한도 — 숫자가 나오는 글
    ("pricing-limits", "practice", "비용·요금제",
     "AI pricing change free tier rate limit usage cap {date}"),
    # 교육·학습설계 실무
    ("edu-practice", "practice", "교육·학습설계",
     "AI instructional design e-learning course build practical guide {date}"),
    # 콘텐츠 제작 실무
    ("content-practice", "practice", "콘텐츠·제작",
     "AI video image content production workflow tips {date}"),
    # 한국어 실무글 — 국내 도구·요금·사용법
    ("kr-practice", "practice", "도구·기능",
     "AI 사용법 설정 꿀팁 실무 활용 {kdate}"),

    # ---------------- signal tier: 흐름 2슬롯 전용 ----------------
    ("model-release", "signal", "흐름·정책",
     "OpenAI Anthropic Google new model release announcement {date}"),
    ("policy", "signal", "흐름·정책",
     "AI regulation policy governance {date}"),
    ("industry", "signal", "흐름·정책",
     "NVIDIA chip big tech AI infrastructure {date}"),
    ("kr-signal", "signal", "흐름·정책",
     "인공지능 AI 한국 정책 발표 {kdate}"),
]

# 티어별 최소 수집 목표 — news-collector가 이 수치를 못 채우면 로그에 명시한다.
TIER_TARGETS = {"practice": 20, "signal": 6}

# 팁 카드 편성 쿼터 — news-scorer가 이 쿼터대로 슬롯을 채운다.
# 팁 슬롯은 actionable_facts가 부족하면 비워두고, signal로 대체하지 않는다.
SLOT_QUOTA = {
    "tip": {"slots": 6, "min_actionable_facts": 2},
    "tool": {"slots": 2, "min_actionable_facts": 1},
    "signal": {"slots": 2, "min_actionable_facts": 0},
}


def build(now_kst: datetime | None = None) -> dict:
    now_kst = now_kst or datetime.now(KST)
    date_en = now_kst.strftime("%B %d, %Y")            # September 18, 2026
    kdate = now_kst.strftime("%Y년 %m월 %d일")
    queries = [
        {
            "angle": a,
            "tier": tier,
            "category": cat,
            "query": tmpl.format(date=date_en, kdate=kdate),
        }
        for a, tier, cat, tmpl in ANGLES
    ]
    return {
        "generated_at": now_kst.isoformat(),
        "date": now_kst.date().isoformat(),
        "categories": CATEGORIES,
        "tier_targets": TIER_TARGETS,
        "slot_quota": SLOT_QUOTA,
        "queries": queries,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", dest="out_path")
    ap.add_argument("--date", dest="date", help="YYYY-MM-DD (KST) override for backfill runs")
    args = ap.parse_args()
    now_kst = None
    if args.date:
        target = datetime.strptime(args.date, "%Y-%m-%d")
        now_kst = target.replace(hour=9, tzinfo=KST)
    data = build(now_kst)
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if args.out_path:
        with open(args.out_path, "w", encoding="utf-8") as f:
            f.write(text)
        n_p = sum(1 for q in data["queries"] if q["tier"] == "practice")
        n_s = len(data["queries"]) - n_p
        print(f"{len(data['queries'])} queries for {data['date']} "
              f"(practice={n_p}, signal={n_s}) -> {args.out_path}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
