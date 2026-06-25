"""
dedupe.py — 후보 기사 중복 제거 (P1 Post-processing, Step 1)

URL 정규화 키 + 제목 유사도(SequenceMatcher ≥ threshold)로 중복을 제거한다.
먼저 등장한 항목을 유지(수집 우선순위 보존).

사용법: python dedupe.py --in candidates.json --out candidates.json [--threshold 0.75]
"""
from __future__ import annotations
import argparse
import json
import re
from difflib import SequenceMatcher
from urllib.parse import urlparse

DEFAULT_THRESHOLD = 0.75


def url_key(url: str) -> str:
    try:
        p = urlparse(url.strip().lower())
        return f"{p.netloc}{p.path}".rstrip("/")
    except Exception:
        return url.strip().lower()


def norm_title(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").lower()).strip()


def dedupe(articles: list[dict], threshold: float = DEFAULT_THRESHOLD) -> tuple[list, int]:
    seen_urls: set[str] = set()
    kept_titles: list[str] = []
    out = []
    removed = 0
    for art in articles:
        u = url_key(art.get("url", ""))
        if not u or u in seen_urls:
            removed += 1
            continue
        nt = norm_title(art.get("title", ""))
        if any(SequenceMatcher(None, nt, kt).ratio() >= threshold for kt in kept_titles):
            removed += 1
            continue
        seen_urls.add(u)
        kept_titles.append(nt)
        out.append(art)
    return out, removed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument("--out", dest="out_path", required=True)
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    args = ap.parse_args()
    with open(args.in_path, encoding="utf-8") as f:
        data = json.load(f)
    arts = data.get("articles", [])
    deduped, removed = dedupe(arts, args.threshold)
    data["articles"] = deduped
    data["deduped_removed"] = removed
    with open(args.out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"dedupe: {len(arts)} -> {len(deduped)} (removed {removed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
