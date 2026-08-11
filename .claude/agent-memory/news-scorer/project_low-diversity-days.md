---
name: low-diversity-days
description: How to handle days where few underlying stories dominate the verified article pool (e.g. 13 articles = only 3 real events) — collapse near-duplicates instead of forcing 10 picks.
metadata:
  type: project
---

On 2026-08-11, `data/planning/scored-2026-08-11.json` had 13 verified articles but they traced
to only 3 underlying events (Meta Muse Glimmer open-weight model release, Anthropic Claude Code
auto-mode default, Nvidia $500B Wall Street AI financing deal) — each covered by 3-5 outlets.

**Rule applied**: pick one best-sourced "primary" card per underlying story (highest score /
most authoritative source). Only add a secondary card from the same story if it contributes
genuinely new information — a different technical angle (e.g. quantization/hardware specs vs.
general market framing), a different mechanism explanation (e.g. "how the classifier permission
model works" vs. "safety test results"), or a contrasting angle (e.g. market skepticism/stock
drop vs. the corporate press release). Pure restatements of the same fact from a different
outlet are dropped even if their score would otherwise place them in the top 10.

**Result**: 6 final cards instead of 10, evenly split across 3 categories (2/2/2). This is the
expected outcome per workflow.md's "10건 미만이면 통과분만 발행한다(억지 채움 금지)" clause —
low headcount from date-verification collapsing further via de-duplication is normal and should
not be padded out with near-duplicate coverage just to hit 10.

**Why**: Publishing 5 near-identical Meta Muse Glimmer cards (or 5 near-identical Nvidia
financing cards) back-to-back would violate the category-balance / non-redundant-coverage
principle even though every individual article passed the Step-2 date-verification gate —
verification passing is necessary but not sufficient for inclusion.

**How to apply**: Whenever a scored file shows multiple articles clustering on the same
headline/story (same company + same announcement, near-identical snippets), treat verification
pass-rate and score-rank as necessary filters, not sufficient ones — run an explicit "does this
add new information beyond the primary pick?" check before including a same-story secondary.
See [[output-format-top10]] for the JSON schema this produced.
