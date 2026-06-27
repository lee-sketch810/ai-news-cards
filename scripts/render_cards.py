"""
render_cards.py — cards JSON을 정적 사이트에 발행 + 매니페스트 생성 (P1 Pre-processing, Step 6)

동작:
  1) 최신 카드를 public/index.html 마커 사이에 주입 (즉시 페인트 + SEO + 오프라인)
  2) public/data/cards-<date>.json 으로 발행 (날짜별 아카이브 — Pages가 서빙)
  3) public/data/index.json 매니페스트 재생성 (날짜 목록 + 카드수 + 대표 헤드라인)

public/ 전체가 GitHub Pages로 배포되므로 아카이브 데이터도 같은 오리진에서 fetch 가능.
re.sub는 lambda로 치환(백슬래시 오염 방지).

사용법: python render_cards.py --cards data/cards-2026-06-25.json
"""
from __future__ import annotations
import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                          # ai-news-cards/
HTML = ROOT / "public" / "index.html"
PUBLIC_DATA = ROOT / "public" / "data"      # Pages가 서빙하는 발행 데이터

START = "/* CARDS_DATA_START */"
END = "/* CARDS_DATA_END */"


def _build_manifest() -> dict:
    """public/data/cards-*.json 을 스캔해 날짜 매니페스트 생성."""
    editions = []
    for p in sorted(PUBLIC_DATA.glob("cards-*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        cards = d.get("cards", [])
        if not d.get("date") or not cards:
            continue
        editions.append({
            "date": d["date"],
            "count": len(cards),
            "top_headline": cards[0].get("headline", ""),
        })
    editions.sort(key=lambda e: e["date"], reverse=True)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "latest": editions[0]["date"] if editions else None,
        "editions": editions,
    }


def inject(cards_path: Path) -> dict:
    cards = json.loads(cards_path.read_text(encoding="utf-8"))
    n = len(cards.get("cards", []))
    date = cards.get("date", "unknown")

    # 1) 발행 데이터로 복사 (서빙용)
    PUBLIC_DATA.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(cards_path, PUBLIC_DATA / f"cards-{date}.json")

    # 2) 매니페스트 재생성
    manifest = _build_manifest()
    (PUBLIC_DATA / "index.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # 3) 최신 에디션만 index.html에 임베드 (즉시 페인트 + SEO)
    if not HTML.exists():
        raise FileNotFoundError(f"template not found: {HTML}")
    html = HTML.read_text(encoding="utf-8")
    if START not in html or END not in html:
        raise ValueError("CARDS_DATA markers not found in index.html")
    if date == manifest["latest"]:
        payload = json.dumps(cards, ensure_ascii=False)
        block = f"{START}\n{payload}\n{END}"
        html = re.sub(re.escape(START) + r".*?" + re.escape(END),
                      lambda _: block, html, count=1, flags=re.DOTALL)
        HTML.write_text(html, encoding="utf-8")

    return {"cards": n, "date": date, "latest": manifest["latest"],
            "editions": len(manifest["editions"])}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cards", required=True)
    args = ap.parse_args()
    res = inject(Path(args.cards))
    print(f"published {res['cards']} cards (date={res['date']}); "
          f"latest={res['latest']}; archive editions={res['editions']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
