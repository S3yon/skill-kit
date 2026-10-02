#!/usr/bin/env python3
"""Check the kit's structure. Standard library only.

Usage: python3 scripts/validate.py [root]

Checks every skills/<name>/ folder (SKILL.md frontmatter, '## Done when', evals/evals.json),
that each skill has a row in the README table, and that the plugin manifests parse and agree
on one version. Prints one 'validate: <problem>' line per problem and exits 1, or prints
'validate: ok (...)' and exits 0.
"""
from __future__ import annotations

import json, pathlib, sys

MANIFESTS: tuple[str, ...] = (
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    "plugin.json",
    "gemini-extension.json",
    ".cursor-plugin/marketplace.json",
)
MIN_EVALS = 3

def frontmatter(text: str) -> dict[str, str] | None:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fields = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        key, sep, value = line.partition(": ")
        if not sep:
            key, value = line.rstrip(":"), ""
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        fields[key.strip()] = value
    return None

def check_skill(root: pathlib.Path, folder: pathlib.Path) -> list[str]:
    md = folder / "SKILL.md"
    rel = md.relative_to(root).as_posix()
    if not md.is_file():
        return [f"{folder.relative_to(root).as_posix()}: no SKILL.md"]
    text = md.read_text(encoding="utf-8")
    fm = frontmatter(text)
    if fm is None:
        return [f"{rel}: no frontmatter"]
    out = []
    if fm.get("name") != folder.name:
        out.append(f"{rel}: name '{fm.get('name', '')}' does not match folder '{folder.name}'")
    if not fm.get("description"):
        out.append(f"{rel}: empty description")
    if "## Done when" not in text:
        out.append(f"{rel}: no '## Done when'")
    return out

def check_evals(root: pathlib.Path, folder: pathlib.Path) -> list[str]:
    path = folder / "evals/evals.json"
    rel = path.relative_to(root).as_posix()
    if not path.is_file():
        return [f"{rel}: missing"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return [f"{rel}: invalid JSON"]
    if not isinstance(data, dict):
        return [f"{rel}: invalid JSON"]
    out = []
    if data.get("skill_name") != folder.name:
        out.append(f"{rel}: skill_name '{data.get('skill_name')}' does not match folder '{folder.name}'")
    evals = data.get("evals")
    if not isinstance(evals, list) or not evals:
        return out + [f"{rel}: 'evals' must be a non-empty list"]
    ids = set()
    for i, case in enumerate(evals, 1):
        where = f"{rel} eval #{i}"
        if not isinstance(case, dict):
            out.append(f"{where}: missing or empty 'id'")
            continue
        for field, kind in (("id", int), ("name", str), ("prompt", str), ("expected_output", str), ("assertions", list)):
            value = case.get(field)
            if not isinstance(value, kind) or isinstance(value, bool) or (kind is not int and not value):
                out.append(f"{where}: missing or empty '{field}'")
        if case.get("id") in ids:
            out.append(f"{where}: duplicate id {case.get('id')}")
        ids.add(case.get("id"))
        assertions = case.get("assertions")
        if isinstance(assertions, list) and any(not isinstance(a, str) or not a.strip() for a in assertions):
            out.append(f"{where}: every assertion must be a non-empty string")
    if len(evals) < MIN_EVALS:
        out.append(f"{rel}: {len(evals)} eval cases, need at least {MIN_EVALS}")
    return out

def readme_rows(root: pathlib.Path) -> str:
    readme = root / "README.md"
    if not readme.is_file():
        return ""
    lines = readme.read_text(encoding="utf-8").splitlines()
    return "\n".join(line for line in lines if line.startswith("|"))

def check_manifests(root: pathlib.Path) -> tuple[list[str], int, str | None]:
    out, versions, present = [], [], 0
    for rel in MANIFESTS:
        path = root / rel
        if not path.is_file():
            continue
        present += 1
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            out.append(f"{rel}: does not parse")
            continue
        if not isinstance(data, dict):
            out.append(f"{rel}: does not parse")
            continue
        if "version" in data:
            versions.append((rel, data["version"]))
        for plugin in data.get("plugins") or []:
            if isinstance(plugin, dict) and "version" in plugin:
                versions.append((rel, plugin["version"]))
    if out:
        return out, present, None
    if not versions:
        return ["no manifest version found"], present, None
    if len({v for _, v in versions}) > 1:
        listed = ", ".join(f"{rel}={v}" for rel, v in versions)
        return [f"manifest versions differ: {listed}"], present, None
    return [], present, versions[0][1]

def run(root: pathlib.Path) -> tuple[list[str], int, int, str | None]:
    found = []
    skills_dir = root / "skills"
    folders = sorted(p for p in skills_dir.iterdir() if p.is_dir()) if skills_dir.is_dir() else []
    rows = readme_rows(root)
    for folder in folders:
        found += check_skill(root, folder)
        found += check_evals(root, folder)
        if f"`{folder.name}`" not in rows:
            found.append(f"skill '{folder.name}' is not in the README table")
    manifest_problems, present, version = check_manifests(root)
    return found + manifest_problems, len(folders), present, version

def validate(root: pathlib.Path) -> list[str]:
    return run(pathlib.Path(root))[0]

def main(argv: list[str]) -> int:
    root = pathlib.Path(argv[0]) if argv else pathlib.Path(__file__).resolve().parent.parent
    found, skills, manifests, version = run(root)
    if found:
        for problem in found:
            print(f"validate: {problem}")
        return 1
    print(f"validate: ok (skills {skills}, manifests {manifests}, version {version})")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
