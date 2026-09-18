---
description: "실전 팁 중심 Daily AI News 파이프라인 전체 실행. 매일 09:00 KST."
---

`workflow.md`에 따라 순차 실행한다. Autopilot enabled.

1. `python scripts/build_queries.py --out data/research/queries.json`
2. `@news-collector` → practice 20건 + signal 6건 목표
3. `python scripts/dedupe.py --in <candidates> --out <candidates>`
4. `@date-verifier` → 발행일 + `actionable_facts` 추출
5. `python scripts/verify_dates.py --in <candidates> --out <verified> --window 1`
6. `python scripts/score_news.py --in <verified> --out <scored>`
7. `@news-scorer` → tip 6 / tool 2 / signal 2 슬롯 선정
8. `@card-writer` → 구조화된 실전 팁 작성
9. `python scripts/check_tip_novelty.py --cards <cards> --history public/data --days 14`
10. reviewer + fact-checker: 팁 UI 경로·명령어가 actionable_facts에 실제 있는지 표본 검증
11. `python scripts/render_cards.py --cards <cards>`
12. git add/commit/push

## 실패 정책

- practice 후보 부족: signal로 충원하지 않고 적은 수로 발행.
- 팁 품질 게이트 실패: 최대 3회 재작성, 계속 실패하면 해당 카드 제외.
- WebSearch 전면 실패: fallback을 1회 사용. 그래도 0건이면 발행 보류.
- KST 10:30까지 발행 파일이 없으면 실패 로그와 알림을 남긴다.
- 전날 데이터를 오늘 날짜로 재포장하지 않는다.

$ARGUMENTS
