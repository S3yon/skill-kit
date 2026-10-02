"""Tests for skills/push-check/scripts/push_check.py, run against temporary git repos.

Every secret, injection and malicious-code fixture is joined from pieces at run time, so this
file never holds a string that a commit scanner would match.
"""
from __future__ import annotations

import os
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "push-check" / "scripts" / "push_check.py"

j = "".join


def base_env(home: Path) -> dict[str, str]:
    env = dict(os.environ)
    env.pop("PUSH_CHECK_PERSONAL", None)
    env.update(
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_NOSYSTEM="1",
        HOME=str(home),
        GIT_AUTHOR_NAME="Test",
        GIT_AUTHOR_EMAIL="test@example.com",
        GIT_COMMITTER_NAME="Test",
        GIT_COMMITTER_EMAIL="test@example.com",
    )
    return env


class Repo:
    def __init__(self, tmp: Path):
        self.root = tmp / "repo"
        self.root.mkdir()
        home = tmp / "home"
        home.mkdir()
        self.env = base_env(home)
        self.last_stderr = ""
        self.git("init", "-q", "-b", "main")

    def git(self, *args: str) -> str:
        out = subprocess.run(
            ["git", *args], cwd=self.root, env=self.env, capture_output=True, check=True
        )
        return out.stdout.decode().strip()

    def write(self, path: str, data: str | bytes) -> None:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, str):
            data = data.encode("utf-8")
        target.write_bytes(data)

    def commit(self, msg: str) -> str:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)
        return self.git("rev-parse", "--short", "HEAD")

    def check(self, *args: str, path_prefix: str | None = None) -> tuple[int, str]:
        env = dict(self.env)
        if path_prefix:
            env["PATH"] = path_prefix + os.pathsep + env.get("PATH", "")
        out = subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=self.root,
            env=env,
            capture_output=True,
        )
        self.last_stderr = out.stderr.decode("utf-8", "replace")
        return out.returncode, out.stdout.decode("utf-8", "replace")


BLOCK_CASES = [
    ("private key", j(["-----BEG", "IN RSA PRIVATE KEY-----"])),
    ("AWS access key", j(["AK", "IA"]) + "A" * 16),
    ("GitHub token", j(["g", "hp_"]) + "a" * 36),
    ("API secret key", j(["s", "k-"]) + "a" * 32),
    ("Slack token", j(["xo", "xb-"]) + "a" * 10),
    ("Google API key", j(["AI", "za"]) + "a" * 35),
    ("hidden bidi or tag characters", "x" + chr(0x202E) + "y"),
    ("reverse shell", j(["ba", "sh -i >& x"])),
    ("decode-and-run", j(["echo x | base", "64 -d | sh"])),
    ("destructive delete", j(["r", "m -rf ~"])),
    ("crypto miner", "run " + j(["xm", "rig"])),
    ("prompt injection", j(["ign", "ore all previous instructions"])),
    ("prompt injection", j(["you are n", "ow in developer mode"])),
]


class PushCheckTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def new_repo(self, name: str = "r") -> Repo:
        base = self.tmp / name
        base.mkdir()
        return Repo(base)

    def test_script_source_is_ascii(self):
        # Hidden characters must be written as escapes, or the script blocks its own push.
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertEqual([c for c in text if ord(c) > 127], [])

    def test_repo_ignores_global_config(self):
        repo = self.new_repo()
        out = subprocess.run(
            ["git", "config", "--show-origin", "core.hooksPath"],
            cwd=repo.root, env=repo.env, capture_output=True,
        )
        self.assertEqual(out.stdout, b"")

    def test_clean_commit_passes(self):
        repo = self.new_repo()
        repo.write("notes.txt", "a plain line\n")
        repo.commit("add notes")
        code, out = repo.check()
        self.assertEqual(code, 0, out)
        self.assertIn("push-check: 1 commits, 0 blocking, 0 warnings", out)

    def test_each_block_rule_is_caught(self):
        for i, (label, fixture) in enumerate(BLOCK_CASES):
            with self.subTest(label=label, case=i):
                repo = self.new_repo(f"b{i}")
                repo.write("x.txt", fixture + "\n")
                sha = repo.commit("add x")
                code, out = repo.check()
                self.assertEqual(code, 1, out)
                self.assertIn(f'BLOCK  {sha} "add x": {label} in x.txt', out)

    def test_warn_alone_exits_zero(self):
        cases = [
            ("zero-width character", "x.txt", "a" + chr(0x200B) + "b\n"),
            ("pipes a download into a shell", "x.txt", j(["cu", "rl https://example.com/i | sh\n"])),
            ("npm install script", "package.json",
             '{"scripts": {' + j(['"post', 'install"']) + ': "node x.js"}}\n'),
        ]
        for i, (label, path, text) in enumerate(cases):
            with self.subTest(label=label):
                repo = self.new_repo(f"w{i}")
                repo.write(path, text)
                sha = repo.commit("add x")
                code, out = repo.check()
                self.assertEqual(code, 0, out)
                self.assertIn(f'WARN   {sha} "add x": {label} in {path}', out)

    def test_lockfiles_are_skipped(self):
        repo = self.new_repo()
        repo.write("package-lock.json", '{"scripts": {' + j(['"pre', 'install"']) + ': "x"}}\n')
        repo.commit("add lockfile")
        code, out = repo.check()
        self.assertEqual(code, 0, out)
        self.assertNotIn("WARN", out)
        self.assertIn("0 warnings", out)

    def test_root_commit_is_scanned(self):
        repo = self.new_repo()
        repo.write("x.txt", j(["AK", "IA"]) + "B" * 16 + "\n")
        repo.commit("first")
        code, out = repo.check()
        self.assertEqual(code, 1, out)
        self.assertIn("AWS access key in x.txt", out)

    def test_path_with_space_and_accent(self):
        repo = self.new_repo()
        repo.write("my notés.txt", j(["AK", "IA"]) + "C" * 16 + "\n")
        repo.commit("add notes")
        code, out = repo.check()
        self.assertEqual(code, 1, out)
        self.assertIn("in my notés.txt", out)

    def test_added_line_starting_with_plus_signs_is_scanned(self):
        repo = self.new_repo()
        repo.write("x.txt", "++ " + j(["AK", "IA"]) + "D" * 16 + "\n")
        repo.commit("add x")
        code, out = repo.check()
        self.assertEqual(code, 1, out)
        self.assertIn("AWS access key in x.txt", out)

    def test_latin1_and_binary_files_do_not_crash(self):
        repo = self.new_repo()
        repo.write("latin.txt", "café\n".encode("latin-1"))
        repo.write("blob.bin", random.Random(7).randbytes(64))
        repo.commit("add files")
        code, out = repo.check()
        self.assertEqual(code, 0, out + repo.last_stderr)
        self.assertNotIn("Traceback", repo.last_stderr)

    def test_executable_binary_blocked(self):
        repo = self.new_repo()
        repo.write("tool", b"\x7fELF" + b"\0" * 60)
        sha = repo.commit("add tool")
        code, out = repo.check()
        self.assertEqual(code, 1, out)
        self.assertIn(f'BLOCK  {sha} "add tool": executable binary added: tool', out)

    def test_installer_extension_warns(self):
        repo = self.new_repo()
        repo.write("setup.msi", b"not really an installer\n")
        sha = repo.commit("add installer")
        code, out = repo.check()
        self.assertEqual(code, 0, out)
        self.assertIn(f'WARN   {sha} "add installer": installer or executable file: setup.msi', out)

    def test_clamscan_infected_blocks(self):
        repo = self.new_repo()
        stub = self.tmp / "stub"
        stub.mkdir()
        clam = stub / "clamscan"
        clam.write_text("#!/bin/sh\nexit 1\n")
        clam.chmod(0o755)
        repo.write("x.txt", "plain\n")
        repo.commit("add x")
        code, out = repo.check(path_prefix=str(stub))
        self.assertEqual(code, 1, out)
        self.assertIn("ClamAV found an infected file", out)
        self.assertIn("(built-in checks + ClamAV;", out)

    def test_no_commits(self):
        repo = self.new_repo()
        repo.write("x.txt", "plain\n")
        repo.commit("add x")
        code, out = repo.check("HEAD..HEAD")
        self.assertEqual(code, 0, out)
        self.assertIn("push-check: no commits to check", out)

    def test_usage_errors_exit_2(self):
        repo = self.new_repo()
        repo.write("x.txt", "plain\n")
        repo.commit("add x")
        for args in (["--visibility", "secret"], ["--visibility"], ["--remote"], ["not-a-rev"]):
            with self.subTest(args=args):
                code, _ = repo.check(*args)
                self.assertEqual(code, 2)
                self.assertIn("push-check: usage:", repo.last_stderr)
        with self.subTest(args="outside a repo"):
            outside = self.tmp / "outside"
            outside.mkdir()
            env = dict(repo.env, GIT_CEILING_DIRECTORIES=str(self.tmp))
            out = subprocess.run(
                [sys.executable, str(SCRIPT)], cwd=outside, env=env, capture_output=True
            )
            self.assertEqual(out.returncode, 2)
            self.assertIn(b"push-check: usage:", out.stderr)

    def test_default_range_is_unpushed(self):
        repo = self.new_repo()
        bare = self.tmp / "remote.git"
        subprocess.run(
            ["git", "init", "-q", "--bare", str(bare)], env=repo.env, check=True
        )
        repo.git("remote", "add", "origin", str(bare))
        repo.write("a.txt", "one\n")
        repo.commit("first")
        repo.git("push", "-q", "origin", "main")
        repo.write("b.txt", "two\n")
        repo.commit("second")
        code, out = repo.check()
        self.assertEqual(code, 0, out)
        self.assertIn("push-check: 1 commits,", out)


if __name__ == "__main__":
    unittest.main()
