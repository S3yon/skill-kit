"""Run: python3 -m unittest discover tests"""
import json, pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts/validate.py"
sys.path.insert(0, str(ROOT / "scripts"))

SKILL = """---
name: {name}
description: {description}
---

# Demo

Steps.

## Done when
The demo ran.
"""

def skill_md(name="demo", description="Run a demo. Use when testing."):
    return SKILL.format(name=name, description=description)

def eval_case(i, **over):
    case = {"id": i, "name": f"case-{i}", "prompt": "Do it.", "expected_output": "It is done.",
            "files": [], "assertions": ["The reply does it"]}
    case.update(over)
    return case

def evals_doc(name="demo", n=3):
    return {"skill_name": name, "evals": [eval_case(i) for i in range(1, n + 1)]}

README = "# kit\n\n| Skill | What it does |\n|---|---|\n| `demo` | Runs a demo. |\n"

def make_kit(tmp, skills=None, readme=None, manifests=None):
    """Write a kit. skills maps folder -> (SKILL.md text or None, evals object, raw string or None).
    manifests maps relative path -> object or raw string."""
    root = pathlib.Path(tmp)
    if skills is None:
        skills = {"demo": (skill_md(), evals_doc())}
    if manifests is None:
        manifests = {".claude-plugin/plugin.json": {"name": "kit", "version": "0.2.0"}}
    for folder, (md, ev) in skills.items():
        d = root / "skills" / folder
        d.mkdir(parents=True)
        if md is not None:
            (d / "SKILL.md").write_text(md)
        if ev is not None:
            (d / "evals").mkdir()
            (d / "evals/evals.json").write_text(ev if isinstance(ev, str) else json.dumps(ev))
    (root / "README.md").write_text(README if readme is None else readme)
    for rel, obj in manifests.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(obj if isinstance(obj, str) else json.dumps(obj))
    return root

def problems(root):
    import validate
    return validate.validate(root)

def cli(root):
    r = subprocess.run([sys.executable, str(SCRIPT), str(root)], capture_output=True, text=True)
    return r.returncode, r.stdout

class Validate(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def assertProblem(self, root, text):
        found = problems(root)
        self.assertTrue(any(text in p for p in found), f"{text!r} not in {found}")

    def test_clean_kit_passes(self):
        root = make_kit(self.tmp)
        self.assertEqual(problems(root), [])
        code, out = cli(root)
        self.assertEqual(code, 0, out)
        self.assertEqual(out.strip(), "validate: ok (skills 1, manifests 1, version 0.2.0)")

    def test_name_must_match_folder(self):
        root = make_kit(self.tmp, skills={"demo": (skill_md(name="other"), evals_doc())})
        self.assertProblem(root, "skills/demo/SKILL.md: name 'other' does not match folder 'demo'")

    def test_missing_done_when(self):
        md = skill_md().replace("## Done when", "## Finish")
        root = make_kit(self.tmp, skills={"demo": (md, evals_doc())})
        self.assertProblem(root, "skills/demo/SKILL.md: no '## Done when'")

    def test_frontmatter_problems(self):
        cases = {
            "no frontmatter": ("# Demo\n\n## Done when\nDone.\n", "skills/demo/SKILL.md: no frontmatter"),
            "empty description": (skill_md(description=""), "skills/demo/SKILL.md: empty description"),
            "no SKILL.md": (None, "skills/demo: no SKILL.md"),
        }
        for label, (md, text) in cases.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as tmp:
                self.assertProblem(make_kit(tmp, skills={"demo": (md, evals_doc())}), text)

    def test_description_with_colon_and_quotes_parses(self):
        md = skill_md(description='Check a draft: "quotes" (parens). Use when ...')
        md = md.replace("name: demo", 'name: "demo"')
        root = make_kit(self.tmp, skills={"demo": (md, evals_doc())})
        self.assertEqual(problems(root), [])

    def test_eval_rules(self):
        rel = "skills/demo/evals/evals.json"
        two = evals_doc(n=2)
        dup = evals_doc(); dup["evals"][1]["id"] = 1
        blank = evals_doc(); blank["evals"][0]["assertions"] = ["ok", "  "]
        cases = {
            "missing": (None, f"{rel}: missing"),
            "invalid JSON": ("{not json", f"{rel}: invalid JSON"),
            "skill_name": (evals_doc(name="x"), f"{rel}: skill_name 'x' does not match folder 'demo'"),
            "empty list": ({"skill_name": "demo", "evals": []}, f"{rel}: 'evals' must be a non-empty list"),
            "duplicate id": (dup, "duplicate id 1"),
            "blank assertion": (blank, "every assertion must be a non-empty string"),
            "two cases": (two, f"{rel}: 2 eval cases, need at least 3"),
        }
        for field, value in (("id", "1"), ("name", ""), ("prompt", ""), ("expected_output", ""), ("assertions", [])):
            doc = evals_doc(); doc["evals"][0][field] = value
            cases[f"field {field}"] = (doc, f"eval #1: missing or empty '{field}'")
        for label, (ev, text) in cases.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as tmp:
                self.assertProblem(make_kit(tmp, skills={"demo": (skill_md(), ev)}), text)

    def test_source_is_optional(self):
        doc = evals_doc(); doc["evals"][0]["source"] = "a real failure"
        root = make_kit(self.tmp, skills={"demo": (skill_md(), doc)})
        self.assertEqual(problems(root), [])

    def test_skill_missing_from_readme(self):
        readme = "# kit\n\nThe `demo` skill runs a demo.\n\n| Skill | What |\n|---|---|\n| `other` | x |\n"
        root = make_kit(self.tmp, readme=readme)
        self.assertProblem(root, "skill 'demo' is not in the README table")

    def test_manifest_versions_must_agree(self):
        manifests = {
            ".claude-plugin/plugin.json": {"name": "kit", "version": "0.2.0"},
            ".claude-plugin/marketplace.json": {"name": "kit", "plugins": [{"name": "kit", "version": "0.1.0"}]},
        }
        root = make_kit(self.tmp, manifests=manifests)
        self.assertProblem(root, "manifest versions differ: .claude-plugin/plugin.json=0.2.0, "
                                 ".claude-plugin/marketplace.json=0.1.0")

    def test_no_manifest_version(self):
        root = make_kit(self.tmp, manifests={".claude-plugin/plugin.json": {"name": "kit"}})
        self.assertProblem(root, "no manifest version found")

    def test_bad_manifest_json(self):
        root = make_kit(self.tmp, manifests={".claude-plugin/plugin.json": "{"})
        self.assertProblem(root, ".claude-plugin/plugin.json: does not parse")

    def test_cli_exit_codes(self):
        root = make_kit(self.tmp, skills={"demo": (skill_md(name="other"), evals_doc(n=2))})
        code, out = cli(root)
        self.assertEqual(code, 1)
        lines = out.strip().splitlines()
        self.assertEqual(len(lines), 2, out)
        for line in lines:
            self.assertTrue(line.startswith("validate: "), line)

if __name__ == "__main__":
    unittest.main()
