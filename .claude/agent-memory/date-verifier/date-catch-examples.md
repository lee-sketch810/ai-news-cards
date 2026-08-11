---
name: date-catch-examples
description: Real examples where snippet_date from Step 1 (research) was wrong and WebFetch verification caught it — validates why this gate matters
metadata:
  type: project
---

On the 2026-08-11 run, `data/research/candidates-2026-08-11.json` had several
candidates whose Step-1 `snippet_date` did not match the article's actual
publication date confirmed via WebFetch:

- `c42` (CIO Korea, "모두의 AI" 챗봇 지원사업 공고): snippet_date was `2026-08-11`
  (today), implying it was fresh. WebFetch of the byline showed the article was
  actually published `2026-07-14` — nearly a month stale. The snippet content
  described an application deadline of "today, Aug 11 5pm," but that appears to be
  an artifact of the article being about a recurring/ongoing deadline, not a same-day
  report.
- `c50` (Lawtimes, AI 기본법 시행령 개정안): snippet_date was `2026-07-14`, but the
  actual article byline date was `2026-06-25` (the article previews an upcoming
  cabinet decision, published before it happened).

**Why:** Confirms the premise of this verification gate — `snippet_date` (likely
scraped from search result snippets or inferred from URL patterns in Step 1) is not
reliable enough on its own and must be checked against real article metadata/byline
before trusting freshness. See [[webfetch_blocked_domains]] for the counter-case
where verification isn't possible at all.

**How to apply:** Never skip WebFetch verification for candidates just because
`snippet_date` looks like it's in the today/yesterday window — that's exactly the
kind of candidate most worth double-checking, since a false "today" snippet_date is
the most dangerous failure mode for this site (an actually-stale article getting
published as new).
