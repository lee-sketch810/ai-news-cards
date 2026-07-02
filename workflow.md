# Daily AI News Card Pipeline

매일 KST 기준 '오늘' 발행된 AI 뉴스 중 의미 있는 Top 10을, 발행일 검증 + 한국어 요약 + 범용 인사이트가 붙은 카드뉴스로 자동 생성해 공개 사이트(GitHub Pages)에 배포한다.

## Overview

- **Input**: 일일 스케줄 트리거 (07:00 KST) + WebSearch 멀티앵글 쿼리 세트
- **Output**: 공개 카드뉴스 사이트 — `data/cards-YYYY-MM-DD.json` (SOT 산출물) + `public/index.html` (GitHub Pages)
- **Frequency**: Daily (09:00 KST, cron)
- **Autopilot**: enabled — 무인 일일 실행. `(human)` 게이트는 자동 승인하되 결정 로그 남김
- **pACS**: enabled

> **핵심 제약**: 수집 엔진은 **WebSearch 도구**(403 없음, 신선). DuckDuckGo 스크래퍼(`news_fetcher.py`)는 WebSearch 실패 시 **폴백 보조 소스**로만 사용. 모든 실행은 Claude Code 구독 내 sub-agent로 수행 → **API 추가 과금 0**.

---

## Inherited DNA (Parent Genome)

> This workflow inherits the complete genome of AgenticWorkflow.
> Purpose varies by domain; the genome is identical. See `soul.md §0`.

