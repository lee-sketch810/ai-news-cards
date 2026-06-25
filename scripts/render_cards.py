"""
render_cards.py — cards JSON을 정적 HTML에 주입 + 아카이브 (P1 Pre-processing, Step 6)

public/index.html 의 마커 사이에 카드 데이터(JSON)를 주입하고,
data/archive/cards-YYYY-MM-DD.json 으로 영구 보존한다.
inject_briefing.py 패턴 재사용. re.sub는 lambda로 치환(백슬래시 오염 방지).

사용법: python render_cards.py --cards ../data/cards-2026-06-25.json
"""
from __future__ import annotations
import argparse
import json
import re
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                         # ai-news-cards/
HTML = ROOT / "public" / "index.html"
ARCHIVE = ROOT / "data" / "archive"

START = "/* CARDS_DATA_START */"
END = "/* CARDS_DATA_END */"


def inject(cards_path: Path) -> dict:
    with open(cards_path, encoding="utf-8") as f:
        cards = json.load(f)
    n = len(cards.get("cards", []))
    if not HTML.exists():
        raise FileNotFoundError(f"template not found: {HTML}")
    html = HTML.read_text(encoding="utf-8")
    if START not in html or END not in html:
        raise ValueError("CARDS_DATA markers not found in index.html")

    payload = json.dumps(cards, ensure_ascii=False)
    block = f"{START}\n{payload}\n{END}"
    new_html = re.sub(
        re.escape(START) + r".*?" + re.escape(END),
        lambda _: block,                   # lambda — 백슬래시 오염 방지
        html, count=1, flags=re.DOTALL,
    )
    HTML.write_text(new_html, encoding="utf-8")

    ARCHIVE.mkdir(parents=True, exist_ok=True)
    date = cards.get("date", "unknown")
    dest = ARCHIVE / f"cards-{date}.json"
    shutil.copyfile(cards_path, dest)
    return {"cards": n, "date": date, "archived": str(dest)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cards", required=True)
    args = ap.parse_args()
    res = inject(Path(args.cards))
    print(f"injected {res['cards']} cards (date={res['date']}); archived -> {res['archived']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
