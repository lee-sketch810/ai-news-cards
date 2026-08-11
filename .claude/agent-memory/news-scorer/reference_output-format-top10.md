---
name: output-format-top10
description: JSON schema/conventions used for data/planning/top10-YYYY-MM-DD.json output files in the ai-news-cards pipeline.
metadata:
  type: reference
---

`data/planning/top10-YYYY-MM-DD.json` structure (observed in prior files like
`top10-2026-08-10.json` and produced for `top10-2026-08-11.json`):

```
{
  "date": "YYYY-MM-DD",
  "selected": [
    { ...all fields carried over from the scored article object (id, title, url, snippet,
      source, category, snippet_date, raw_published, verified_date, verification_status,
      signals, score, rank)... ,
      "story_group": "<optional, added when de-duplicating near-duplicate coverage>",
      "selection_reason": "<optional, one-line reason — added per specific task instructions>"
    },
    ...
  ],
  "rationale": "<top-level string explaining overall category-balance / selection tradeoffs>"
}
```

Notes:
- The `rank` field is normally carried over from the scorer's global rank, not renumbered
  within the selection (see `top10-2026-08-10.json`).
- `rationale` is always a single top-level string, not per-item, in past outputs — but when
  a task explicitly asks for "a one-line selection reason" per item, add a per-item
  `selection_reason` field (done for 2026-08-11) without breaking the existing schema.
- Related: [[low-diversity-days]] for when/why articles get dropped rather than force-filled to 10.
