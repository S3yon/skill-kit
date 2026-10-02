# skill-kit

Agent skills for the points where an agent's work reaches a person.

| When | Skill | What it does |
|---|---|---|
| A decision is needed | `quiz` | Asks it as multiple choice |
| Options to pick from | `variant-lab` | Builds and tests 4 to 6 working versions |
| Writing is handed over | `writing-check` | Flags AI writing patterns |
| A graded or shared document | `deliverable` | Drafts it from the rubric |
| The agent says done | `proof-before-done` | Shows the tool result as proof |
| A push to a public repo | `push-check` | Blocks secrets, malicious code and personal information |
| A session or tool ends | `handoff` | Writes and picks up handoff notes |

These are the points where agent work costs a person time or embarrassment: a question buried
in a long reply, a claim with no source, a key in a public commit. Process kits such as
[superpowers](https://github.com/obra/superpowers) cover how an agent builds. This kit covers
what happens when that work meets a person, and works alongside them.

Each skill is a plain `SKILL.md` folder, so any agent tool that reads that format can use it.

## Install

### Claude Code

```
/plugin marketplace add S3yon/skill-kit
/plugin install skill-kit@skill-kit
```

The skills then show as `skill-kit:<name>`, for example `skill-kit:quiz`.

Checked against https://code.claude.com/docs/en/plugin-marketplaces, 2026-10-02.

### GitHub Copilot CLI

Reads the same plugin manifests as Claude Code.

```
copilot plugin marketplace add S3yon/skill-kit
copilot plugin install skill-kit@skill-kit
```

Or in one step: `copilot plugin install S3yon/skill-kit`.

Checked against https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-plugin-reference, 2026-10-02.

### Qwen Code

Reads the same marketplace file as Claude Code.

```
qwen extensions install S3yon/skill-kit:skill-kit
```

Checked against https://github.com/QwenLM/qwen-code/blob/main/docs/users/extension/introduction.md, 2026-10-02.

### Gemini CLI

Reads `gemini-extension.json` and loads `skills/`.

```
gemini extensions install https://github.com/S3yon/skill-kit
```

Checked against https://github.com/google-gemini/gemini-cli/blob/main/docs/extensions/reference.md, 2026-10-02.

### Codex

Reads the root `plugin.json` and finds `skills/` on its own.

```
codex plugin marketplace add S3yon/skill-kit
codex plugin add skill-kit@skill-kit
```

Checked against https://developers.openai.com/plugins/build/plugins, 2026-10-02.

### Cursor

Reads the root `plugin.json` and `.cursor-plugin/marketplace.json`. Open Customize, then
From GitHub Repository, and enter `S3yon/skill-kit`.

Checked against https://cursor.com/docs/plugins, 2026-10-02.

### Copy a folder

Copy one folder from `skills/` into the tool's skills folder:

| Tool | For your user | For one project |
|---|---|---|
| Claude Code | `~/.claude/skills/` | `.claude/skills/` |
| Codex, Cursor, Gemini CLI, Copilot CLI | `~/.agents/skills/` | `.agents/skills/` |
| Qwen Code | `~/.qwen/skills/` | `.qwen/skills/` |

No manual install test was run. Of these tools, only the Cursor CLI was installed on the
machine where the steps were checked, and it was not signed in, so it could not load a plugin.

## Always-on snippet

Skills load when their description matches the task. To have three of the rules apply on every
task, paste these lines into a project's agent instructions file:

```
- Report an action as done only with the tool result that shows it, and an outside fact only with its source.
- Put any draft that needs approval in full in the reply text.
- Run push-check before any push to a public remote.
```

## The scripts on their own

Both need only Python 3.10 or later. `push_check.py` also needs git.

`skills/writing-check/scripts/slop_check.py` checks a draft:

```
python3 skills/writing-check/scripts/slop_check.py draft.md
```

It prints one line per flag with the line number and a replacement. Exit 0 means clean, 1 means
something was flagged. The patterns and why they are on the list:
[tells.md](skills/writing-check/tells.md).

`skills/push-check/scripts/push_check.py` checks commits before a push:

```
python3 skills/push-check/scripts/push_check.py --remote origin
python3 skills/push-check/scripts/push_check.py --install-hook
```

With no range it scans the unpushed commits. `--install-hook` installs it as the repo's
pre-push hook. Exit 0 means nothing blocks, 1 means something does, 2 means a usage error.

## Tests, CI and evals

- `python3 -m unittest discover tests` runs the script tests.
- `python3 scripts/validate.py` checks every skill folder, eval file and plugin manifest.
- CI runs both on every push and pull request, on Python 3.10 and the latest 3.x.
- Each skill's `evals/evals.json` holds prompts with checkable assertions. How to run and grade
  them: [docs/evals.md](docs/evals.md).

## License

MIT
