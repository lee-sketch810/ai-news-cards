"""
build_rss.py — public/data/cards-*.json 아카이브에서 RSS 2.0 피드를 결정론적으로 생성 (P1)

뉴스레터 구독을 대신한다: 자체 이메일 발송(SMTP/PII 수집) 없이, 독자가 자기 RSS 리더나
Kill-the-Newsletter 같은 서비스로 "이메일처럼" 받아볼 수 있게 한다. AI 판단 없음 — 이미
쓰인 daily_insight/카드 데이터를 XML로 옮기기만 한다.

에디션(날짜) 1개 = 아이템 1개. 카드 낱개가 아니라 그날의 daily_insight를 본문으로 삼고,
그 날 카드 헤드라인 목록을 링크와 함께 붙인다(뉴스레터 다이제스트 형태).

사용법: python build_rss.py [--limit 30] [--site-url https://ai-news.wiselab.kr/]
"""
from __future__ import annotations
import argparse
import html
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PUBLIC = HERE.parent / "public"
PUBLIC_DATA = PUBLIC / "data"
KST = timezone(timedelta(hours=9))

DEFAULT_SITE_URL = "https://ai-news.wiselab.kr/"


def rfc822(date_str: str) -> str:
    """YYYY-MM-DD (KST, 그날 09:00 발행 기준) -> RFC 822 pubDate."""
    d = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=9, tzinfo=KST)
    return d.strftime("%a, %d %b %Y %H:%M:%S %z")


def item_xml(edition: dict, site_url: str) -> str:
    date = edition["date"]
    di = edition.get("daily_insight") or {}
    cards = edition.get("cards", [])
    title = di.get("title") or (cards[0]["headline"] if cards else date)
    link = f"{site_url}?date={date}"

    body_parts = []
    if di.get("body"):
        body_parts.append(f"<p>{html.escape(di['body'])}</p>")
    if cards:
        lis = "".join(
            f'<li><a href="{html.escape(c.get("source_url", ""))}">{html.escape(c.get("headline", ""))}</a></li>'
            for c in cards
        )
        body_parts.append(f"<ul>{lis}</ul>")
    description = "".join(body_parts)

    return (
        "<item>"
        f"<title>{html.escape(title)}</title>"
        f"<link>{html.escape(link)}</link>"
        f'<guid isPermaLink="true">{html.escape(link)}</guid>'
        f"<pubDate>{rfc822(date)}</pubDate>"
        f"<description><![CDATA[{description}]]></description>"
        "</item>"
    )


def build(limit: int, site_url: str) -> str:
    editions = []
    for p in sorted(PUBLIC_DATA.glob("cards-*.json"), reverse=True):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if d.get("date") and d.get("cards"):
            editions.append(d)
        if len(editions) >= limit:
            break

    items = "".join(item_xml(e, site_url) for e in editions)
    last_build = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "<channel>"
        "<title>오늘의 AI 뉴스</title>"
        f"<link>{html.escape(site_url)}</link>"
        "<description>매일 아침, 그날의 핵심 AI 뉴스만 골라 요약과 인사이트로. 출처와 발행일을 확인한 뉴스만 싣습니다.</description>"
        "<language>ko</language>"
        f'<atom:link href="{html.escape(site_url)}rss.xml" rel="self" type="application/rss+xml" />'
        f"<lastBuildDate>{last_build}</lastBuildDate>"
        f"{items}"
        "</channel>\n</rss>\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=30, help="포함할 최근 에디션 수 (기본 30)")
    ap.add_argument("--site-url", default=DEFAULT_SITE_URL)
    args = ap.parse_args()

    site_url = args.site_url if args.site_url.endswith("/") else args.site_url + "/"
    xml = build(args.limit, site_url)
    out = PUBLIC / "rss.xml"
    out.write_text(xml, encoding="utf-8")
    print(f"rss: wrote {out} ({xml.count('<item>')} items)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
