"""
build_ebook.py — 카드 아카이브(data/cards-*.json)를 EPUB 3 전자책 1권으로 엮는다 (P1, 결정론적)

원칙: 카드 원문(headline/summary/points/insight/출처)은 발행 당시 그대로 보존한다.
      서문·부(部) 여는 글 등 새로 쓴 글은 이 스크립트의 상수로만 존재한다.

사용법: python scripts/build_ebook.py
        [--data-dir data] [--out ebook/AI-49days-2026-summer.epub]
        [--font-bold path.ttf --font-regular path.ttf]   # 표지 PNG용(없으면 표지 생략)
"""
from __future__ import annotations

import argparse
import html
import json
import zipfile
from datetime import date
from pathlib import Path
from xml.dom import minidom

CAT_COLOR = {
    "모델·연구": "#534AB7", "에이전트·자동화": "#0F6E56", "도구·개발": "#0F6E56",
    "교육·생산성": "#854F0B", "산업·투자": "#993C1D", "정책·규제": "#993556",
}
DEFAULT_COLOR = "#534AB7"
WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]

BOOK_TITLE = "격변의 49일"
BOOK_SUBTITLE = "2026년 여름, AI 뉴스 아카이브 2026.06.24–08.11"
BOOK_AUTHOR = "오늘의 AI 뉴스"
BOOK_ID = "urn:uuid:7c1f2a4e-9d3b-4e6f-8a21-ainews49-2026"
SITE_URL = "https://ai-news.wiselab.kr/"

PREFACE = """이 책은 2026년 6월 24일부터 8월 11일까지 49일 동안, 매일 아침 발행일 검증을 거쳐
선별한 AI 뉴스 276건의 기록이다. 각 뉴스는 발행 당일 한국어 요약과 핵심 포인트,
그리고 '왜 중요한가'라는 범용 인사이트로 정리되었고, 이 책에는 그 원문이 발행 당시
모습 그대로 실려 있다. 사후에 고쳐 쓰거나 결과를 알고 덧붙인 해설은 없다.

이 49일은 AI 산업이 몇 개의 축을 따라 빠르게 재편된 기간이었다. 성능 경쟁의 정점에서
승부처가 경제성과 비용으로 내려왔고, 세 프런티어 랩이 같은 날 신모델을 내놓는가 하면,
오픈 가중치 공세가 판을 흔들었다. 에이전트는 데스크톱을 떠나 모바일과 손목으로,
그리고 계정 권한 안으로 들어왔으며, 그 속도를 안전장치가 따라잡지 못한다는 경고가
반복해서 등장했다. 국가 단위의 인프라 청구서와 월가의 자본, 미·중의 제도 경쟁,
한국의 소버린 AI까지 — 하루하루의 기사를 시간 순서대로 따라가면, 뉴스 한 건으로는
보이지 않던 흐름이 떠오른다.

빠르게 소비되고 잊히는 뉴스를 '흐름을 읽는 기록'으로 남기기 위해 이 책을 엮었다."""

HOW_TO_READ = """이 책은 월 단위 3부, 날짜 단위 49개 장으로 구성된다. 각 장의 제목은 그날의
핵심 흐름을 요약한 '일일 인사이트' 제목이며, 장 첫머리에 그날의 흐름 전체를 조망하는
글이 실린다. 이어지는 카드 하나가 뉴스 한 건이다.

각 카드는 다음 순서로 읽는다.

· 분류·검증일 — 뉴스의 카테고리와, 발행일 메타데이터로 확인한 실제 발행 날짜.
· 헤드라인과 요약 — 무슨 일이 있었는가.
· 핵심 포인트 — 사실 관계 세 줄 요약.
· 왜 중요한가 — 개인 맞춤이 아닌, 산업 함의와 일반 교훈 중심의 인사이트.
· 출처 — 원 기사 링크. 모든 카드는 출처와 발행일을 확인한 뉴스만 실었다.

날짜 표기는 모두 절대 날짜다. '어제'·'오늘' 같은 상대 표현이 없으므로,
시간이 지나 읽어도 각 사건의 시점이 정확하다."""

