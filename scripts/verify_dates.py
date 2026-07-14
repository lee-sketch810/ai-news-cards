"""
verify_dates.py — 발행일 검증 게이트 (이 사이트의 생명선)

당일성 검증을 결정론적으로 수행한다. AI(@date-verifier)가 WebFetch로 각 기사의
발행일 메타데이터를 추출해 `raw_published` 필드에 채워 넣으면, 이 스크립트가
KST 기준 '오늘/어제' 윈도우 판정을 내린다. 윈도우 밖·미상은 보수적으로 탈락.

판정 결과(verification_status):
  passed     — 발행일이 KST 오늘
  yesterday  — 발행일이 KST 어제 (WINDOW_DAYS=1 허용, 절대표기로 표시됨)
  (탈락)      — 윈도우 밖(stale) 또는 발행일 미상(unverified) → 출력에서 제거

사용법:
  python verify_dates.py --in candidates.json --out verified.json [--window 1]
  python verify_dates.py --selftest
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))
DEFAULT_WINDOW_DAYS = 1


def parse_date(raw: str | None) -> datetime | None:
    """ISO 8601(Z/offset/날짜만)·흔한 변형을 tz-aware datetime으로 파싱. 실패 시 None."""
    if not raw:
        return None
    s = str(raw).strip()
    if not s:
        return None
    # ISO 8601
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    # 날짜만 (YYYY-MM-DD 또는 YYYY/MM/DD)
    m = re.search(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", s)
    if m:
        y, mo, d = (int(g) for g in m.groups())
        try:
            return datetime(y, mo, d, tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def classify(raw_published: str | None, now_kst: datetime | None = None,
             window_days: int = DEFAULT_WINDOW_DAYS) -> tuple[str | None, str]:
    """
    (verified_date, status)를 반환.
    status ∈ {passed, yesterday, stale, unverified}.
    verified_date는 KST 기준 절대표기(YYYY-MM-DD) — stale/unverified면 None일 수 있음.
    """
    now_kst = now_kst or datetime.now(KST)
    today = now_kst.date()
    dt = parse_date(raw_published)
    if dt is None:
        return None, "unverified"
    d_kst = dt.astimezone(KST).date()
    verified_date = d_kst.isoformat()
    if d_kst == today:
        return verified_date, "passed"
    if today - timedelta(days=window_days) <= d_kst < today:
        return verified_date, "yesterday"
    return verified_date, "stale"


def verify_file(in_path: str, out_path: str, window_days: int = DEFAULT_WINDOW_DAYS,
                 now_kst: datetime | None = None) -> dict:
    with open(in_path, encoding="utf-8") as f:
        data = json.load(f)
    articles = data.get("articles", [])
    now_kst = now_kst or datetime.now(KST)
    kept, rejected = [], []
    for art in articles:
        raw = art.get("raw_published") or art.get("snippet_date")
        verified_date, status = classify(raw, now_kst, window_days)
        if status in ("passed", "yesterday"):
            art["verified_date"] = verified_date
            art["verification_status"] = status
            kept.append(art)
        else:
            art["verification_status"] = status
            rejected.append({"title": art.get("title", "")[:80],
                             "url": art.get("url", ""),
                             "raw_published": raw, "reason": status})
    result = {
        "generated_at": now_kst.isoformat(),
        "date": now_kst.date().isoformat(),
        "window_days": window_days,
        "total_in": len(articles),
        "total_passed": len(kept),
        "passed_today": sum(1 for a in kept if a["verification_status"] == "passed"),
        "passed_yesterday": sum(1 for a in kept if a["verification_status"] == "yesterday"),
        "rejected": rejected,
        "articles": kept,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result


def _selftest() -> int:
    now = datetime(2026, 6, 25, 7, 0, tzinfo=KST)  # KST 아침
    cases = [
        ("2026-06-25T03:00:00+00:00", "passed"),     # UTC 03시 = KST 12시 오늘
        ("2026-06-24T20:00:00+00:00", "passed"),     # UTC 20시 = KST 익일 05시 → 06-25 오늘
        ("2026-06-24T05:00:00+00:00", "yesterday"),  # KST 06-24
        ("2026-06-23T05:00:00+00:00", "stale"),      # 이틀 전
        ("2026-06-25", "passed"),
        (None, "unverified"),
        ("garbage", "unverified"),
    ]
    ok = True
    for raw, expect in cases:
        _, status = classify(raw, now)
        flag = "OK " if status == expect else "FAIL"
        if status != expect:
            ok = False
        print(f"{flag} {str(raw)[:30]:32} expect={expect:11} got={status}")
    print("ALL PASS" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path")
    ap.add_argument("--out", dest="out_path")
    ap.add_argument("--window", type=int, default=DEFAULT_WINDOW_DAYS)
    ap.add_argument("--date", dest="date", help="YYYY-MM-DD (KST) override 'today' for backfill runs")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    if not args.in_path or not args.out_path:
        ap.error("--in and --out required (or --selftest)")
    now_kst = None
    if args.date:
        target = datetime.strptime(args.date, "%Y-%m-%d")
        now_kst = target.replace(hour=9, tzinfo=KST)
    res = verify_file(args.in_path, args.out_path, args.window, now_kst)
    print(f"verified: {res['total_passed']}/{res['total_in']} "
          f"(today={res['passed_today']}, yesterday={res['passed_yesterday']}, "
          f"rejected={len(res['rejected'])})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
