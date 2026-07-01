"""
build_threads.py — 여러 날짜에 걸쳐 반복 등장하는 주제를 스레드로 묶어
"이 소식의 그 후"를 추적한다 (P1, build_analytics.py 이후 실행)

curated 토픽 사전으로 카드를 분류하고(엔티티보다 세분화된 '사건' 단위),
같은 토픽이 서로 다른 날짜에 2회 이상 등장하면 하나의 스레드로 묶는다.
각 카드 파일에 thread_ids를 주입하고, public/data/threads.json에 진행상황을 기록한다.

사용법: python build_threads.py
"""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PUBLIC_DATA = HERE.parent / "public" / "data"

# 토픽 사전 — 신규 사건이 등장하면 여기에 항목만 추가하면 자동으로 스레드화된다.
TOPICS = {
    "gpt-5.6": {"label": "GPT-5.6 출시 여정", "aliases": ["gpt-5.6", "gpt5.6"]},
    "gemini-3.5-pro": {"label": "Gemini 3.5 Pro 출시 지연", "aliases": ["gemini 3.5 pro"]},
    "deepmind-exodus": {"label": "구글 DeepMind 인재 유출", "aliases": ["deepmind", "인재 이탈", "인재 유출"]},
    "claude-access": {"label": "Claude 모델 접근 제한·복원", "aliases": ["mythos", "fable 5"]},
}


def match_topics(card: dict) -> list[str]:
    text = f" {card.get('headline','')} {card.get('summary','')} ".lower()
    return [k for k, t in TOPICS.items() if any(a in text for a in t["aliases"])]


def main() -> int:
    files = sorted(PUBLIC_DATA.glob("cards-*.json"))
    buckets: dict[str, list] = {k: [] for k in TOPICS}

    for p in files:
        d = json.loads(p.read_text(encoding="utf-8"))
        date = d.get("date")
        if not date:
            continue
        changed = False
        for c in d.get("cards", []):
            keys = match_topics(c)
            if c.get("thread_ids") != keys:
                c["thread_ids"] = keys
                changed = True
            for k in keys:
                buckets[k].append({
                    "date": date,
                    "headline": c.get("headline", ""),
                    "summary": c.get("summary", ""),
                    "url": c.get("source_url", ""),
                    "category": c.get("category", ""),
                })
        if changed:
            p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    threads = []
    for k, items in buckets.items():
        dates = sorted(set(i["date"] for i in items))
        if len(dates) < 2:  # 서로 다른 날짜 2회 이상 등장해야 '스레드'
            continue
        items.sort(key=lambda x: x["date"])
        threads.append({
            "id": k,
            "label": TOPICS[k]["label"],
            "first_seen": dates[0],
            "last_seen": dates[-1],
            "count": len(items),
            "entries": items,
        })
    threads.sort(key=lambda t: t["last_seen"], reverse=True)

    (PUBLIC_DATA / "threads.json").write_text(
        json.dumps({"threads": threads}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"threads: {len(threads)} multi-day topics -> "
          + ", ".join(f"{t['label']}({t['count']})" for t in threads))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
