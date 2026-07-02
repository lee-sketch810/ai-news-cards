"""
build_digest.py — 발행된 카드 에디션을 이메일 다이제스트(HTML)로 변환 (P1, render 이후)

주의: 이 스크립트는 초안(draft) 콘텐츠만 생성한다. 실제 발송은 하지 않는다
(Gmail MCP create_draft로 초안함에만 저장 — 발송은 사용자가 직접).

사용법: python build_digest.py --cards data/cards-2026-07-01.json [--site-url https://...]
       또는 --out으로 HTML을 파일로 저장하고 싶을 때
"""
from __future__ import annotations
import argparse
import html
import json
from pathlib import Path

CAT_COLOR = {
    "모델·연구": "#534AB7", "에이전트·자동화": "#0F6E56", "도구·개발": "#0F6E56",
    "교육·생산성": "#854F0B", "산업·투자": "#993C1D", "정책·규제": "#993556",
}


def build_html(cards_data: dict, site_url: str) -> tuple[str, str]:
    date = cards_data.get("date", "")
    di = cards_data.get("daily_insight") or {}
    cards = cards_data.get("cards", [])

    subject = f"[오늘의 AI 뉴스] {date} · {di.get('title', '오늘의 핵심 뉴스')}"

    parts = [
        '<div style="font-family:-apple-system,\'Apple SD Gothic Neo\',sans-serif;max-width:640px;margin:0 auto">',
        f'<h1 style="font-size:20px;margin:0 0 4px">오늘의 AI 뉴스</h1>',
        f'<p style="font-size:13px;color:#666;margin:0 0 20px">{html.escape(date)} · '
        f'검증된 뉴스 {len(cards)}건</p>',
    ]
    if di.get("title"):
        parts.append(
            '<div style="background:#EEEDFE;border:1px solid #534AB7;border-radius:10px;'
            'padding:14px 16px;margin:0 0 20px">'
            '<div style="font-size:11px;font-weight:600;color:#534AB7">오늘의 흐름</div>'
            f'<h2 style="font-size:16px;margin:4px 0 6px">{html.escape(di.get("title",""))}</h2>'
            f'<p style="font-size:13px;color:#333;margin:0;line-height:1.6">'
            f'{html.escape(di.get("body",""))}</p></div>'
        )
    for c in cards:
        color = CAT_COLOR.get(c.get("category", ""), "#534AB7")
        pts = "".join(f'<li style="margin:3px 0">{html.escape(p)}</li>' for p in c.get("points", []))
        parts.append(
            '<div style="border:1px solid #e5e5e0;border-radius:10px;padding:14px 16px;margin:0 0 12px">'
            f'<span style="font-size:11px;font-weight:600;color:{color};background:#f1efe8;'
            f'padding:2px 8px;border-radius:6px">{html.escape(c.get("category",""))}</span> '
            f'<span style="font-size:12px;color:#999">{html.escape(c.get("verified_date",""))}</span>'
            f'<h3 style="font-size:15px;margin:8px 0 6px">{html.escape(c.get("headline",""))}</h3>'
            f'<p style="font-size:13px;color:#555;margin:0 0 8px;line-height:1.6">'
            f'{html.escape(c.get("summary",""))}</p>'
            f'<ul style="font-size:12.5px;color:#555;margin:0 0 8px;padding-left:18px">{pts}</ul>'
            '<div style="background:#f6f6f4;border-radius:6px;padding:8px 10px;margin:0 0 8px">'
            '<span style="font-size:11px;font-weight:600">왜 중요한가</span>'
            f'<p style="font-size:12.5px;color:#555;margin:4px 0 0">{html.escape(c.get("insight",""))}</p>'
            '</div>'
            f'<a href="{html.escape(c.get("source_url",""))}" style="font-size:12px;color:{color}">'
            f'출처 · {html.escape(c.get("source_name",""))}</a>'
            '</div>'
        )
    parts.append(
        f'<p style="font-size:12px;color:#999;margin-top:20px">'
        f'<a href="{html.escape(site_url)}" style="color:#534AB7">사이트에서 더 보기</a> · '
        '매일 아침 9시 업데이트, 출처와 발행일을 확인한 뉴스만 싣습니다.</p></div>'
    )
    return subject, "".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cards", required=True)
    ap.add_argument("--site-url", default="https://example.github.io/ai-news-cards/")
    ap.add_argument("--out")
    args = ap.parse_args()

    data = json.loads(Path(args.cards).read_text(encoding="utf-8"))
    subject, body = build_html(data, args.site_url)

    result = {"subject": subject, "html": body}
    if args.out:
        Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"digest written -> {args.out}")
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
