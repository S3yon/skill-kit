# Changelog

## 0.2.0 (2026-10-02)

The kit now covers the points where an agent's work reaches a person.

New skills:
- `push-check`: scans unpushed commits for secrets, malicious code, personal information and
  AI credit lines, blocks the push on a serious finding, and installs as a pre-push hook.
- `proof-before-done`: reports work as done only with a tool result, and outside facts only
  with a source.
- `deliverable`: drafts a graded or shared document from its rubric, at an agreed length.
- `handoff`: writes a handoff note when a session or tool ends, and picks it up in the next one.

Changed skills:
- `quiz`: drafts for approval go in full in the reply text, and reversible steps go ahead
  without a question.
- `variant-lab`: judges motion in a headless or foreground browser, and lays out media
  variants on one comparison sheet.
- `writing-check`: points graded documents to `deliverable`, and has a third eval case.

Scripts, CI and install:
- `scripts/validate.py` checks every skill folder, eval file, README row and plugin manifest.
- `docs/evals.md` explains how to run old-vs-new eval runs with any agent.
- CI runs the tests and `validate.py` on Python 3.10 and the latest 3.x.
- Manifests for GitHub Copilot CLI, Qwen Code, Gemini CLI, Codex and Cursor, with install
  steps and check dates in the README.

## 0.1.0 (2026-09-27)

First release: `quiz`, `variant-lab` and `writing-check`.
