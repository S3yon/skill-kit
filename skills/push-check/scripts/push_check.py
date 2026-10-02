#!/usr/bin/env python3
"""Scan the commits about to be pushed for secrets, hidden characters and malicious code.

Usage:
  push_check.py [--remote NAME] [--visibility public|private] [--install-hook] [<rev-list args>]

With no range it checks the commits no remote has yet (HEAD --not --remotes). Any argument it
does not know goes to git rev-list, and "--" passes everything after it through.

Exit codes: 0 when nothing blocks (warnings allowed), 1 when anything blocks, 2 on a usage
error. Standard library only, Python 3.10 or later.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterator, NamedTuple

USAGE = (
    "push-check: usage: push_check.py [--remote NAME] [--visibility public|private] "
    "[--install-hook] [<rev-list args>]"
)
DEFAULT_RANGE = ["HEAD", "--not", "--remotes"]
# ":(top)" keeps the scan on the whole tree when the script runs from a subdirectory.
PATHSPEC = [
    "--", ":(top)", ":(top,exclude)*lock.json", ":(top,exclude)*.lock", ":(top,exclude)*lock.yaml",
]
MAGIC = ("7f454c46", "feedface", "feedfacf", "cefaedfe", "cffaedfe", "4d5a")
INSTALLER_EXT = (".exe", ".dll", ".scr", ".com", ".msi", ".vbs", ".jar", ".apk", ".dmg", ".pkg")
C_ESCAPES = {"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13, '"': 34, "\\": 92}
AI_TOOLS = re.compile(
    r"\b(claude|anthropic|chatgpt|openai|copilot|gemini|codex|cursor|devin|aider|windsurf"
    r"|cody|qwen|grok|jules)\b",
    re.I,
)
GENERATED = re.compile(
    r"\bgenerated\s+(with|by)\b.*?(" + AI_TOOLS.pattern + r"|\b(ai|agent)\b)", re.I
)
CO_AUTHOR = re.compile(r"^\s*co-authored-by:", re.I)
PHONE = re.compile(
    r"(?<![\d-])(\+?1[\s.-])?(\(\d{3}\)\s?|\d{3}[\s.-])\d{3}[\s.-]\d{4}(?![\d-])"
)
DIGIT_PUNCT = re.compile(r"[\s().+\-]")
GITHUB_SLUG = re.compile(
    r"^(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)"
    r"([^/\s]+/[^/\s]+?)(?:\.git)?/?$"
)


class Finding(NamedTuple):
    level: str
    what: str
    file: str | None


class UsageError(Exception):
    pass


class Pattern(NamedTuple):
    kind: str
    value: str
    digits: bool


# Two of these patterns would match their own source text, so they are joined from pieces.
LINE_RULES: list[tuple[str, str, re.Pattern]] = [
    ("BLOCK", "private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("BLOCK", "AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("BLOCK", "GitHub token",
     re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,})")),
    ("BLOCK", "API secret key", re.compile(r"\b(sk-[A-Za-z0-9_-]{32,}|sk_live_[0-9A-Za-z]{20,})")),
    ("BLOCK", "Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}")),
    ("BLOCK", "Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("BLOCK", "hidden bidi or tag characters",
     re.compile(r"[\u202A-\u202E\u2066-\u2069\U000E0000-\U000E007F]")),
    ("WARN", "zero-width character", re.compile(r"[\u200B\u2060]")),
    ("BLOCK", "reverse shell",
     re.compile(re.escape("/dev/" + "tcp/") + r"|\bnc\s+(-\w+\s+)*-e\s|\bbash\s+-i\s+>&")),
    ("BLOCK", "decode-and-run", re.compile(
        r"base64\s+(-d|--decode|-D)\b.*\|\s*(sudo\s+)?(ba|z)?sh\b"
        r"|\b(eval|exec)\s*\(\s*(atob|Buffer\.from|base64_decode|base64\.b64decode|unescape)\s*\(")),
    ("BLOCK", "destructive delete", re.compile(r"\brm\s+-rf\s+\"?(/|~|\$HOME|\$\{HOME\})/?\*?\"?(\s|$|[\"'])")),
    ("BLOCK", "crypto miner", re.compile(r"stratum\+tcp://|\b" + "xm" + "rig" + r"\b", re.I)),
    ("WARN", "pipes a download into a shell",
     re.compile(r"\b(curl|wget)\b[^|]*\|\s*(sudo\s+)?(ba|z)?sh\b")),
    ("WARN", "npm install script", re.compile(r'"(pre|post)?install"\s*:')),
    ("BLOCK", "prompt injection", re.compile(
        r"\b(ignore|disregard|forget)\s+(all\s+|any\s+)?(the\s+|your\s+)?"
        r"(previous|prior|above|earlier)\s+(instructions|prompts|rules|messages)", re.I)),
    ("BLOCK", "prompt injection", re.compile(
        r"\byou\s+are\s+now\s+(in\s+)?(developer|dan|jailbreak|unrestricted)"
        r"|\bdo\s+not\s+(tell|inform)\s+the\s+user\b|<\|im_start\|>|\bnew\s+system\s+prompt\b",
        re.I)),
]


def git(*args: str, stdin: bytes | None = None) -> bytes:
    out = subprocess.run(["git", *args], input=stdin, capture_output=True)
    if out.returncode != 0:
        raise subprocess.CalledProcessError(out.returncode, args, out.stdout, out.stderr)
    return out.stdout


_empty_tree: str | None = None


def base_of(sha: str) -> str:
    """The commit's first parent, or the empty tree for a root commit."""
    global _empty_tree
    parents = git("rev-list", "--parents", "-n", "1", sha).decode().split()[1:]
    if parents:
        return parents[0]
    if _empty_tree is None:
        _empty_tree = git("hash-object", "-t", "tree", "--stdin", stdin=b"").decode().strip()
    return _empty_tree


