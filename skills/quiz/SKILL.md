---
name: quiz
description: Get decisions from the user as quick multiple-choice questions instead of a long written message. Use when they say "quiz me", "just ask me", "don't write me an essay", or when a task is blocked on several decisions at once.
---

# Quiz

For when a long message is the wrong way to get a decision out of someone.

## Rules

1. **No preamble.** Do not explain the situation first. Go straight to the questions.
2. **Use the agent's multiple-choice question tool** (`AskUserQuestion` in some tools), up to 4
   questions per round. Chain a second round if needed. Without such a tool, write numbered
   questions with lettered options in the reply, under the same limits.
3. **Every option is a real choice.** Put the recommended one first and mark it "(Recommended)".
4. **Option descriptions stay under about 15 words** and say what happens if it is picked,
   not what it means.

5. **Only ask what changes what you do next.** If a sensible default exists, take it and
   mention it in the summary instead of asking.
6. **Never ask what you can check.** Look in the repo, the files or the web first.
7. **Do reversible steps, don't ask about them.** A local trial, a draft or a retry just
   happens. Ask only before a step that is outward-facing, costly or destructive. Never end on
   "say go".

## Approving a draft

Anything the person must approve (a post, an email, a message) goes in full in the reply
text: one draft per recipient, no `{placeholders}` left. End with a plain-text "yes?" and stop.
Never put a draft inside a multiple-choice question or its option previews; some apps do not
display them, so the person would approve text they never saw.

## After the answers

Reply in five lines or fewer:

- what was decided, one line each
- what you are doing next
- what the user owes you, if anything, with a deadline if one exists

No recap of the reasoning. If they want the reasoning they will ask.

## When not to use it

If the decision needs the user to see a draft or a number first, show that one thing, then
quiz. Do not ask someone to choose between options they cannot evaluate.

## Done when
Every question that changes the next step is answered, and the five-line summary is sent.
