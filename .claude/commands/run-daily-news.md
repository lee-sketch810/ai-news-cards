---
description: "Daily AI News Card 파이프라인 전체 실행 (수집→검증→점수→카드→배포). 매일 09:00 KST 스케줄."
---

ai-news-cards/workflow.md를 따라 1~6단계를 순차 실행한다. Autopilot enabled.

실행 절차 (Orchestrator):
1. `python scripts/build_queries.py --out data/research/queries.json`
2. `@news-collector` → WebSearch 8앵글 수집 → `data/research/candidates-<DATE>.json`
3. `python scripts/dedupe.py --in <candidates> --out <candidates>`
4. `@date-verifier` → 각 후보 WebFetch로 발행일 확인 → `raw_published` 채움
   → `python scripts/verify_dates.py --in <candidates> --out data/research/verified-<DATE>.json --window 1`
   → `@fact-checker`로 발행일 표본 검증
5. `python scripts/score_news.py --in <verified> --out data/planning/scored-<DATE>.json`
   → `@news-scorer` → Top10 선정·카테고리 균형 → `data/planning/top10-<DATE>.json`
6. (human) `/review-news` — Autopilot 자동 승인 + `autopilot-logs/step-4-decision.md`
7. `@card-writer` → 한국어 카드 + 범용 인사이트 → `data/cards-<DATE>.json`
   → `@reviewer + @fact-checker` 검토
8. `@news-deployer` → `python scripts/render_cards.py --cards data/cards-<DATE>.json`
   (public/index.html 주입 + public/data/cards-<DATE>.json 발행 + public/data/index.json 매니페스트)
   → `git add public/ && git commit && git push` (GitHub Pages 자동 빌드)

검증 통과가 10건 미만이면 통과분만 발행한다(억지 채움 금지). WebSearch 전면 실패 시
`scripts/ddg_fallback.py`로 보충하고, 그래도 0건이면 당일 발행을 보류하고 로그를 남긴다.

$ARGUMENTS