**Constitutional Principles** (adapted to this workflow's domain):

1. **Quality Absolutism** — 이 도메인에서 '품질'은 ① 당일성 정확도(틀린 날짜 0%), ② 출처 신뢰성(실제 URL·placeholder 금지), ③ 인사이트의 통찰력(단순 요약 초과)이다. 10건을 억지로 채우는 것보다 **검증된 N건**이 우선. 속도·분량 무시.
2. **Single-File SOT** — `.claude/state.yaml`에 일일 실행 상태 집중. 일일 산출물은 `data/cards-YYYY-MM-DD.json`.
3. **Code Change Protocol** — 스크립트(`scripts/*.py`) 변경 시 의도→영향→설계 3단계. 코딩 기준점(CAP-1 코딩 전 사고, CAP-2 단순성, CAP-3 목표 기반, CAP-4 외과적 변경) 내면화.

**Inherited Patterns**:

| DNA Component | Inherited Form |
|--------------|---------------|
| 3-Phase Structure | Research(수집·검증) → Planning(선별·점수) → Implementation(카드·배포) |
| SOT Pattern | `.claude/state.yaml` — single writer (Orchestrator) |
| 4-Layer QA | L0 Anti-Skip(파일·100B) → L1 Verification → L1.5 pACS → L2 Adversarial Review |
| P1 Hallucination Prevention | `verify_dates.py`·`score_news.py`·`dedupe.py` 결정론적 검증 |
| P2 Expert Delegation | @news-collector / @date-verifier / @news-scorer / @card-writer 분리 |
| Safety Hooks | `block_destructive_commands.py` — git push 등 위험 명령 차단 |
| Adversarial Review | `@reviewer` + `@fact-checker` — 발행일·요약 사실성 독립 검증 |
| Decision Log | `autopilot-logs/` — 일일 자동 승인 결정 추적 |
| Context Preservation | 일일 실행 간 상태 보존 (전일 아카이브 인덱스) |

**Domain-Specific Gene Expression**:
- **P1(데이터 정제)이 가장 강하게 발현** — 당일성 검증 게이트(`verify_dates.py`)와 점수 사전계산(`score_news.py`)이 이 워크플로우의 심장. AI는 '판단·작문'에만 집중하고, '날짜 참/거짓'과 '점수 산술'은 코드가 결정론적으로 처리한다.
- **P3(리소스 정확성)** — 모든 카드의 출처 URL은 실제·검증된 것이어야 하며 placeholder 금지.

---

## Research

### 1. 뉴스 수집 (Multi-angle Collection)
- **Pre-processing**: `scripts/build_queries.py` — 실행 시각의 KST 날짜를 쿼리에 주입하여 8개 앵글 쿼리 세트 생성 (모델 릴리스 / AI 도구·에이전트 / 교육·생산성 AI / 한국 AI / 정책·규제 / 빅테크 / 자동화 / 글로벌). placeholder 날짜 금지.
- **Agent**: `@news-collector`
- **Verification**:
  - [ ] 8개 앵글 쿼리 모두 WebSearch 실행 완료
  - [ ] 후보 기사 최소 25건 수집, 각 항목에 `title`·`url`·`snippet`·`source`·`snippet_date`(있으면) 포함
  - [ ] 모든 `url`이 실제 http(s) 링크 (placeholder·검색결과 페이지 자체 제외)
  - [ ] Step 2 검증이 필요로 하는 필드 구조로 출력 (source: Step 2 입력 호환)
- **Task**: Run WebSearch across the 8 query angles, collect candidate AI-news articles into a normalized JSON pool. Over-collect (noise removed downstream). Do NOT summarize yet.
- **Output**: `data/research/candidates-YYYY-MM-DD.json`
- **Review**: none
- **Translation**: none
- **Post-processing**: `scripts/dedupe.py` — URL 키 + 제목 유사도(≥0.75) 중복 제거.

### 2. 발행일 검증 게이트 (Publication-Date Verification) ⭐
- **Pre-processing**: none (에이전트가 WebFetch로 직접 검증)
- **Agent**: `@date-verifier`
- **Verification**:
  - [ ] 모든 후보에 대해 WebFetch로 발행일 메타데이터 확인 시도 (`article:published_time`·JSON-LD `datePublished`·og)
  - [ ] 통과 기사는 전부 발행일이 KST 윈도우(오늘 또는 어제) 내 — `scripts/verify_dates.py`로 판정
  - [ ] 각 통과 기사에 `verified_date`(YYYY-MM-DD, 절대표기)·`verification_status`(passed|yesterday|unverified) 기록
  - [ ] 메타데이터 없거나 윈도우 밖이면 **탈락** (보수적). 탈락 사유 로깅
  - [ ] 통과 건수가 10 미만이면 사유를 SOT에 기록 (억지로 채우지 않음 — 품질 우선)
- **Task**: For each candidate, WebFetch the article and extract its publication date from metadata. Pass `scripts/verify_dates.py` the parsed dates; keep only articles whose date falls in the KST today/yesterday window. Reject undated or stale articles. Annotate each survivor with absolute `verified_date` and status. Never invent or relative-format dates.
- **Output**: `data/research/verified-YYYY-MM-DD.json`
- **Review**: `@fact-checker` — 통과 기사의 발행일이 실제 원문과 일치하는지 표본 독립 검증 (당일성은 이 사이트의 생명선)
- **Translation**: none

---

## Planning

### 3. 선별·점수화 (Significance Scoring)
- **Pre-processing**: `scripts/score_news.py` — 각 기사의 신호(키워드 매칭·소스 권위·카테고리)에서 `중요도×0.3 + 실용성×0.4 + 관련성×0.3` 점수를 **결정론적으로 사전계산**. AI는 산술하지 않는다.
- **Agent**: `@news-scorer`
- **Verification**:
  - [ ] 사전계산 점수를 입력으로 받아 상위 Top 10 선정 (10 미만이면 전량 + 사유)
  - [ ] 카테고리 편중 방지 — 단일 카테고리가 Top10의 과반을 넘지 않도록 조정하고 조정 근거 기록
  - [ ] 각 선정 기사에 `score`·`rank`·`category`·선정 사유(source: Step 3 점수) 포함
  - [ ] 모든 선정 기사가 Step 2에서 발행일 검증을 통과한 항목 (source: Step 2)
- **Task**: Take the pre-computed scores from `score_news.py`, interpret them, and select the Top 10 most meaningful articles for a general practitioner audience. Balance categories. Output ranked list with rationale. Do not re-derive scores.
- **Output**: `data/planning/top10-YYYY-MM-DD.json`
- **Review**: none
- **Translation**: none

### 4. (human) Top10 발행 전 검토
- **Action**: 일별 Top10을 발행 전 빠르게 검토 (부적절·중복·오분류 제외)
- **Command**: `/review-news`
- **Autopilot Default**: 자동 승인 — Top10 전체를 그대로 통과시키되, Step 2·3 검증을 모두 통과한 항목만 포함되어 있음을 확인하고 결정 로그(`autopilot-logs/step-4-decision.md`) 기록. (근거: 절대 기준 1 — 검증 게이트가 이미 품질을 보장)

---

## Implementation

### 5. 카드 콘텐츠 작성 (Korean Summary + Universal Insight)
- **Pre-processing**: none (입력은 Step 3 Top10 JSON)
- **Agent**: `@card-writer`
- **Verification**:
  - [ ] Top10 각 기사마다 카드 1장 — `category`·`verified_date`(절대표기)·`headline`(한국어)·`summary`(1줄)·`points`(3개)·`insight`·`source_url`·`verification_status` 필드 완비
  - [ ] `insight`는 **범용('왜 중요한가')** — 개인 맥락('그래서 나에게'·특정 사용자 지칭) **금지**
  - [ ] 날짜 표기에 상대표현('어제'·'오늘'·'N일 전') **전무**, 절대 발행일(YYYY-MM-DD)만
  - [ ] 모든 `source_url`이 Step 2에서 검증된 실제 링크 (source: Step 2)
  - [ ] 한국어 네이티브 — 번역체 아님, 판매용 카피 수준의 자연스러움
- **Task**: Write one news card per Top-10 article in native Korean. Each card: catchy Korean headline, one-line summary, three key bullet points, and a UNIVERSAL "왜 중요한가" insight (industry implication / general lesson — never personalized). Use only absolute publication dates. Output structured JSON.
- **Output**: `data/cards-YYYY-MM-DD.json` (SOT 산출물)
- **Review**: `@reviewer + @fact-checker` — 고위험 공개 콘텐츠: 요약의 사실 정합성(@fact-checker) + 카드 구조·필드 완전성·인사이트 범용성(@reviewer)
- **Translation**: none (이미 한국어 원본)

### 6. 렌더 + 배포 (Render & Deploy)
- **Pre-processing**: `scripts/render_cards.py` — 최신 카드를 `public/index.html`의 `/* CARDS_DATA_START */ … /* CARDS_DATA_END */` 마커에 주입하고, 에디션을 `public/data/cards-YYYY-MM-DD.json`으로 발행하며, 날짜 매니페스트 `public/data/index.json`을 재생성. (서빙 데이터는 public/ 하위에 두어 GitHub Pages가 직접 서빙 → 아카이브/검색 fetch 가능)
- **Agent**: `@news-deployer`
- **Verification**:
  - [ ] `public/index.html`에 Top10(또는 검증 통과분) 카드가 모두 렌더됨
  - [ ] `data/archive/cards-YYYY-MM-DD.json` 저장 완료 (날짜별 아카이브 누적)
  - [ ] 모든 카드 출처 링크가 클릭 가능한 유효 URL (placeholder 0)
  - [ ] 날짜 네비게이션(아카이브)과 카테고리 필터가 동작
  - [ ] GitHub Pages 배포 커밋·푸시 완료 (또는 Autopilot 미승인 시 푸시 보류 + 로그)
- **Task**: Run `render_cards.py` to inject cards into the static HTML and archive the JSON. Verify the page renders all cards with valid source links, then commit and push to the GitHub Pages branch.
- **Output**: `public/index.html` (배포본) + git push
- **Review**: none
- **Translation**: none

### 7. Notion 누적 동기화 (Accumulating Archive)
- **Pre-processing**: none (입력은 `data/cards-YYYY-MM-DD.json`)
- **Agent**: `@news-deployer` (Notion MCP)
- **Verification**:
  - [ ] 당일 카드가 Notion DB "AI 뉴스 아카이브"(data_source `af0009aa-29ea-4d16-8ef6-2689de6eda95`)에 적재됨
  - [ ] 속성 매핑 정확: 헤드라인·발행일(verified_date)·수집일(edition date)·카테고리·요약·인사이트·출처·출처명·검증(passed→당일/yesterday→전일)
  - [ ] 동일 수집일+헤드라인 중복 미삽입 (idempotent)
  - [ ] 개인 필드(읽음·북마크·메모·활용태그)는 비워 둠 (사용자 몫)
- **Task**: Upsert each day's cards into the Notion archive DB via Notion MCP create-pages; the 3 points become the page body. Non-blocking: log and continue on failure (site deploy is the primary output).
- **Output**: Notion DB rows (파생 싱크 — SOT 아님)
- **Review**: none
- **Translation**: none

> **SOT 원칙 (절대 기준 2)**: Notion은 `cards-*.json`의 **파생 싱크(거울)**다. 진실원천은 사이트의 카드 JSON이며, Notion 쓰기 실패가 파이프라인을 막지 않는다.

### 8. 분석 인덱스 재생성 (엔티티·트렌드·검색·스레드)
- **Pre-processing**: none (입력은 `public/data/cards-*.json` 전체 — 아카이브 재스캔)
- **Agent**: `@news-deployer`
- **Verification**:
  - [ ] `scripts/build_analytics.py` 실행 → `public/data/entities.json`·`trends.json`·`search-index.json` 재생성
  - [ ] `scripts/build_threads.py` 실행 → `public/data/threads.json` 재생성, 카드에 `thread_ids` 주입
  - [ ] 최신 에디션이 `index.html`에 엔티티·스레드 태그 포함해 재임베드됨
- **Task**: Run `build_analytics.py` then `build_threads.py` over the full archive. Both are deterministic (P1) — no AI judgment involved.
- **Output**: `public/data/{entities,trends,search-index,threads}.json`
- **Review**: none
- **Translation**: none

### 9. 일일 다이제스트 초안 생성 (Gmail Draft — 발송 안 함)
- **Pre-processing**: `scripts/build_digest.py --cards data/cards-YYYY-MM-DD.json` — 당일 카드+종합인사이트를 이메일 HTML로 변환
- **Agent**: `@news-deployer` (Gmail MCP)
- **Verification**:
  - [ ] 다이제스트 제목이 `[오늘의 AI 뉴스] <날짜> · <오늘의 흐름 제목>` 형식
  - [ ] 카드 전부(헤드라인·요약·포인트·인사이트·출처)가 본문에 포함
  - [ ] Gmail MCP `create_draft`로 **초안만** 생성 — 발송(send) 호출 금지
  - [ ] 실패 시 논블로킹 (사이트 배포가 우선 산출물)
- **Task**: Build the HTML digest, then call Gmail MCP `create_draft` (never send) so the user can review and send manually.
- **Output**: Gmail 초안함의 임시 메일 1건
- **Review**: none
- **Translation**: none

> **안전 원칙**: 이메일 "발송"은 매번 사용자 명시 승인이 필요한 행위다(절대 기준 외부의 시스템 안전 규칙). 이 단계는 **초안 생성까지만** 자동화하고, 실제 발송 버튼은 항상 사용자가 누른다.

---

## Claude Code Configuration

### Sub-agents

```yaml
# .claude/agents/news-collector.md
---
name: news-collector
description: "당일 AI 뉴스를 WebSearch 멀티앵글로 수집하는 에이전트. '뉴스 수집', '오늘 AI 뉴스 모아줘' 시 사용."
model: sonnet            # 반복 수집 — 안정적 처리로 충분
tools: WebSearch, WebFetch, Read, Write
permissionMode: default
maxTurns: 30
memory: project
---
You collect candidate AI-news articles for a daily Korean card-news site.
Run WebSearch across the provided query angles, normalize results into JSON
(title, url, snippet, source, snippet_date). Over-collect; never summarize or
judge yet. Only real article URLs — never search-result pages or placeholders.

# .claude/agents/date-verifier.md
---
name: date-verifier
description: "수집된 뉴스의 발행일을 WebFetch로 검증해 KST 당일/어제 윈도우만 통과시키는 게이트. '발행일 검증', '당일성 확인' 시 사용."
model: sonnet
tools: WebFetch, Read, Write, Bash
permissionMode: default
maxTurns: 40
memory: project
---
You are the publication-date verification gate — the lifeline of this site.
For each candidate, WebFetch the article and extract its publication date from
metadata (article:published_time, JSON-LD datePublished, og). Feed parsed dates
to scripts/verify_dates.py; keep only KST today/yesterday articles. Reject
undated or stale items conservatively. Annotate survivors with absolute
verified_date (YYYY-MM-DD) and status. Never invent or relative-format dates.

# .claude/agents/news-scorer.md
---
name: news-scorer
description: "사전계산된 점수로 의미 있는 Top10을 선정하고 카테고리 균형을 맞추는 에이전트. '뉴스 선별', '점수화', 'Top10' 시 사용."
model: sonnet
tools: Read, Write, Bash
permissionMode: default
maxTurns: 20
memory: project
---
You select the Top 10 most meaningful AI-news items for a general practitioner
audience. Scores are pre-computed by scripts/score_news.py — interpret, do not
re-derive. Balance categories so one topic does not dominate. Output a ranked
list with rationale. If fewer than 10 pass verification, output all with a note.

# .claude/agents/card-writer.md
---
name: card-writer
description: "검증된 뉴스를 한국어 요약 + 범용 인사이트 카드로 작성. '카드 작성', '뉴스 요약 카드', '인사이트 카드' 시 사용."
model: opus              # 최종 산출물 품질 핵심 — 자연스러운 한국어 + 통찰
tools: Read, Write
permissionMode: default
maxTurns: 25
memory: project
---
You write daily AI-news cards in native Korean. Per article: catchy Korean
headline, one-line summary, three key points, and a UNIVERSAL "왜 중요한가"
insight (industry implication or general lesson — NEVER personalized, never
"그래서 나에게"). Use only absolute publication dates (YYYY-MM-DD); no relative
expressions. Output structured JSON. Sales-copy-level naturalness is the bar.

# .claude/agents/news-deployer.md
---
name: news-deployer
description: "카드 JSON을 정적 HTML에 주입·아카이브하고 GitHub Pages에 배포. '배포', '렌더', '사이트 갱신' 시 사용."
model: sonnet
tools: Read, Write, Bash
permissionMode: default
maxTurns: 20
memory: project
---
You render cards into the static site and publish. Run scripts/render_cards.py
to inject cards into public/index.html and archive the JSON. Verify all cards
render with valid source links, then commit and push to the GitHub Pages branch.
```

> **모델 선택 근거 (절대 기준 1)**: `card-writer`만 opus (최종 한국어 품질·인사이트가 결과물의 핵심). 수집·검증·점수·배포는 sonnet으로 안정적·결정론적 처리.

#### Sub-agent Memory Scope
모든 에이전트 `project` 스코프 — SOT 읽기 전용, 산출물 파일만 생성. SOT 쓰기는 Orchestrator 단독.

### SOT (상태 관리)
- **SOT 파일**: `.claude/state.yaml`
- **쓰기 권한**: Orchestrator 단독 (단일 쓰기 지점)
- **에이전트 접근**: 읽기 전용 — 각 단계 산출물 JSON만 디스크에 생성
- **품질 우선 조정**: 기본 패턴 적용 (순차 sub-agent 파이프라인 — Agent Team 불필요. 단계 간 정확한 맥락 전달이 품질의 핵심이므로 순차 호출이 최적)
- **일일 산출물 vs SOT**: SOT는 당일 실행 진행 상태(current_step·outputs·검증 이력)를 추적. 카드 데이터 자체는 `data/cards-YYYY-MM-DD.json`(산출물) + `data/archive/`(영구 보존).

### Context Injection 패턴
- Step 1→2: 후보 JSON < 50KB → Pattern A (파일 경로 전달)
- Step 2 WebFetch: 후보가 25건 초과 시 Pattern C (청크 분할 검증) 고려
- Step 3·5: 정제된 JSON 입력 → Pattern A

### Scripts (P1 결정론적 처리)

| 스크립트 | 역할 | 단계 |
|---------|------|------|
| `scripts/build_queries.py` | 실행 KST 날짜 주입 + 8앵글 쿼리 세트 생성 | 1 (Pre) |
| `scripts/dedupe.py` | URL키 + 제목 유사도 중복 제거 | 1 (Post) |
| `scripts/verify_dates.py` | 발행일 파싱 + KST 오늘/어제 윈도우 판정 (검증 게이트 핵심) | 2 (Pre) |
| `scripts/score_news.py` | 중요도×실용성×관련성 점수 사전계산 | 3 (Pre) |
| `scripts/render_cards.py` | cards JSON → index.html 마커 주입 + 아카이브 | 6 (Pre) |

> 폴백: `scripts/ddg_fallback.py`는 상위 `news_fetcher.py`(throttle+KST윈도우 수리본)를 감싸 WebSearch 전면 실패 시에만 후보를 보충.

### Slash Commands

```markdown
# .claude/commands/review-news.md
---
description: "당일 Top10 카드를 발행 전 표시하고 검토/제외 입력 대기"
---
오늘의 Top10 뉴스 카드를 표 형태로 보여주고, 발행에서 제외할 항목이 있는지 확인한다.
Step 2(발행일)·Step 3(점수) 검증을 모두 통과한 항목만 포함되어 있음을 확인한다.
$ARGUMENTS

# .claude/commands/run-daily-news.md
---
description: "Daily AI News Card 파이프라인 전체 실행 (수집→검증→점수→카드→배포)"
---
ai-news-cards/workflow.md를 따라 1~6단계를 순차 실행한다. Autopilot enabled.
$ARGUMENTS
```

### Hooks

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{
          "type": "command",
          "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/scripts/block_destructive_commands.py",
          "timeout": 15
        }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [{
          "type": "prompt",
          "prompt": "방금 저장한 카드 JSON에 상대 날짜 표현('어제'·'오늘'·'N일 전')이 있으면 지적하고, 모든 source_url이 실제 링크인지 확인하라.",
          "model": "haiku"
        }]
      }
    ]
  }
}
```

### Scheduled Trigger (일일 자동 실행)

```yaml
# 매일 09:00 KST — Claude Code 스케줄 태스크 (sch-news 인프라 재사용)
schedule:
  cron: "0 0 * * *"         # 00:00 UTC = 09:00 KST
  command: "/run-daily-news"
  autopilot: enabled
  note: "구독 내 sub-agent 실행 — API 추가 과금 0"
