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