PART_INTROS = {
    "2026-06": (
        "1부 — 2026년 6월",
        "6월 24일부터 30일까지, 일주일의 기록. 최신 모델과 인재가 '상위'로 쏠리는 집중 현상,"
        " 능력 확장에 따라붙는 통제, 그리고 승부처가 성능에서 경제성으로 내려오는 전환이"
        " 이 주에 함께 나타났다. 모델이 '등급'으로 쪼개지고 사상 최대 베팅의 청구서가"
        " 논의되기 시작한, 여름 격변의 서장이다.",
    ),
    "2026-07": (
        "2부 — 2026년 7월",
        "한 달 내내 굵직한 변곡점이 이어졌다. 수출규제 완화와 새 규정이 동시에 진행되고,"
        " AI 인프라 청구서는 국가 단위로 커졌다. 7월 9일에는 사상 최초로 세 프런티어 랩이"
        " 같은 날 신모델을 내놨고, 에이전트는 모바일과 손목으로 이동했다. 빅테크 연합군 결성,"
        " 중국발 오픈 가중치 공세, 한국의 '소버린 AI'와 1400조 AI 혈맹, 그리고 '증류' 논쟁까지"
        " — 월말로 갈수록 AI 투자는 실적으로 검증받는 '증명의 국면'에 들어섰다.",
    ),
    "2026-08": (
        "3부 — 2026년 8월",
        "성능 경쟁이 저물고 통제권·비용·책임의 경쟁이 시작됐다. 에이전트가 계정 권한까지"
        " 넘겨받는 사이 능력은 하루 만에 증명되고 안전장치는 하루 만에 뚫렸으며, '자율성은"
        " 앞서가는데 안전장치는 뒤따라간다'는 경고가 연일 반복됐다. 전장은 모델에서"
        " 인프라·거버넌스로 옮겨갔고, AI는 개인의 기기와 월가의 자본으로 동시에 내려왔다.",
    ),
}

CLOSING = """여기까지가 49일의 기록이다.

이 책의 모든 카드는 자동화 파이프라인(수집 → 발행일 검증 → 점수화 → 카드 작성 → 배포)이
매일 아침 생성해 공개 사이트에 발행한 것으로, 출처와 발행일을 확인한 뉴스만 실었다.
요약과 인사이트에 원 기사에 대한 해석이 포함되어 있으므로, 정확한 사실 관계는
각 카드의 출처 링크에서 원문을 확인하기 바란다.

이후의 기록은 사이트에서 매일 이어진다."""

CSS = """\
body { font-family: "Apple SD Gothic Neo", "Noto Sans KR", "NanumGothic", sans-serif;
       line-height: 1.7; margin: 0 5%; color: #222; }
h1 { font-size: 1.5em; margin: 1.2em 0 0.3em; line-height: 1.4; }
h2 { font-size: 1.15em; margin: 1.4em 0 0.5em; line-height: 1.45; }
p  { margin: 0.6em 0; }
a  { color: #534AB7; }
.meta { color: #888; font-size: 0.85em; margin: 0 0 1.2em; }
.badge { font-size: 0.78em; font-weight: bold; padding: 0.1em 0.55em;
         border-radius: 0.5em; color: #fff; }
.vdate { color: #999; font-size: 0.8em; margin-left: 0.5em; }
.card { border: 1px solid #e2e2dc; border-radius: 0.6em; padding: 0.9em 1em;
        margin: 1.1em 0; page-break-inside: avoid; }
.card h2 { margin: 0.5em 0 0.4em; }
.card p.summary { color: #444; }
.card ul { margin: 0.5em 0; padding-left: 1.2em; color: #555; font-size: 0.95em; }
.card li { margin: 0.25em 0; }
.insight { background: #f5f4ef; border-radius: 0.4em; padding: 0.6em 0.8em;
           margin: 0.7em 0; font-size: 0.95em; }
.insight .label { font-weight: bold; font-size: 0.85em; color: #534AB7; }
.source { font-size: 0.85em; }
.daily { background: #EEEDFE; border: 1px solid #cac6f0; border-radius: 0.6em;
         padding: 0.8em 1em; margin: 1em 0 1.4em; }
.daily .label { font-weight: bold; font-size: 0.85em; color: #534AB7; }
.titlepage { text-align: center; margin-top: 22%; }
.titlepage h1 { font-size: 2em; border: none; }
.titlepage .subtitle { color: #555; font-size: 1.05em; }
.titlepage .author { margin-top: 3em; color: #777; }
.part { text-align: left; margin-top: 30%; }
.part h1 { font-size: 1.7em; }
.part p { color: #555; }
hr.sep { border: none; border-top: 1px solid #ddd; margin: 2em 0; }
"""

