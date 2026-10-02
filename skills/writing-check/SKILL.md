---
name: writing-check
description: Check a draft for the patterns that make writing read as machine-generated (dashes inside sentences, "it's not X, it's Y", tier-one words like "leverage" and "delve", filler, hedges, uniform paragraphs) and fix them. Use before handing over any draft meant for people, or when the user says a draft "reads like AI", "sounds robotic" or "clean this up".
---

# Writing check

A pattern belongs on the list only if it shows up constantly in generated text and rarely in
careful human writing. The full catalogue with examples is [tells.md](tells.md).

## Steps
1. Save the draft to a file (or pipe it) and run the checker. It has no dependencies:
   `python3 scripts/slop_check.py draft.md` (paths relative to this skill's folder), or
   `cat draft.md | python3 scripts/slop_check.py -`.
2. Fix every flag with the replacement it prints: a period or comma for a dash, "is" for
   "serves as", the plain word for a tier-one word, the direct statement for a manufactured
   contrast.
3. Read the draft once more for what a regex cannot see (last section of [tells.md](tells.md)):
   sentences that parse but say nothing, a register that does not fit where the text is going,
   and length that grew past what was asked.
4. Run the checker again. Hand over the draft with the flag count before and after.

## Rules
- Keep the author's meaning and facts. Change wording, not claims.
- A flag inside a quote, a code block or a proper name stays. Say so in one line.
- Do not add new phrasing from the list while fixing another flag.
- For a document that will be graded, submitted or read by others, use the `deliverable` skill
  too. This check is one of its steps.

## Done when
The checker prints `clean`, or every remaining flag is explained in one line, and the manual
read in step 3 is done.