def c_unquote(text: str) -> str:
    """Undo git's C-style quoting of a path (the part between the double quotes)."""
    out = bytearray()
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text):
            octal = text[i + 1:i + 4]
            if len(octal) == 3 and all(c in "01234567" for c in octal):
                out.append(int(octal, 8))
                i += 4
                continue
            nxt = text[i + 1]
            out.extend(bytes([C_ESCAPES[nxt]]) if nxt in C_ESCAPES else nxt.encode())
            i += 2
            continue
        out.extend(ch.encode("utf-8"))
        i += 1
    return out.decode("utf-8", "replace")


def header_path(text: str) -> str | None:
    # git ends the header with a tab when the name holds a space.
    text = text.rstrip("\t")
    if text == "/dev/null":
        return None
    if len(text) > 1 and text.startswith('"') and text.endswith('"'):
        text = c_unquote(text[1:-1])
    return text[2:] if text.startswith("b/") else text


def added_lines(sha: str) -> Iterator[tuple[str, str]]:
    """Yield (path, line) for every line the commit adds, lockfiles excluded."""
    out = git(
        "-c", "core.quotePath=false", "diff", "-U0", "--no-color", "--no-ext-diff",
        "--no-renames", "--src-prefix=a/", "--dst-prefix=b/", base_of(sha), sha, *PATHSPEC,
    )
    path: str | None = None
    in_hunk = False
    for raw in out.split(b"\n"):
        line = raw.decode("utf-8", "replace")
        if line.startswith("diff --git "):
            path, in_hunk = None, False
        elif not in_hunk:
            if line.startswith("+++ "):
                path = header_path(line[4:])
            elif line.startswith("@@"):
                in_hunk = True
        elif line.startswith("+") and path is not None:
            yield path, line[1:]