XHTML_HEAD = (
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<!DOCTYPE html>\n'
    '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" '
    'xml:lang="ko" lang="ko">\n<head>\n<meta charset="utf-8"/>\n<title>{title}</title>\n'
    '<link rel="stylesheet" type="text/css" href="style.css"/>\n</head>\n<body>\n'
)
XHTML_FOOT = "</body>\n</html>\n"


def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def paragraphs(text: str) -> str:
    out = []
    for block in text.split("\n\n"):
        block = " ".join(line.strip() for line in block.strip().splitlines())
        if block:
            out.append(f"<p>{esc(block)}</p>")
    return "\n".join(out)


def date_label(iso: str) -> str:
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{m}월 {d}일 ({WEEKDAY_KO[date(y, m, d).weekday()]})"


def card_html(c: dict) -> str:
    color = CAT_COLOR.get(c.get("category", ""), DEFAULT_COLOR)
    pts = "".join(f"<li>{esc(p)}</li>" for p in c.get("points", []))
    src_name = c.get("source_name", "")
    src_url = c.get("source_url", "")
    parts = [
        '<div class="card">',
        f'<p><span class="badge" style="background:{color}">{esc(c.get("category", ""))}</span>'
        f'<span class="vdate">{esc(c.get("verified_date", ""))}</span></p>',
        f'<h2>{esc(c.get("headline", ""))}</h2>',
        f'<p class="summary">{esc(c.get("summary", ""))}</p>',
    ]
    if pts:
        parts.append(f"<ul>{pts}</ul>")
    if c.get("insight"):
        parts.append(
            f'<div class="insight"><span class="label">왜 중요한가</span>'
            f'<p>{esc(c["insight"])}</p></div>'
        )
    if src_url:
        parts.append(f'<p class="source">출처 · <a href="{esc(src_url)}">{esc(src_name or src_url)}</a></p>')
    parts.append("</div>")
    return "\n".join(parts)


def day_page(d: dict) -> tuple[str, str]:
    di = d.get("daily_insight") or {}
    title = f'{date_label(d["date"])} — {di.get("title", "")}'
    body = [XHTML_HEAD.format(title=esc(title))]
    body.append(f"<h1>{esc(title)}</h1>")
    body.append(f'<p class="meta">{esc(d["date"])} · 검증된 뉴스 {len(d.get("cards", []))}건</p>')
    if di.get("body"):
        body.append(
            f'<div class="daily"><span class="label">오늘의 흐름</span>'
            f'<p>{esc(di["body"])}</p></div>'
        )
    for c in d.get("cards", []):
        body.append(card_html(c))
    body.append(XHTML_FOOT)
    return title, "\n".join(body)


def text_page(title: str, heading: str, text: str, cls: str = "") -> str:
    div = f'<div class="{cls}">' if cls else "<div>"
    return (
        XHTML_HEAD.format(title=esc(title))
        + f"{div}\n<h1>{esc(heading)}</h1>\n{paragraphs(text)}\n</div>\n"
        + XHTML_FOOT
    )


