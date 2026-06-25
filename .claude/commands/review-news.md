---
description: "당일 Top10 카드를 발행 전 표시하고 검토/제외 입력 대기"
---

`data/planning/top10-<DATE>.json`의 Top10을 표 형태로 보여주고, 발행에서 제외할
항목이 있는지 확인한다. Step 2(발행일)·Step 3(점수) 검증을 모두 통과한 항목만
포함되어 있음을 확인한다.

Autopilot enabled 시: Top10 전체를 그대로 통과시키고
`autopilot-logs/step-4-decision.md`에 결정 로그를 기록한다(근거: 검증 게이트가
이미 품질을 보장 — 절대 기준 1).

$ARGUMENTS
