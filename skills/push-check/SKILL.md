---
name: push-check
description: Scan the commits about to be pushed for secrets, malicious code, hidden characters, personal information and AI credit lines, and block the push when anything serious turns up. Use before any push to a public remote, before asking the person whether to push, or when the user says "check before I push", "scan my commits" or "set up a pre-push check".
---

# Push check

A secret or a home address in a pushed commit stays in the history even after a later commit
deletes it. This skill scans the commits before they leave the machine. The scanner is
`scripts/push_check.py` in this skill's folder.

## When to run it
- Before any push to a public remote.
- Before asking the person whether to push, so the question comes with a clean result.
- After fixing a blocked commit, to confirm the fix.

## Run it
```
python3 <skill folder>/scripts/push_check.py --remote origin
```
- With no range it scans the unpushed commits (`HEAD --not --remotes`). Any other arguments
  go to `git rev-list`, for example `origin/main..HEAD`.
- `--remote NAME` sets how personal information counts (see below). `--visibility public` or
  `--visibility private` overrides the lookup.
- The last line is `push-check: N commits, B blocking, W warnings (...)`. Exit 0 means nothing
  blocks, 1 means something does, 2 means a usage error.

## Act on each level
**BLOCK:** do not push. Fix the commit itself: `git commit --amend` for the last commit, or a
rebase that edits an older one. A new commit that deletes the line leaves it in the old one.
Rescan, and ask to push only once it shows 0 blocking. A secret that already left the machine
must also be revoked and replaced.

**WARN:** read each one and decide. Say in one line each which ones stay and why.

Never push a blocked scan. Never use `--no-verify` unless the person asks for it in so many
words.

## AI credit lines
A co-author trailer naming an AI tool, an AI tool as author or committer, or a "generated
with" line in a commit message always blocks. There is no flag or setting to turn it down to
a warning, and the script should not be edited to add one. Offer to remove the line: amend the
last commit's message, or reword the older commit in a rebase. Then rescan.

## Personal information
The scanner reads a patterns file that never goes into git:
`~/.config/push-check/personal.txt`, or the path in `PUSH_CHECK_PERSONAL`. One `kind|value`
per line; lines starting with `#` are skipped. For example:
```
# email|you@example.com
# phone|2125550143
# address|12 Example Street
```
- Create the file with commented examples like these. The person fills in their own values in
  an editor. Never ask them to paste a phone number, address or other value into the chat.
- Phone numbers go in as digits only, so they match however the code spaces them.
- If `PUSH_CHECK_PERSONAL` points inside a repo, add the file to that repo's `.gitignore`.
- Only the kind is printed, never the value.

How a match counts depends on the remote:
- private: skipped
- public, or visibility unknown: BLOCK
- no `--remote` given: WARN

Visibility comes from the GitHub CLI when it is installed and the remote is on GitHub.
Otherwise it is unknown, unless `--visibility` sets it. With personal checks on, anything
shaped like a North American phone number warns too.

## Install as a hook
```
python3 <skill folder>/scripts/push_check.py --install-hook
```
- Run it inside the repo. It writes a pre-push hook that scans exactly the commits each push
  sends, with the remote's name.
- If a pre-push hook already exists, it does not overwrite it. It prints the line to add.
- If `core.hooksPath` is set, git ignores `.git/hooks`, so it prints the line to add to the
  pre-push file in that folder instead.

## Needs
Python 3 and git. ClamAV is used on added files when `clamscan` is installed. Without Python,
say the scan cannot run here and check by hand before pushing: read `git log -p` for the
unpushed commits and look for keys and tokens, personal details, encoded commands and AI
credit lines.

## Done when
The scan ran on the commits about to be pushed and shows 0 blocking, each warning was kept or
fixed with a one-line reason, and nothing was pushed without the person's yes.
