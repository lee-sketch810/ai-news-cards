"""render_cards.py v2 — 발행 전 스키마·카테고리·팁 품질 검증 포함."""
from __future__ import annotations
import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
HTML = ROOT / "public" / "index.html"
PUBLIC_DATA = ROOT / "public" / "data"
START = "/* CARDS_DATA_START */"
END = "/* CARDS_DATA_END */"

CATEGORIES = {
    "프롬프트·활용", "도구·기능", "자동화·에이전트", "보안·프라이버시",
    "비용·요금제", "교육·학습설계", "콘텐츠·제작", "흐름·정책",
}
LANES = {"tip", "tool", "signal"}


def validate(cards: dict, cards_path: Path) -> None:
    """렌더링 전에 구조 오류를 차단한다. 경고가 아니라 실패시키는 게 핵심."""
    errors: list[str] = []
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(cards.get("date", ""))):
        errors.append("top-level date가 YYYY-MM-DD가 아님")
    if not cards.get("cards"):
        errors.append("cards가 비어 있음")

    for i, card in enumerate(cards.get("cards", []), 1):
        cat = card.get("category")
        lane = card.get("lane")
        prefix = f"card #{i} {card.get('headline','(제목 없음)')}"
        if cat not in CATEGORIES:
            errors.append(f"{prefix}: 허용되지 않은 category '{cat}'")
        if lane not in LANES:
            errors.append(f"{prefix}: lane은 tip/tool/signal 중 하나여야 함")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(card.get("verified_date", ""))):
            errors.append(f"{prefix}: verified_date 누락/형식 오류")
        if not card.get("source_url") or not str(card["source_url"]).startswith(("http://", "https://")):
            errors.append(f"{prefix}: 실제 source_url 필요")
        if lane in {"tip", "tool"} and not isinstance(card.get("tip"), dict):
            errors.append(f"{prefix}: {lane} 레인은 구조화된 tip 객체 필수")
        if lane == "signal" and not card.get("so_what"):
            errors.append(f"{prefix}: signal 레인은 so_what 필수")

    if errors:
        raise ValueError("발행 스키마 검증 실패:\n- " + "\n- ".join(errors))

    # 세부 팁 품질·최근 14일 중복 검사. 파일이 없으면 배포를 멈춘다.
    checker = HERE / "check_tip_novelty.py"
    if not checker.exists():
        raise FileNotFoundError(f"tip checker missing: {checker}")
    result = subprocess.run(
        [sys.executable, str(checker), "--cards", str(cards_path),
         "--history", str(PUBLIC_DATA), "--days", "14"],
        text=True, capture_output=True,
    )
    if result.returncode != 0:
        raise ValueError("팁 품질 검증 실패:\n" + result.stdout + result.stderr)


def _build_manifest() -> dict:
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
            "tip_count": sum(1 for c in cards if c.get("lane") in {"tip", "tool"}),
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
    validate(cards, cards_path)
    n = len(cards.get("cards", []))
    date = cards["date"]

    PUBLIC_DATA.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(cards_path, PUBLIC_DATA / f"cards-{date}.json")
    manifest = _build_manifest()
    (PUBLIC_DATA / "index.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

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
