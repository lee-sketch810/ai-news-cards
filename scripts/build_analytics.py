"""
build_analytics.py — 아카이브 전체를 스캔해 엔티티·트렌드·검색 인덱스 생성 (P1, render 이후 실행)

결정론적 처리. public/data/cards-*.json 전부를 읽어:
  1) 각 카드에 entities(기업·모델) 태그를 주입해 카드 파일에 다시 씀
  2) public/data/entities.json  — 엔티티별 타임라인 {entity:[{date,headline,url,category,verification_status}]}
  3) public/data/trends.json    — 카테고리 빈도 + 엔티티 랭킹 + 기간
  4) public/data/search-index.json — 전체 카드 경량 인덱스(검색용)

사용법: python build_analytics.py
"""
from __future__ import annotations
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PUBLIC_DATA = HERE.parent / "public" / "data"
HTML = HERE.parent / "public" / "index.html"
START = "/* CARDS_DATA_START */"
END = "/* CARDS_DATA_END */"


def _reembed_latest(dates: list[str]) -> None:
    """엔티티 태그가 추가된 최신 에디션을 index.html에 다시 임베드 (홈 칩 반영)."""
    if not dates or not HTML.exists():
        return
    latest = max(dates)
    src = PUBLIC_DATA / f"cards-{latest}.json"
    if not src.exists():
        return
    payload = src.read_text(encoding="utf-8").strip()
    html = HTML.read_text(encoding="utf-8")
    if START not in html or END not in html:
        return
    block = f"{START}\n{payload}\n{END}"
    html = re.sub(re.escape(START) + r".*?" + re.escape(END),
                  lambda _: block, html, count=1, flags=re.DOTALL)
    HTML.write_text(html, encoding="utf-8")

# 엔티티 사전: 표준명 → 소문자 별칭(부분일치). 명명된 개체(기업·모델) 위주.
ENTITY_ALIASES = {
    "OpenAI": ["openai", "chatgpt"],
    "Anthropic": ["anthropic"],
    "Google": ["구글", "google", "deepmind", "알파벳", "alphabet"],
    "Microsoft": ["microsoft", "마이크로소프트", "github copilot", "copilot"],
    "Gemini": ["gemini"],
    "Claude": ["claude", "sonnet 5", "sonnet", "opus", "mythos", "fable"],
    "GPT": ["gpt-5", "gpt5", "gpt "],
    "NVIDIA": ["엔비디아", "nvidia"],
    "Qualcomm": ["퀄컴", "qualcomm"],
    "xAI": ["xai"],
    "Meta": ["메타", " meta "],
    "중국 오픈웨이트": ["deepseek", "오픈웨이트", "중국"],
}


def detect_entities(card: dict) -> list[str]:
    text = f" {card.get('headline','')} {card.get('summary','')} ".lower()
    found = []
    for name, aliases in ENTITY_ALIASES.items():
        if any(a in text for a in aliases):
            found.append(name)
    return found


def main() -> int:
    files = sorted(PUBLIC_DATA.glob("cards-*.json"))
    timelines: dict[str, list] = defaultdict(list)
    ent_counter: Counter = Counter()
    cat_counter: Counter = Counter()
    search_index: list = []
    dates = []
    total_cards = 0

    for p in files:
        d = json.loads(p.read_text(encoding="utf-8"))
        date = d.get("date")
        if not date:
            continue
        dates.append(date)
        changed = False
        for c in d.get("cards", []):
            ents = detect_entities(c)
            if c.get("entities") != ents:
                c["entities"] = ents
                changed = True
            total_cards += 1
            cat_counter[c.get("category", "기타")] += 1
            for e in ents:
                ent_counter[e] += 1
                timelines[e].append({
                    "date": date,
                    "headline": c.get("headline", ""),
                    "url": c.get("source_url", ""),
                    "category": c.get("category", ""),
                    "verification_status": c.get("verification_status", ""),
                })
            search_index.append({
                "date": date,
                "category": c.get("category", ""),
                "headline": c.get("headline", ""),
                "summary": c.get("summary", ""),
                "insight": c.get("insight", ""),
                "url": c.get("source_url", ""),
                "source_name": c.get("source_name", ""),
                "entities": ents,
            })
        if changed:
            p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    # 타임라인 최신순 정렬
    for e in timelines:
        timelines[e].sort(key=lambda x: x["date"], reverse=True)

    (PUBLIC_DATA / "entities.json").write_text(
        json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(),
                    "timelines": timelines}, ensure_ascii=False, indent=2), encoding="utf-8")

    trends = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period": f"{min(dates)} ~ {max(dates)}" if dates else "",
        "total_editions": len(dates),
        "total_cards": total_cards,
        "by_category": dict(cat_counter.most_common()),
        "top_entities": [{"name": n, "count": c} for n, c in ent_counter.most_common(10)],
    }
    (PUBLIC_DATA / "trends.json").write_text(
        json.dumps(trends, ensure_ascii=False, indent=2), encoding="utf-8")

    search_index.sort(key=lambda x: x["date"], reverse=True)
    (PUBLIC_DATA / "search-index.json").write_text(
        json.dumps(search_index, ensure_ascii=False), encoding="utf-8")

    _reembed_latest(dates)

    print(f"analytics: {total_cards} cards, {len(timelines)} entities, "
          f"{len(dates)} editions. top: "
          + ", ".join(f"{e['name']}({e['count']})" for e in trends['top_entities'][:5]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
