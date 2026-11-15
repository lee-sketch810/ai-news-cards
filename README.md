# 오늘의 AI 뉴스 · 카드뉴스

매일 09:00 KST, 발행일 검증을 거친 AI 소식을 원문 근거가 있는 '실전 팁' 중심 카드뉴스로 자동 생성·배포하는 공개 사이트.

## 특징
- **당일성 검증 게이트** — 각 기사의 발행일 메타데이터를 확인해 KST 오늘/어제 윈도우만 통과. 미상·구문은 탈락.
- **절대 발행일 표기** — 상대표현('어제'·'오늘') 없음. 아카이브로 나중에 봐도 정확.
- **실전 팁 검증** — 팁의 메뉴 경로·명령어·숫자는 원문에서 추출한 근거와 독립 에이전트가 대조.
- **정적 사이트** — 서버 없음. `public/index.html` + 임베드 JSON.

## 구조
```
public/index.html          카드뉴스 페이지 (iwinv 서버 웹 루트로 업로드)
data/cards-YYYY-MM-DD.json  당일 카드 (SOT 산출물)
data/archive/               날짜별 영구 보존
scripts/                    수집·검증·점수·렌더 파이프라인 (P1 결정론적 처리)
.claude/agents/             전문 sub-agent 6개
workflow.md                 전체 설계도 (Research→Planning→Implementation)
```

## 파이프라인
`build_queries → @news-collector → dedupe → @date-verifier(발행일+actionable_facts) → score_news → @news-scorer → @card-writer → check_tip_novelty → @tip-verifier → @news-deployer(렌더·분석·RSS·로컬 커밋)`

## 배포
2026-07부터 GitHub Pages 배포는 중단하고 iwinv 서버(`https://ai-news.wiselab.kr`)로 완전히 이전했다.
`auto_publish.bat`이 로컬 커밋(이력용) 후 `deploy_to_iwinv.bat`을 호출해 `public/`을 서버 웹 루트(`/var/www/ai-news-cards`)로 scp 업로드한다.
서버 최초 설정은 `IWINV_SETUP.md` + `server_finish_setup.sh` 참고.

생성: AgenticWorkflow 하네스 (workflow-generator). API 추가 과금 없이 Claude Code 구독 내 sub-agent로 구동.