def make_cover_png(font_bold: Path, font_regular: Path, day_count: int, card_count: int) -> bytes:
    from io import BytesIO

    from PIL import Image, ImageDraw, ImageFont

    W, H = 1600, 2560
    bg, accent, dim = (24, 22, 48), (110, 100, 220), (150, 145, 190)
    img = Image.new("RGB", (W, H), bg)
    dr = ImageDraw.Draw(img)
    f_title = ImageFont.truetype(str(font_bold), 210)
    f_sub = ImageFont.truetype(str(font_regular), 62)
    f_small = ImageFont.truetype(str(font_regular), 48)

    # 49일을 뜻하는 7×7 격자
    gx, gy, cell, gap = 200, 340, 92, 40
    for i in range(day_count):
        r, c = divmod(i, 7)
        x, y = gx + c * (cell + gap), gy + r * (cell + gap)
        dr.rectangle([x, y, x + cell, y + cell], fill=accent if i % 7 in (2, 4) else (52, 48, 92))

    dr.text((200, 1420), "격변의", font=f_title, fill=(240, 238, 250))
    dr.text((200, 1660), "49일", font=f_title, fill=accent)
    dr.line([(200, 1980), (1400, 1980)], fill=(70, 66, 120), width=4)
    dr.text((200, 2030), "2026년 여름, AI 뉴스 아카이브", font=f_sub, fill=(210, 206, 235))
    dr.text((200, 2130), f"2026.06.24 – 08.11 · 검증된 뉴스 {card_count}건", font=f_small, fill=dim)
    dr.text((200, 2380), "오늘의 AI 뉴스", font=f_small, fill=dim)

    buf = BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def build(data_dir: Path, out: Path, font_bold: Path | None, font_regular: Path | None) -> None:
    files = sorted(data_dir.glob("cards-*.json"))
    days = [json.loads(f.read_text(encoding="utf-8")) for f in files]
    days.sort(key=lambda d: d["date"])
    total_cards = sum(len(d.get("cards", [])) for d in days)

    # (파일명, 제목, XHTML, 깊이) — 깊이 0=권두/부, 1=일자 장
    pages: list[tuple[str, str, str, int]] = []
    pages.append((
        "titlepage.xhtml", BOOK_TITLE,
        XHTML_HEAD.format(title=esc(BOOK_TITLE))
        + f'<div class="titlepage">\n<h1>{esc(BOOK_TITLE)}</h1>\n'
        + f'<p class="subtitle">{esc(BOOK_SUBTITLE)}</p>\n'
        + f'<p class="subtitle">검증된 뉴스 {total_cards}건 · {len(days)}일의 기록</p>\n'
        + f'<p class="author">{esc(BOOK_AUTHOR)} · {esc(SITE_URL)}</p>\n</div>\n'
        + XHTML_FOOT, 0,
    ))
    pages.append(("preface.xhtml", "서문", text_page("서문", "서문", PREFACE), 0))
    pages.append(("howto.xhtml", "이 책을 읽는 법", text_page("이 책을 읽는 법", "이 책을 읽는 법", HOW_TO_READ), 0))

    seen_months: set[str] = set()
    for i, d in enumerate(days):
        month = d["date"][:7]
        if month not in seen_months:
            seen_months.add(month)
            part_title, part_text = PART_INTROS[month]
            pages.append((f"part-{month}.xhtml", part_title,
                          text_page(part_title, part_title, part_text, cls="part"), 0))
        title, xhtml = day_page(d)
        pages.append((f"day-{d['date']}.xhtml", title, xhtml, 1))
    pages.append(("closing.xhtml", "맺음말", text_page("맺음말", "맺음말", CLOSING), 0))

    for _, title, xhtml, _ in pages:
        minidom.parseString(xhtml)  # 웰폼드 검증 — 깨진 XHTML은 여기서 즉시 실패

    cover_png = None
    if font_bold and font_regular and font_bold.exists() and font_regular.exists():
        cover_png = make_cover_png(font_bold, font_regular, len(days), total_cards)

    modified = "2026-08-29T00:00:00Z"
    manifest = ['<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
                '<item id="css" href="style.css" media-type="text/css"/>',
                '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>']
    if cover_png:
        manifest.append('<item id="cover-img" href="cover.png" media-type="image/png" properties="cover-image"/>')
    spine = []
    for idx, (fname, _, _, _) in enumerate(pages):
        manifest.append(f'<item id="p{idx}" href="{fname}" media-type="application/xhtml+xml"/>')
        spine.append(f'<itemref idref="p{idx}"/>')

    opf = f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid" xml:lang="ko">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="bookid">{BOOK_ID}</dc:identifier>
