# ai-news-cards

한국어 실전 AI 팁 카드뉴스 사이트(https://ai-news.wiselab.kr)의 생성 파이프라인.
설계·결정 이력은 `workflow.md`, 실행 순서는 `.claude/commands/run-daily-news.md`.

## 코드를 읽어도 모르는 것

- **독자**: 1인 실무자, 교육·콘텐츠 제작자. 기업 거버넌스 조언이 아니라 "혼자 오늘 안에 할 수 있는 일"을 원한다.
- **제품의 핵심은 `tip`**. 요약은 팁의 문맥일 뿐이다. 근거 없는 팁은 없는 것보다 나쁘다.
- **문체**: 네이티브 한국어, 번역투 금지. 날짜는 항상 절대표기(YYYY-MM-DD).
- **배포 경로**: 사용자 Windows PC의 작업 스케줄러가 돌린다. 생성(`run_daily_news.bat`, 09:00)과
  배포(`auto_publish.bat` → `deploy_to_iwinv.bat`, scp)는 별개 작업이다.
  GitHub 저장소는 백업일 뿐이고 push해도 라이브 사이트는 바뀌지 않는다.
- **이메일**은 Gmail 초안까지만. 발송은 사용자가 직접 한다.

## 작업 규칙

- `scripts/*.py`를 고칠 때는 결정론적 동작을 유지하고, 변경 후 해당 스크립트를 최근 에디션으로 한 번 돌려 본다.
- 카드·에디션 데이터(`data/`, `public/data/`)를 손으로 고쳐 과거 날짜를 바꾸지 않는다.
