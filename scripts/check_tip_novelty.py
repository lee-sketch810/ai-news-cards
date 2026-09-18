"""
check_tip_novelty.py — 실전 팁의 구체성·반복 패턴 품질 게이트

사용법:
  python scripts/check_tip_novelty.py \
    --cards data/cards-2026-09-18.json --history public/data --days 14

종료 코드
  0: 통과
  1: 하나 이상의 팁이 실패
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

VAGUE_ENDINGS = (
    "확인한다", "점검한다", "고려한다", "검토한다", "살펴본다", "파악한다",
    "유의한다", "주의한다", "비교한다", "측정한다", "계산한다", "정리한다",
)

# 2026-09-14~16에 반복된 만능 조언 패턴. 구체 고유명사 없이 이 구조면 실패.
BANNED_PATTERNS = (
    re.compile(r"(작은|간단한|샘플|테스트).{0,25}(먼저|부터).{0,40}(확인|검증).{0,35}(넓|확대|적용)"),
    re.compile(r"처음에는.{0,50}(확인|검증).{0,35}(범위|허용).{0,20}(넓|확대)"),
    re.compile(r"일주일.{0,40}(기록|확인).{0,35}(뒤|후).{0,30}(적용|켜|자동)"),
)

GENERIC_ANCHORS = {"설정", "메뉴", "도구", "기능", "모델", "옵션", "화면", "버튼"}


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^0-9a-z가-힣]+", "", text)
    return text


def char_ngrams(text: str, n: int = 3) -> set[str]:
    s = normalize(text)
    return {s[i:i+n] for i in range(max(0, len(s)-n+1))}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def tip_text(card: dict) -> str:
    tip = card.get("tip")
    if isinstance(tip, str):
        return tip.strip()
    if isinstance(tip, dict):
        parts = [tip.get("goal", ""), *(tip.get("steps") or [])]
        return " ".join(str(x) for x in parts if x).strip()
    return ""


def load_history(folder: Path, before_date: str, days: int) -> list[tuple[str, str]]:
    before = datetime.strptime(before_date, "%Y-%m-%d").date()
    start = before - timedelta(days=days)
    rows: list[tuple[str, str]] = []
    for p in folder.glob("cards-*.json"):
        m = re.fullmatch(r"cards-(\d{4}-\d{2}-\d{2})\.json", p.name)
        if not m:
            continue
        d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        if not (start <= d < before):
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for card in data.get("cards", []):
            text = tip_text(card)
            if text:
                rows.append((m.group(1), text))
    return rows


def validate_card(card: dict, history: list[tuple[str, str]], threshold: float) -> list[str]:
    errs: list[str] = []
    lane = card.get("lane")
    tip = card.get("tip")
    headline = card.get("headline", "(제목 없음)")

    if lane == "signal":
        if tip not in (None, "", {}):
            errs.append("signal 레인은 tip이 null이어야 함")
        if not card.get("so_what"):
            errs.append("signal 레인은 so_what 필수")
        return errs

    if not isinstance(tip, dict):
        return ["tip/tool 레인의 tip은 객체여야 함"]

    goal = str(tip.get("goal", "")).strip()
    steps = tip.get("steps") or []
    time = str(tip.get("time", "")).strip()
    applies = str(tip.get("applies_to", "")).strip()
    text = tip_text(card)

    if not goal:
        errs.append("goal 누락")
    if not isinstance(steps, list) or not 2 <= len(steps) <= 4:
        errs.append("steps는 2~4개여야 함")
    if not re.search(r"\d", time):
        errs.append("time에 숫자 누락")
    if not applies:
        errs.append("applies_to 누락")
    if not re.search(r"\d", text + " " + time + " " + applies):
        errs.append("팁 전체에 숫자 1개 이상 필요")

    for i, step in enumerate(steps, 1):
        s = str(step).strip().rstrip(".。 ")
        if any(s.endswith(v) for v in VAGUE_ENDINGS):
            errs.append(f"step {i}: 모호한 종결어 '{next(v for v in VAGUE_ENDINGS if s.endswith(v))}'")

    # 실제 제품명·메뉴명·명령어로 보이는 앵커: 영문 고유 토큰, 따옴표 문자열,
    # 경로 기호(>), CLI 형태 중 하나. 일반어 '설정/메뉴'만으로는 불충분.
    anchor_ok = bool(
        re.search(r"[A-Za-z][A-Za-z0-9.+_-]{2,}", text)
        or re.search(r"[>›→/]", text)
        or re.search(r"['\"“”][^'\"“”]{2,}['\"“”]", text)
        or re.search(r"(?:npm|pip|git|curl|docker|python)\s+", text, re.I)
    )
    if not anchor_ok:
        errs.append("검증 가능한 고유명사/UI경로/명령어 앵커 누락")

    if any(p.search(text) for p in BANNED_PATTERNS) and not anchor_ok:
        errs.append("금지된 '작게 시험→확인→확대' 만능 패턴")

    grams = char_ngrams(text)
    best = (0.0, "", "")
    for d, old in history:
        sim = jaccard(grams, char_ngrams(old))
        if sim > best[0]:
            best = (sim, d, old)
    if best[0] >= threshold:
        errs.append(f"최근 팁과 유사도 {best[0]:.2f} (기준 {threshold:.2f}, {best[1]})")

    # 같은 날 카드끼리 중복은 main에서 누적 history로 잡는다.
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cards", required=True)
    ap.add_argument("--history", required=True)
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--threshold", type=float, default=0.58)
    args = ap.parse_args()

    cards_path = Path(args.cards)
    data = json.loads(cards_path.read_text(encoding="utf-8"))
    issue_date = data.get("date")
    if not issue_date:
        print("FAIL: date 누락")
        return 1

    history = load_history(Path(args.history), issue_date, args.days)
    failures = 0
    same_day: list[tuple[str, str]] = []

    for idx, card in enumerate(data.get("cards", []), 1):
        errs = validate_card(card, history + same_day, args.threshold)
        if errs:
            failures += 1
            print(f"FAIL #{idx} {card.get('headline','(제목 없음)')}")
            for e in errs:
                print(f"  - {e}")
        text = tip_text(card)
        if text:
            same_day.append((issue_date, text))

    n = len(data.get("cards", []))
    if failures:
        print(f"\nRESULT: {failures}/{n} cards failed tip quality gate")
        return 1
    print(f"RESULT: PASS - {n} cards; compared with {len(history)} tips from last {args.days} days")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
