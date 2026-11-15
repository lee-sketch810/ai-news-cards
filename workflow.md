# Daily AI News Card Pipeline

매일 09:00 KST, 발행일이 검증된 AI 소식을 **"오늘 바로 따라 할 수 있는 실전 팁"** 중심 카드뉴스로
만들어 https://ai-news.wiselab.kr 에 발행한다.

- 실행: Windows 작업 스케줄러 → `run_daily_news.bat` → `claude -p "/run-daily-news"` (생성만)
- 배포: 별도 작업 → `auto_publish.bat`(로컬 커밋) → `deploy_to_iwinv.bat`(scp로 `public/` 업로드)
- GitHub: 소스 백업용. **push로는 라이브 사이트가 바뀌지 않는다** (2026-07 GitHub Pages 폐기).
- 단계별 실행 순서는 `.claude/commands/run-daily-news.md`, 각 단계의 상세 규칙은 `.claude/agents/*.md`가 기준이다.
  이 문서는 설계 의도와 결정 이력만 담는다.

## 품질 원칙

1. **틀린 날짜 0건.** 발행일 메타데이터로 KST 당일/전일만 통과. 날짜를 추측하지 않는다.
2. **지어낸 팁 0건.** 팁의 메뉴 경로·명령어·숫자는 원문에서 뽑은 `actionable_facts`에 있는 것만 쓴다.
3. **억지로 10장 채우지 않는다.** 재료가 없으면 적게 발행한다. 전날 데이터를 오늘로 재포장하지 않는다.
4. **판단은 AI, 산술·판정은 코드.** 날짜 판정·점수·중복·팁 패턴 검사는 `scripts/`가 결정론적으로 한다.
5. **쓰는 쪽과 검증하는 쪽을 분리한다.** 날짜는 `date-verifier`, 팁 사실성은 `tip-verifier`가 작성자와 독립적으로 본다.

## 흐름

| # | 단계 | 담당 | 산출물 |
|---|------|------|--------|
| 0 | 빠진 날짜 자동 보충 (gap check) | orchestrator | — |
| 1 | 14개 쿼리 생성 (practice 10 / signal 4) | `build_queries.py` | `data/research/queries.json` |
| 2 | 수집 → 중복 제거 | `news-collector` → `dedupe.py` | `data/research/candidates-DATE.json` |
| 3 | 발행일 검증 + 팁 근거(`actionable_facts`) 추출 | `date-verifier` → `verify_dates.py` | `data/research/verified-DATE.json` |
| 4 | 점수 → 슬롯 선정 (tip 6 / tool 2 / signal 2) | `score_news.py` → `news-scorer` | `data/planning/top10-DATE.json` |
| 5 | 카드 작성 → 팁 패턴 게이트 | `card-writer` → `check_tip_novelty.py` | `data/cards-DATE.json` |
| 6 | 팁 사실성 독립 검증 | `tip-verifier` | `review-logs/tip-verify-DATE.json` |
| 7 | 렌더·분석·주간종합·RSS·다이제스트 초안·로컬 커밋 | `news-deployer` | `public/`, Gmail 초안 |

`(human)` 검토(`/review-news`)는 Autopilot에서 자동 통과한다. 수동으로 볼 때만 쓴다.

## 실패 처리

- 후보 0건: 1회 재시도 후 그날은 발행 보류 + 로그. 가짜 발행 금지.
- 검증 통과 < 10: 통과분만 발행.
- 팁 게이트(5·6) 실패: 해당 카드만 최대 3회 재작성, 그래도 실패하면 제외.
- 다이제스트 초안 실패: 무시하고 진행 (사이트가 주 산출물).
- 스케줄이 하루 이상 빠져도 다음 실행의 Step 0이 자동으로 따라잡는다. 당일분은 검증 실패 시 비워 두고 다음 실행에서 채운다.

## 결정 이력

- **2026-07** — GitHub Pages → iwinv 서버로 이전. git은 로컬 이력용, push 안 함.
- **2026-08-01** — 쿼리를 카테고리당 2앵글로 확장. 기존 8앵글은 검증 통과가 하루 3~6건뿐이었다.
- **2026-08-01** — 주간 종합(`overview.json`)을 **매일** 재생성. 이 단계가 빠져 한 달간 07-01에 고정됐던 버그가 있었다.
- **2026-08-01** — 이메일 뉴스레터 대신 RSS(`public/rss.xml`) 채택. iwinv는 메일 서버가 없고(25번 포트 차단),
  이메일 수집은 개인정보 보관·수신거부 책임이 생긴다. 구독 수요가 확인되면 Resend 등 메일 API를 재검토한다.
- **2026-08-10** — 생성 스케줄이 사라져 사이트가 08-06에 4일간 멈췄던 사고 → `run_daily_news.bat` 재생성, Step 0 gap check 도입.
- **2026-09 (practical-tips v2)** — "범용 인사이트" 중심에서 "실전 팁" 중심으로 전환. practice/signal 2티어 수집,
  `actionable_facts` 추출, tip 객체 스키마, `check_tip_novelty.py`(2026-09-14~16 팁 24건 중 14건이 같은 만능 패턴이었음).
- **2026-11** — 하네스 정리: 존재하지 않는 훅·로그 체계(pACS 등) 서술 제거, `tip-verifier` 추가,
  배포 단계(분석·주간종합·RSS)를 `run-daily-news`에 다시 연결.

## 안전 규칙

- 이메일은 **초안만** 만든다. 발송은 항상 사용자가 직접 한다.
- 카드에 placeholder URL이나 상대 날짜('어제'·'오늘'·'N일 전')가 있으면 커밋하지 않는다.
