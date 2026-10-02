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
PATHSPEC = ["--", ".", ":(exclude)*lock.json", ":(exclude)*.lock", ":(exclude)*lock.yaml"]
MAGIC = ("7f454c46", "feedface", "feedfacf", "cefaedfe", "cffaedfe", "4d5a")
INSTALLER_EXT = (".exe", ".dll", ".scr", ".com", ".msi", ".vbs", ".jar", ".apk", ".dmg", ".pkg")
C_ESCAPES = {"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13, '"': 34, "\\": 92}


class Finding(NamedTuple):
    level: str
    what: str
    file: str | None


class UsageError(Exception):
    pass


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
    ("BLOCK", "destructive delete", re.compile(r"\brm\s+-rf\s+(/|~|\$HOME)(\s|$|[\"'])")),
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


def scan_commit(sha: str) -> list[Finding]:
    findings = [
        Finding(level, label, path)
        for path, line in added_lines(sha)
        for level, label, pattern in LINE_RULES
        if pattern.search(line)
    ]
    findings += file_findings(sha)
    return list(dict.fromkeys(findings))


def parse_args(argv: list[str]) -> tuple[str | None, str | None, list[str]]:
    remote: str | None = None
    visibility: str | None = None
    revs: list[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--":
            revs.extend(argv[i + 1:])
            break
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
    return remote, visibility, revs


def main(argv: list[str]) -> int:
    try:
        remote, visibility, revs = parse_args(argv)
        git("rev-parse", "--git-dir")
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

    blocks = warns = 0
    for sha in commits:
        meta = git("log", "-1", "--format=%h%x00%s", sha).decode("utf-8", "replace")
        short, subject = meta.rstrip("\n").split("\0", 1)
        for f in scan_commit(sha):
            what = f"{f.what} in {f.file}" if f.file else f.what
            print(f'{f.level:<6} {short} "{subject}": {what}')
            if f.level == "BLOCK":
                blocks += 1
            else:
                warns += 1

    checks = "built-in checks + ClamAV" if shutil.which("clamscan") else "built-in checks"
    print(
        f"push-check: {len(commits)} commits, {blocks} blocking, {warns} warnings "
        f"({checks}; personal info off)"
    )
    return 1 if blocks else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
