#!/usr/bin/env python3
"""cards-YYYY-MM-DD.json -> 나만의 나무위키 1_raw 용 마크다운 (결정론적, AI 판단 없음).

사용:
  python scripts/cards_to_wiki.py --cards data/cards-2026-11-22.json      # 변환
  python scripts/cards_to_wiki.py --pending                               # 미업로드 목록
  python scripts/cards_to_wiki.py --mark-uploaded 2026-11-22 <drive_file_id>

산출물: data/wiki_raw/news_YYYY-MM-DD.md (하루 1파일), data/wiki_raw/upload_manifest.json
하루 1파일 + 업로드 매니페스트로 중복·번호충돌을 막는다(Drive create_file은 덮어쓰지 않음).
"""
import argparse, json, re, sys
from pathlib import Path

OUT_DIR = Path("data/wiki_raw")
MANIFEST = OUT_DIR / "upload_manifest.json"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def load_manifest():
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {}


def save_manifest(m):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(m, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def clean(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def render_card(c):
    lines = []
    cat = clean(c.get("category"))
    lines.append(f"### {c.get('rank', '')}. {clean(c.get('headline'))}")
    meta = [x for x in (cat, c.get("verified_date")) if x]
    if meta:
        lines.append(f"*{' · '.join(map(str, meta))}*")
    lines.append("")
    if c.get("summary"):
        lines.append(clean(c["summary"]))
        lines.append("")
    for p in c.get("points") or []:
        lines.append(f"- {clean(p)}")
    tip = c.get("tip")
    if isinstance(tip, dict) and tip:
        lines += ["", f"**💡 실전 팁 — {clean(tip.get('goal'))}**"]
        for i, s in enumerate(tip.get("steps") or [], 1):
            lines.append(f"{i}. {clean(s)}")
        facts = [f"소요 {clean(tip['time'])}" if tip.get("time") else "",
                 f"적용 {clean(tip['applies_to'])}" if tip.get("applies_to") else "",
                 f"주의 {clean(tip['caveat'])}" if tip.get("caveat") else ""]
        facts = [f for f in facts if f]
        if facts:
            lines.append(f"> {' / '.join(facts)}")
    elif isinstance(tip, str) and tip.strip():  # v1 스키마 호환
        lines += ["", f"**💡 실전 팁** {clean(tip)}"]
    if c.get("so_what"):
        lines += ["", f"**So what** {clean(c['so_what'])}"]
    if c.get("insight"):
        lines += ["", f"**왜 중요한가** {clean(c['insight'])}"]
    url, name = c.get("source_url"), clean(c.get("source_name")) or "원문"
    if url:
        lines += ["", f"출처: [{name}]({url}) — {c.get('verified_date', '')}"]
    return "\n".join(lines)


def build(cards_path):
    d = json.loads(Path(cards_path).read_text(encoding="utf-8"))
    date = d.get("date", "")
    if not DATE_RE.match(date):
        sys.exit(f"invalid date in {cards_path}: {date!r}")
    cards = d.get("cards") or []
    if not cards:
        sys.exit(f"no cards in {cards_path}")
    cats = []
    for c in cards:
        k = clean(c.get("category"))
        if k and k not in cats:
            cats.append(k)
    ents = []
    for c in cards:
        for e in c.get("entities") or []:
            e = clean(e if isinstance(e, str) else e.get("name", ""))
            if e and e not in ents:
                ents.append(e)
    tags = ["ai-news"] + cats + ents[:8]
    di = d.get("daily_insight") or {}
    out = ["---",
           "tags: [" + ", ".join(t.replace(",", " ") for t in tags) + "]",
           "category: AI기술",
           f"created: {date}",
           "stage: raw",
           "source: ai-news-cards",
           f"cards: {len(cards)}",
           "---", "",
           f"# AI 뉴스 {date}", ""]
    if di:
        out += [f"## 오늘의 흐름 — {clean(di.get('title'))}", "", clean(di.get("body")), ""]
        if di.get("today_action"):
            out += [f"**오늘의 한 가지 행동:** {clean(di['today_action'])}", ""]
    out += ["## 카드", ""]
    for c in cards:
        out += [render_card(c), ""]
    out += ["## 태그", " ".join("#" + t.replace(" ", "") for t in tags), ""]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    p = OUT_DIR / f"news_{date}.md"
    p.write_text("\n".join(out), encoding="utf-8")
    print(p)


def pending():
    m = load_manifest()
    for p in sorted(OUT_DIR.glob("news_*.md")):
        date = p.stem[len("news_"):]
        if date not in m:
            print(f"{date}\t{p}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cards")
    ap.add_argument("--pending", action="store_true")
    ap.add_argument("--mark-uploaded", nargs=2, metavar=("DATE", "DRIVE_ID"))
    a = ap.parse_args()
    if a.cards:
        build(a.cards)
    elif a.pending:
        pending()
    elif a.mark_uploaded:
        date, fid = a.mark_uploaded
        if not DATE_RE.match(date):
            sys.exit("invalid date")
        m = load_manifest(); m[date] = fid; save_manifest(m)
        print(f"marked {date}")
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