```

### Required Skills
- 없음 (자체 에이전트 + 스크립트로 충분)

### MCP Servers
- 없음 (WebSearch·WebFetch 내장 도구 사용). 선택: Google Drive MCP로 아카이브 백업 시 추가.

### Runtime Directories

```yaml
runtime_directories:
  verification-logs/:        # step-N-verify.md (L1 검증 결과)
  autopilot-logs/:           # step-N-decision.md ((human) 자동 승인 로그)
  pacs-logs/:                # step-N-pacs.md (pACS 자체 평가)
  review-logs/:              # step-2/5-review.md (Adversarial Review)
  data/research/:            # 수집·검증 중간 산출물
  data/planning/:            # Top10 중간 산출물
  data/archive/:             # 날짜별 카드 영구 보존
```

> gitignore 권장: `verification-logs/`·`autopilot-logs/`·`pacs-logs/`·`data/research/`·`data/planning/` (런타임). `data/archive/`·`data/cards-*.json`·`public/`은 커밋 (배포 대상).

### Error Handling

```yaml
error_handling:
  on_agent_failure:
    action: retry_with_feedback
    max_attempts: 3
    escalation: human

  on_validation_failure:
    action: retry_or_rollback
    retry_with_feedback: true
    rollback_after: 3

  on_collection_empty:               # WebSearch가 후보 0건
    action: invoke_ddg_fallback      # scripts/ddg_fallback.py로 보충
    then: if_still_empty_skip_day    # 그래도 0이면 당일 발행 보류 + 로그 (가짜 발행 금지)

  on_few_verified:                   # 검증 통과 < 10
    action: publish_available        # 통과분만 발행 (억지 채움 금지 — 품질 우선)

  on_hook_failure:
    action: log_and_continue

  on_context_overflow:
    action: save_and_recover
```

### pACS Logs (enabled)

```yaml
pacs_logging:
  log_directory: "pacs-logs/"
  log_format: "step-{N}-pacs.md"
  dimensions: [F, C, L]              # Factual Grounding(발행일·출처 사실성) / Completeness(필드 완비) / Logical Coherence(인사이트 타당성)
  scoring: "min-score"
  triggers:
    GREEN: "≥ 70 → auto-proceed"
    YELLOW: "50-69 → proceed with flag"
    RED: "< 50 → rework or escalate"
  protocol: "AGENTS.md §5.4"
```
