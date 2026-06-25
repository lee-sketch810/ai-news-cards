# 오늘의 AI 뉴스 · 카드뉴스

매일 09:00 KST, 발행일 검증을 거친 AI 뉴스 Top 10을 한국어 요약 + 범용 인사이트('왜 중요한가') 카드뉴스로 자동 생성·배포하는 공개 사이트.

## 특징
- **당일성 검증 게이트** — 각 기사의 발행일 메타데이터를 확인해 KST 오늘/어제 윈도우만 통과. 미상·구문은 탈락.
- **절대 발행일 표기** — 상대표현('어제'·'오늘') 없음. 아카이브로 나중에 봐도 정확.
- **범용 인사이트** — 개인 맞춤이 아닌 산업 함의·일반 교훈.
- **정적 사이트** — 서버 없음. `public/index.html` + 임베드 JSON.

## 구조
```
public/index.html          카드뉴스 페이지 (GitHub Pages 루트)
data/cards-YYYY-MM-DD.json  당일 카드 (SOT 산출물)
data/archive/               날짜별 영구 보존
scripts/                    수집·검증·점수·렌더 파이프라인 (P1 결정론적 처리)
.claude/agents/             전문 sub-agent 5개
workflow.md                 전체 설계도 (Research→Planning→Implementation)
```

## 파이프라인
`build_queries → @news-collector(WebSearch) → dedupe → @date-verifier(WebFetch+verify_dates) → score_news → @news-scorer → @card-writer → render_cards → @news-deployer(push)`

## 배포
`public/`에 push되면 GitHub Actions가 GitHub Pages로 자동 배포한다(`.github/workflows/deploy-pages.yml`).

생성: AgenticWorkflow 하네스 (workflow-generator). API 추가 과금 없이 Claude Code 구독 내 sub-agent로 구동.
