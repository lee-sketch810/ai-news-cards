"""
build_overview_input.py — 최근 N일 아카이브를 스캔해 주간 종합(overview.json)
작성에 필요한 재료를 결정론적으로 준비한다 (P1, build_analytics.py 이후 실행)

public/data/index.json에서 최신 에디션부터 거슬러 최근 --window일을 뽑아,
각 날짜의 daily_insight + 카테고리/엔티티 집계를 data/planning/overview-input.json에 씀.
집계(숫자)는 여기서 전부 계산 완료 — AI는 이 파일을 읽고 프로즈(제목·리드·4개 테마)만 작성한다.
overview.json 자체는 이 스크립트가 아니라 다음 단계(에이전트)가 WRITE한다 — 매일 실행해
절대 정체되지 않게 한다 (2026-08-01 발견된 정체 버그의 재발 방지).

사용법: python build_overview_input.py [--window 7]
"""
from __future__ import annotations
import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PUBLIC_DATA = HERE.parent / "public" / "data"
PLANNING = HERE.parent / "data" / "planning"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=7, help="집계할 최근 일수 (기본 7)")
    args = ap.parse_args()

    index_path = PUBLIC_DATA / "index.json"
    if not index_path.exists():
        print("overview-input: public/data/index.json 없음 — 먼저 render_cards.py 실행 필요")
        return 1
    index = json.loads(index_path.read_text(encoding="utf-8"))
    dates = sorted(e["date"] for e in index.get("editions", []))[-args.window:]
    if not dates:
        print("overview-input: 에디션 0건 — 스킵")
        return 0

    cat_counter: Counter = Counter()
    ent_counter: Counter = Counter()
    daily_insights: list[dict] = []

    for date in dates:
        p = PUBLIC_DATA / f"cards-{date}.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        di = d.get("daily_insight") or {}
        if di.get("title") or di.get("body"):
            daily_insights.append({"date": date, "title": di.get("title", ""), "body": di.get("body", "")})
        for c in d.get("cards", []):
            cat_counter[c.get("category", "기타")] += 1
            for e in c.get("entities", []):
                ent_counter[e] += 1

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_days": args.window,
        "period": f"{dates[0]} ~ {dates[-1]}",
        "by_category": dict(cat_counter.most_common()),
        "top_entities": [{"name": n, "count": c} for n, c in ent_counter.most_common(8)],
        "daily_insights": daily_insights,
    }

    PLANNING.mkdir(parents=True, exist_ok=True)
    out = PLANNING / "overview-input.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"overview-input: {len(daily_insights)} daily insights over {payload['period']} "
          f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
