---
name: proof-before-done
description: Report finished work and outside facts only with proof. An action counts as done when a tool result shows it, and a price, limit, spec, version, date or count is sourced now or marked unverified. Use before saying anything is done, written, committed, pushed, sent or deployed, and before stating a price, limit, version, date or count.
---

# Proof before done

A report is only as good as the evidence behind it. This skill covers any claim, not only code.
It complements test-based verification skills (superpowers' `verification-before-completion`
covers code and tests).

## Actions
- Say a file was written, saved, committed, pushed, sent, posted or deployed only after the
  tool result shows it happened.
- Quote hashes, URLs and IDs exactly as a tool printed them. If the output was cut off or never
  appeared, read it again (for a commit, `git log -1 --format=%H`) instead of filling it in.

## Outside facts
- A price, limit, spec, version, date or count gets a source now: a link to the page you just
  read with the agent's web search or fetch tool.
- If there is no such tool or you cannot check it, mark it "unverified" and say where you
  looked or where to look.
- An earlier statement in the same session, yours or a file's, is not a source. Repeating it
  does not make it checked.

## Partial results
- Report partial work as partial. "41 of 43 tests pass" is not "done".
- A failing test is reported with its name, its file and its output, or an offer to show it.

## Report shape
End with up to three short lists:
- **Done:** each item and how it was checked.
- **Not verified:** each claim and where you looked.
- **Not done:** what is left.

## Done when
Every action in the report has a tool result behind it, every outside fact has a link or an
"unverified" mark, and anything partial or failing is reported as such.
