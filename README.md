# skill-kit

Three agent skills, packaged as a plugin.

| Skill | What it does |
|---|---|
| `variant-lab` | Builds 4 to 6 working versions of one element (a UI section, an animation, a video title card), tests each one, lets you pick, ships the winner and deletes the rest. |
| `writing-check` | Flags the patterns that make a draft read as machine-generated, then fixes them. Includes a dependency-free checker script. |
| `quiz` | Asks for decisions as up to 4 multiple-choice questions, then replies with a summary of five lines or fewer. |
| `push-check` | Scans unpushed commits for secrets, malicious code, personal information and AI credit lines, and blocks the push on a serious finding. Installs as a pre-push hook. |
| `proof-before-done` | Reports work as done only with a tool result, and outside facts only with a source. |
| `deliverable` | Drafts a graded or shared document from its rubric, at an agreed length, with sourced facts. |
| `handoff` | Writes a handoff note when a session or tool ends, and picks it up in the next one. |

Each skill is a plain `SKILL.md` folder, so any agent tool that reads that format can use it.

## Install

As a plugin:

```
/plugin marketplace add S3yon/skill-kit
/plugin install skill-kit@skill-kit
```

The skills then show as `skill-kit:variant-lab`, `skill-kit:writing-check` and `skill-kit:quiz`.

Or copy a single skill folder from `skills/` into `~/.claude/skills/` or a project's
`.claude/skills/`.

## The checker on its own

`skills/writing-check/scripts/slop_check.py` needs only Python 3.

```
python3 skills/writing-check/scripts/slop_check.py draft.md
```

It prints one line per flag with the line number and a replacement, and exits 1 if anything
was flagged. The patterns and why they are on the list: [tells.md](skills/writing-check/tells.md).

## Tests and evals

- `python3 -m unittest discover tests` runs the checker tests.
- `skills/<name>/evals/evals.json` holds prompts with checkable assertions for each skill.
  Run a prompt with and without the skill and grade the reply against the assertions.

## License

MIT