def file_findings(sha: str) -> list[Finding]:
    """Executable binaries and installers among the added or modified files, plus ClamAV."""
    names = git(
        "diff", "--name-only", "-z", "--no-renames", "--diff-filter=AM", base_of(sha), sha,
        *PATHSPEC,
    )
    clamscan = shutil.which("clamscan")
    findings: list[Finding] = []
    blobs: dict[str, bytes] = {}
    for name in names.split(b"\0"):
        if not name:
            continue
        path = name.decode("utf-8", "surrogateescape")
        blob = subprocess.run(["git", "cat-file", "blob", f"{sha}:{path}"], capture_output=True)
        if blob.returncode != 0:  # a submodule entry has no blob
            continue
        if blob.stdout[:4].hex().startswith(MAGIC):
            findings.append(Finding("BLOCK", f"executable binary added: {path}", None))
        if path.lower().endswith(INSTALLER_EXT):
            findings.append(Finding("WARN", f"installer or executable file: {path}", None))
        if clamscan:
            blobs[path] = blob.stdout
    if blobs:
        with tempfile.TemporaryDirectory() as tmp:
            for path, data in blobs.items():
                target = Path(tmp, path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            scan = subprocess.run(
                [clamscan, "-r", "--infected", "--no-summary", tmp], capture_output=True
            )
            if scan.returncode == 1:
                findings.append(Finding("BLOCK", "ClamAV found an infected file", None))
    return findings


def patterns_path() -> Path:
    env = os.environ.get("PUSH_CHECK_PERSONAL")
    return Path(env) if env else Path.home() / ".config" / "push-check" / "personal.txt"


def load_patterns() -> list[Pattern] | None:
    """The person's `kind|value` lines, or None when the file can't be read."""
    try:
        text = patterns_path().read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    patterns = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "|" not in line:
            continue
        kind, value = (part.strip() for part in line.split("|", 1))
        if value:
            digits = re.fullmatch(r"[0-9]+", value) is not None
            patterns.append(Pattern(kind, value.lower(), digits))
    return patterns


def github_visibility(slug: str) -> str:
    if not shutil.which("gh"):
        return ""
    out = subprocess.run(
        ["gh", "repo", "view", slug, "--json", "visibility", "-q", ".visibility"],
        capture_output=True,
    )
    return out.stdout.decode("utf-8", "replace").strip().upper() if out.returncode == 0 else ""


def personal_level(remote: str | None, visibility: str | None) -> tuple[str, str]:
    """How personal-info matches count ("", WARN or BLOCK) and the note for the summary."""
    if visibility == "private":
        return "", "personal info skipped (--visibility private)"
    if visibility == "public":
        level, note = "BLOCK", "personal info blocks (--visibility public)"
    elif remote is not None:
        try:
            url = git("remote", "get-url", remote).decode("utf-8", "replace").strip()
        except subprocess.CalledProcessError:
            url = remote
        match = GITHUB_SLUG.match(url)
        vis = github_visibility(match.group(1)) if match else ""
        if vis in ("PRIVATE", "INTERNAL"):
            return "", f"personal info skipped, {match.group(1)} is private"
        if vis == "PUBLIC":
            level, note = "BLOCK", f"personal info blocks, {match.group(1)} is public"
        else:
            level, note = "BLOCK", f"personal info blocks, visibility of {remote} unknown"
    else:
        level, note = "WARN", "no remote given, personal info warns only"
    if not patterns_path().is_file():
        note += "; no patterns file, generic checks only"
    return level, note


def personal_findings(path: str, line: str, level: str, patterns: list[Pattern]) -> list[Finding]:
    lower = line.lower()
    digits = DIGIT_PUNCT.sub("", line)
    findings = [
        Finding(level, f"personal info ({p.kind})", path)
        for p in patterns
        if p.value in (digits if p.digits else lower)
    ]
    if PHONE.search(line):
        findings.append(Finding("WARN", "looks like a phone number", path))
    return findings


def ai_credit(sha: str) -> list[Finding]:
    """AI tools named as author, committer, co-author or in a 'generated with' line."""
    meta = git("log", "-1", "--format=%an <%ae>%n%cn <%ce>%n%B", sha).decode("utf-8", "replace")
    lines = meta.split("\n")
    findings = []
    if any(AI_TOOLS.search(line) for line in lines[:2]):
        findings.append(Finding("BLOCK", "author or committer is an AI tool", None))
    body = lines[2:]
    if any(CO_AUTHOR.match(line) and AI_TOOLS.search(line) for line in body):
        findings.append(Finding("BLOCK", "co-author trailer credits an AI tool", None))
    if any(GENERATED.search(line) for line in body):
        findings.append(Finding("BLOCK", "has a 'generated with' line", None))
    return findings


def scan_commit(sha: str, level: str = "", patterns: list[Pattern] | None = None) -> list[Finding]:
    findings: list[Finding] = []
    for path, line in added_lines(sha):
        findings += [
            Finding(rule_level, label, path)
            for rule_level, label, pattern in LINE_RULES
            if pattern.search(line)
        ]
        if level:
            findings += personal_findings(path, line, level, patterns or [])
    findings += file_findings(sha)
    findings += ai_credit(sha)
    return list(dict.fromkeys(findings))


HOOK = """#!/bin/sh
# Installed by push-check --install-hook. Scans the commits each push would add.
while read -r lref lsha rref rsha; do
  case "$lsha" in *[!0]*) ;; *) continue ;; esac
  case "$rsha" in
    *[!0]*) {line} "$rsha..$lsha" ;;
    *) {line} "$lsha" --not --remotes="$1" ;;
  esac || {{ echo "pre-push: blocked by push-check" >&2; exit 1; }}
done
exit 0
"""


def install_hook() -> int:
    """Write a pre-push hook that runs this script, unless git would ignore it or one exists."""
    script = re.sub(r'([\\"$`])', r"\\\1", str(Path(__file__).resolve()))
    line = f'python3 "{script}" --remote "$1"'
    try:
        hooks_path = git("config", "core.hooksPath").decode("utf-8", "replace").strip()
    except subprocess.CalledProcessError:
        hooks_path = ""
    if hooks_path:
        print(
            f"push-check: core.hooksPath is {hooks_path}; git ignores .git/hooks. "
            f"Add this line to {hooks_path}/pre-push:\n{line}"
        )
        return 1
    hook = Path(git("rev-parse", "--git-path", "hooks").decode().strip(), "pre-push").resolve()
    if hook.exists():
        print(f"push-check: {hook} exists; not overwriting. Add this line to it:\n{line}")
        return 1
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text(HOOK.format(line=line), encoding="utf-8")
    hook.chmod(0o755)
    print(f"push-check: installed {hook}")
    return 0


def parse_args(argv: list[str]) -> tuple[str | None, str | None, bool, list[str]]:
    remote: str | None = None
    visibility: str | None = None
    install = False
    revs: list[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--":
            revs.extend(argv[i + 1:])
            break
        if arg == "--install-hook":
            install = True
            i += 1
            continue
        if arg in ("--remote", "--visibility"):
            if i + 1 >= len(argv) or argv[i + 1].startswith("-"):
                raise UsageError(f"{arg} needs a value")
            value = argv[i + 1]
            if arg == "--remote":
                remote = value
            elif value in ("public", "private"):
                visibility = value
            else:
                raise UsageError("--visibility is public or private")
            i += 2
            continue
        revs.append(arg)
        i += 1
    return remote, visibility, install, revs


def main(argv: list[str]) -> int:
    try:
        remote, visibility, install, revs = parse_args(argv)
        git("rev-parse", "--git-dir")
        if install:
            return install_hook()
        commits = git("rev-list", "--reverse", *(revs or DEFAULT_RANGE)).decode().split()
    except UsageError as err:
        print(f"push-check: {err}\n{USAGE}", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as err:
        reason = err.stderr.decode("utf-8", "replace").strip().splitlines()
        print(f"push-check: {reason[0] if reason else 'git failed'}\n{USAGE}", file=sys.stderr)
        return 2
    except FileNotFoundError:
        print(f"push-check: git not found\n{USAGE}", file=sys.stderr)
        return 2

    if not commits:
        print("push-check: no commits to check")
        return 0

    level, note = personal_level(remote, visibility)
    patterns = load_patterns() if level else None
    blocks = warns = 0
    for sha in commits:
        meta = git("log", "-1", "--format=%h%x00%s", sha).decode("utf-8", "replace")
        short, subject = meta.rstrip("\n").split("\0", 1)
        for f in scan_commit(sha, level, patterns):
            what = f"{f.what} in {f.file}" if f.file else f.what
            print(f'{f.level:<6} {short} "{subject}": {what}')
            if f.level == "BLOCK":
                blocks += 1
            else:
                warns += 1

    checks = "built-in checks + ClamAV" if shutil.which("clamscan") else "built-in checks"
    print(
        f"push-check: {len(commits)} commits, {blocks} blocking, {warns} warnings "
        f"({checks}; {note})"
    )
    return 1 if blocks else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
