"""
score_news.py — 의미도 점수 사전계산 (P1 Pre-processing, Step 3)

AI는 산술하지 않는다. 이 스크립트가 결정론적으로 점수를 계산하면
@news-scorer는 해석·선정·카테고리 균형만 담당한다.

점수 = 중요도(weight 0.3) + 실용성(0.4) + 관련성(0.3), 각 0~100 정규화.
신호: 키워드 매칭 + 소스 권위 + 검증 상태.

사용법: python score_news.py --in verified.json --out scored.json
"""
from __future__ import annotations
import argparse
import json

# 키워드 신호 테이블 (소문자 부분일치). 가중은 의미도 축별로 분리.
IMPORTANCE_KW = {  # 중요도 — 업계 파급
    "release": 30, "launch": 30, "unveil": 28, "announce": 22, "gpt": 25,
    "claude": 25, "gemini": 25, "model": 18, "acquire": 26, "ipo": 20,
    "출시": 30, "공개": 26, "발표": 22, "인수": 26,
}
PRACTICAL_KW = {  # 실용성 — 바로 써먹음
    "tool": 30, "agent": 28, "automation": 28, "api": 24, "workflow": 26,
    "feature": 22, "free": 18, "open source": 26, "plugin": 22, "integration": 22,
    "도구": 30, "자동화": 28, "기능": 22, "워크플로우": 26, "에이전트": 28,
}
RELEVANCE_KW = {  # 관련성 — 실무자·교육·생산성·생태계
    "education": 26, "e-learning": 30, "productivity": 24, "content": 20,
    "anthropic": 24, "openai": 20, "prompt": 22, "coding": 22, "developer": 20,
    "교육": 26, "이러닝": 30, "생산성": 24, "콘텐츠": 20, "프롬프트": 22,
}
# 감점 — 실무 적용 불명확
PENALTY_KW = {"funding round": -15, "stock": -12, "lawsuit": -8, "주가": -12, "투자유치": -12}

SOURCE_AUTHORITY = {  # 도메인 부분일치 → 가산점(중요도)
    "anthropic.com": 12, "openai.com": 12, "blog.google": 10, "microsoft.com": 8,
    "techcrunch.com": 8, "theverge.com": 7, "cnbc.com": 6, "reuters.com": 8,
    "aitimes": 8, "zdnet": 5,
}
WEIGHTS = {"importance": 0.3, "practical": 0.4, "relevance": 0.3}


def _axis(text: str, table: dict) -> int:
    s = text.lower()
    return sum(w for kw, w in table.items() if kw in s)


def score_article(art: dict) -> dict:
    text = f"{art.get('title','')} {art.get('snippet','')}"
    url = art.get("url", "").lower()
    imp = _axis(text, IMPORTANCE_KW) + sum(w for d, w in SOURCE_AUTHORITY.items() if d in url)
    pra = _axis(text, PRACTICAL_KW)
    rel = _axis(text, RELEVANCE_KW)
    penalty = _axis(text, PENALTY_KW)
    # 검증 상태 보정: 오늘 발행 약가산
    if art.get("verification_status") == "passed":
        imp += 6
    clamp = lambda v: max(0, min(100, v))
    imp_n, pra_n, rel_n = clamp(imp), clamp(pra), clamp(rel)
    total = round(imp_n * WEIGHTS["importance"] + pra_n * WEIGHTS["practical"]
                  + rel_n * WEIGHTS["relevance"] + penalty, 1)
    art["signals"] = {"importance": imp_n, "practical": pra_n,
                      "relevance": rel_n, "penalty": penalty}
    art["score"] = max(0, total)
    return art


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument("--out", dest="out_path", required=True)
    args = ap.parse_args()
    with open(args.in_path, encoding="utf-8") as f:
        data = json.load(f)
    arts = [score_article(a) for a in data.get("articles", [])]
    arts.sort(key=lambda a: a["score"], reverse=True)
    for i, a in enumerate(arts, 1):
        a["rank"] = i
    data["articles"] = arts
    data["scored_count"] = len(arts)
    with open(args.out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    top = ", ".join(f"{a['score']:.0f}" for a in arts[:10])
    print(f"scored {len(arts)} articles. top10 scores: [{top}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
