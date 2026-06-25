"""
build_queries.py — 실행 KST 날짜를 주입한 8앵글 WebSearch 쿼리 세트 생성 (P1 Pre-processing, Step 1)

@news-collector가 이 출력을 받아 각 쿼리를 WebSearch로 실행한다.
placeholder 날짜 금지 — 항상 실행 시각의 KST 날짜를 주입한다.

사용법: python build_queries.py [--out queries.json]
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

ANGLES = [
    ("model-release", "AI", "OpenAI Anthropic Google new model release announcement {date}"),
    ("agent-automation", "자동화·에이전트", "AI agent automation tool launch {date} latest"),
    ("edu-productivity", "교육·생산성", "AI education productivity tool {date} e-learning"),
    ("korea-ai", "국내 AI", "인공지능 AI 한국 발표 출시 {kdate}"),
    ("policy", "AI 정책", "AI regulation policy governance {date}"),
    ("bigtech", "빅테크", "NVIDIA chip big tech AI {date}"),
    ("workflow", "워크플로우", "AI workflow LLM developer tool {date} release"),
    ("global", "글로벌 AI", "artificial intelligence news biggest stories {date}"),
]


def build(now_kst: datetime | None = None) -> dict:
    now_kst = now_kst or datetime.now(KST)
    date_en = now_kst.strftime("%B %d, %Y")           # June 25, 2026
    kdate = now_kst.strftime("%Y년 %m월 %d일")
    queries = [
        {"angle": a, "category": cat, "query": tmpl.format(date=date_en, kdate=kdate)}
        for a, cat, tmpl in ANGLES
    ]
    return {
        "generated_at": now_kst.isoformat(),
        "date": now_kst.date().isoformat(),
        "queries": queries,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", dest="out_path")
    args = ap.parse_args()
    data = build()
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if args.out_path:
        with open(args.out_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"{len(data['queries'])} queries for {data['date']} -> {args.out_path}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
