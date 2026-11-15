---
description: "실전 팁 중심 Daily AI News 파이프라인 전체 실행. 매일 09:00 KST."
---

`workflow.md`에 따라 순차 실행한다. Autopilot enabled — 사람 확인을 기다리지 않는다.

0. Gap check: `public/data/index.json`의 최신 날짜 다음날부터 어제까지 빠진 날짜가 있으면
   그 날짜들부터 1~12단계를 먼저 돌린다.
1. `python scripts/build_queries.py --out data/research/queries.json`
2. `@news-collector` → practice 20건 + signal 6건 목표
3. `python scripts/dedupe.py --in <candidates> --out <candidates>`
4. `@date-verifier` → 발행일 + `actionable_facts` 추출
5. `python scripts/verify_dates.py --in <candidates> --out <verified> --window 1`
6. `python scripts/score_news.py --in <verified> --out <scored>`
7. `@news-scorer` → tip 6 / tool 2 / signal 2 슬롯 선정
8. `@card-writer` → 구조화된 실전 팁 작성
9. `python scripts/check_tip_novelty.py --cards <cards> --history public/data --days 14`
10. `@tip-verifier` → 팁의 경로·명령어·숫자를 원문 근거와 대조
    - `fix` 카드: 판정 노트를 `@card-writer`에 넘겨 해당 카드만 재작성 → 9·10 재실행 (최대 3회)
    - `drop` 카드 또는 3회 실패: 그 카드를 제외 (signal로 대체하지 않음)
11. `@news-deployer` → render → analytics → threads → analytics → overview → RSS → 다이제스트 초안
12. 로컬 커밋만 한다. **push 하지 않는다** (배포는 `auto_publish.bat` → iwinv scp가 담당).

## 실패 정책

- practice 후보 부족: signal로 충원하지 않고 적은 수로 발행.
- 팁 품질 게이트(9·10) 실패: 최대 3회 재작성, 계속 실패하면 해당 카드 제외.
- WebSearch 전면 실패: 1회 재시도. 그래도 0건이면 그날은 발행 보류하고 로그만 남긴다.
- KST 10:30까지 발행 파일이 없으면 실패 로그와 알림을 남긴다.
- 전날 데이터를 오늘 날짜로 재포장하지 않는다.

$ARGUMENTS
