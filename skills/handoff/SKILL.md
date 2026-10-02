---
name: handoff
description: Write a handoff note when a session or tool ends, and pick one up in the next session, so work moves between chats and tools without losing state. Use when the user says "handoff", "switching tools", "out of credits", "wrap up", or "pick up where we left off".
---

# Handoff

The repo is the only memory that survives a new chat or a different tool. A handoff note
says what changed, what is unfinished and why, and the next step.

## Write
1. **Save durable facts first.** Anything worth keeping beyond this session (a decision, a
   setting, a finding) goes into the project's own docs: the README, a decision log, notes.
   Not into the handoff.
2. **Commit finished work.** Unfinished work stays uncommitted; list it instead of committing
   it half done.

3. **Append a section** to `HANDOFF.md` at the repo root, or to the project's existing handoff
   file. Head it `## YYYY-MM-DD: <topic> (open)` and include:
   - the tool used
   - what changed, with commit hashes as printed
   - what is uncommitted, file by file, and why
   - the next concrete step
   - gotchas the next session would hit

   If the project has a task list, link to it instead of copying it.

4. **Commit only that file:** `git add HANDOFF.md`, then
   `git commit -m "<message>" -- HANDOFF.md`. The path after `--` keeps anything else staged
   out of the commit.
5. **End the reply with a one-line paste prompt:** read the `<topic>` section of HANDOFF.md and
   pick it up.

## Pick up
- Read the section the person named, matched by topic, not just the newest one.
- With no topic named, list the sections marked `(open)` and ask which one. Start nothing
  before the answer.
- Change its mark to `(picked up)`.
- Run `git log --oneline --since=<the section's date>` and `git status` to see what changed
  since, then continue from its next step.

## Several chats
One topic and one section per chat. Switch them one at a time, so two sessions never write
the file at once.

## Done when
Writing: the section is committed on its own, lists every uncommitted file with its reason,
and the reply ends with the paste prompt. Picking up: the named section is marked picked up
and work continues from its next step.