<dc:title>{esc(BOOK_TITLE)} — {esc(BOOK_SUBTITLE)}</dc:title>
<dc:language>ko</dc:language>
<dc:creator>{esc(BOOK_AUTHOR)}</dc:creator>
<dc:date>2026-08-29</dc:date>
<meta property="dcterms:modified">{modified}</meta>
{'<meta name="cover" content="cover-img"/>' if cover_png else ''}
</metadata>
<manifest>
{chr(10).join(manifest)}
</manifest>
<spine toc="ncx">
{chr(10).join(spine)}
</spine>
</package>
'''

    def toc_entries() -> str:
        out, open_sub = [], False
        for fname, title, _, depth in pages:
            if depth == 0:
                if open_sub:
                    out.append("</ol></li>")
                    open_sub = False
                if fname.startswith("part-"):
                    out.append(f'<li><a href="{fname}">{esc(title)}</a><ol>')
                    open_sub = True
                else:
                    out.append(f'<li><a href="{fname}">{esc(title)}</a></li>')
            else:
                out.append(f'<li><a href="{fname}">{esc(title)}</a></li>')
        if open_sub:
            out.append("</ol></li>")
        return "\n".join(out)

    nav = (
        XHTML_HEAD.format(title="차례")
        + '<nav epub:type="toc" id="toc">\n<h1>차례</h1>\n<ol>\n'
        + toc_entries()
        + "\n</ol>\n</nav>\n"
        + XHTML_FOOT
    )
    minidom.parseString(nav)

    navpoints = []
    for idx, (fname, title, _, _) in enumerate(pages):
        navpoints.append(
            f'<navPoint id="np{idx}" playOrder="{idx + 1}"><navLabel><text>{esc(title)}</text></navLabel>'
            f'<content src="{fname}"/></navPoint>'
        )
    ncx = f'''<?xml version="1.0" encoding="utf-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1" xml:lang="ko">
<head><meta name="dtb:uid" content="{BOOK_ID}"/></head>
<docTitle><text>{esc(BOOK_TITLE)}</text></docTitle>
<navMap>
{chr(10).join(navpoints)}
</navMap>
</ncx>
'''

    container = '''<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>
'''

    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", zipfile.ZIP_STORED)
        z.writestr("META-INF/container.xml", container, zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/content.opf", opf, zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/nav.xhtml", nav, zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/toc.ncx", ncx, zipfile.ZIP_DEFLATED)
        z.writestr("OEBPS/style.css", CSS, zipfile.ZIP_DEFLATED)
        if cover_png:
            z.writestr("OEBPS/cover.png", cover_png, zipfile.ZIP_DEFLATED)
        for fname, _, xhtml, _ in pages:
            z.writestr(f"OEBPS/{fname}", xhtml, zipfile.ZIP_DEFLATED)

    print(f"OK: {out} · {len(days)}일 · 카드 {total_cards}건 · 페이지 {len(pages)}개"
          f" · 표지 {'포함' if cover_png else '없음(폰트 미지정)'}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out", default="ebook/AI-49days-2026-summer.epub")
    ap.add_argument("--font-bold")
    ap.add_argument("--font-regular")
    args = ap.parse_args()
    build(Path(args.data_dir), Path(args.out),
          Path(args.font_bold) if args.font_bold else None,
          Path(args.font_regular) if args.font_regular else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
