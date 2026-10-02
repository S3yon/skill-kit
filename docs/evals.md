# Running evals

Each skill has `evals/evals.json`: prompts, the expected behaviour, and assertions that can be
checked one at a time. An eval run shows whether a change to a skill helped, hurt, or did
nothing. Any agent that can start a fresh session can run them.

## Format

```json
{
  "skill_name": "quiz",
  "evals": [
    {
      "id": 1,
      "name": "short-kebab-name",
      "prompt": "What the person types.",
      "expected_output": "What a good reply does, in one or two sentences.",
      "files": [],
      "assertions": ["One checkable statement about the reply"]
    }
  ]
}
```

`source` is optional: where the case came from. `python3 scripts/validate.py` checks the
format and that each skill has at least 3 cases.

## Old vs new

1. Before editing a skill, copy its folder somewhere outside the repo. That copy is "old".
2. Make the edit. The repo version is "new".
3. Start one fresh session per version. Give it only the path to that version's `SKILL.md` and
   the prompts. Never give it the assertions or the expected output.

4. Tell it this is a dry run: it describes or drafts what it would do and writes nothing.
   Prompts that could touch the outside world (a push, a send, a post) start with "Dry run".

5. Grade each assertion on its own, pass or fail. Keep the grades outside the repo.
6. Put the result in the commit message of the skill change: `evals <skill>: old a/b, new c/d`.

For a new skill, run without the skill and with it, and record
`evals <skill>: without a/b, with c/d`.

## Regressions

If the new version fails an assertion the old version passed, that is a regression. Fix it
before committing.

## Corrections become cases

When a person corrects the agent on something a skill covers, add that situation as a case in
the same commit as the fix to the skill.
