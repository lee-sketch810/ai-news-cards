---
name: webfetch-blocked-domains
description: Domains that consistently return 403/429 to WebFetch, breaking direct date verification for those candidates
metadata:
  type: project
---

Bloomberg (`www.bloomberg.com`), Axios (`www.axios.com`), CNBC (`www.cnbc.com`), and
`openai.com` blog posts consistently return HTTP 403 to WebFetch (confirmed across
multiple retries on 2026-08-11 run). VentureBeat (`venturebeat.com`) frequently
returns HTTP 429 (rate limit) rather than 403 — retrying after other fetches
sometimes helps but not reliably.

**Why:** These sites have bot/WAF protection that blocks the WebFetch tool's fetcher
outright, independent of paywall status — even Bloomberg articles that are usually
paywalled still 403 before any paywall would even render.

**How to apply:** When a candidate's URL is on one of these domains and WebFetch
fails, do not silently invent `raw_published`. Try `http://archive.org/wayback/available?url=<url-without-protocol>`
as a fallback independent check — it sometimes returns a Wayback Machine snapshot
timestamp that corroborates (or fails to corroborate) freshness without needing to
render the original page. If no snapshot exists either, leave `raw_published` null
and rely on corroboration from sibling articles covering the same story from
fetchable domains, but report this explicitly as a caveat rather than treating it
as independently confirmed.

**Known downstream effect:** `scripts/verify_dates.py` falls back to `snippet_date`
when `raw_published` is null/empty (`art.get("raw_published") or art.get("snippet_date")`).
This means candidates from blocked domains can still pass the window filter purely
on the Step-1 `snippet_date` guess, without genuine WebFetch-based confirmation. Flag
any such passes explicitly in the final report so downstream consumers know the
confidence level is lower for those specific candidates. See [[date-catch-examples]].
