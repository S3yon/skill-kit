#!/usr/bin/env python3
"""Flag AI writing tells in a draft. No dependencies, runs offline.

Usage: python3 slop_check.py <file> [...]
       cat draft.md | python3 slop_check.py -

Exit 0 when every file is clean, 1 when anything is flagged.
Patterns and the reasons for them: ../tells.md.
"""
import re
import sys

TIER1 = r"""leverage|leveraging|robust|seamless|seamlessly|pivotal|crucial|vital|delve|delving|
tapestry|landscape|realm|harness|harnessing|unlock|unlocking|elevate|elevating|navigate|
navigating|foster|fostering|underscore|underscores|myriad|plethora|holistic|comprehensive|
transformative|game-changing|cutting-edge|ever-evolving|multifaceted"""
TIER1 = TIER1.replace("\n", "")

CHECKS = [
    ("dash inside a sentence", r"\w[ \t]*[—–][ \t]*\w|\w[ \t]+-[ \t]+\w", "period, comma or new line"),
    ("it's not X, it's Y", r"\b(?:it(?:'s| is)|that(?:'s| is))\s+not\s+(?:just\s+)?[^.,;]{2,40},\s*it(?:'s| is)\b", "state the point directly"),
    ("not only ... but also", r"\bnot only\b[^.]{0,60}\bbut also\b", "state the point directly"),
    ("isn't just ... it's", r"\bis(?:n't| not)\s+just\b[^.]{0,60}\bit(?:'s| is)\b", "state the point directly"),
    ("significance inflation", r"\b(?:marks? a pivotal|a testament to|underscore[sd]? the importance|in today'?s (?:landscape|world)|plays? a (?:key|vital|crucial) role)\b", "say what happened"),
    ("copula avoidance", r"\b(?:serves as|functions as|acts as|stands as)\b", "use 'is'"),
    ("tier-one vocabulary", rf"\b(?:{TIER1})\b", "plain word"),
    ("filler construction", r"\b(?:in order to|it is important to note that|it'?s worth noting that|when it comes to|the fact that|a wide range of|a variety of)\b", "cut it"),
    ("hedge stacking", r"\b(?:may potentially|could possibly|might perhaps|arguably one of the most|can help to)\b", "commit or cut"),
    ("stock opener or closer", r"\b(?:let'?s dive in|here'?s the kicker|the truth is|let that sink in|i hope this helps|at the end of the day|continues to evolve)\b", "delete"),
    ("rhetorical transition", r"(?:^|\. )(?:so )?(?:what does this mean|why does this matter|the result\?|so what\?)", "answer it instead"),
]

def paragraphs(text):
    return [p for p in re.split(r"\n\s*\n", text) if p.strip()]

def check(name, text):
    hits = []
    for label, pattern, fix in CHECKS:
        for m in re.finditer(pattern, text, re.I | re.M):
            line = text[:m.start()].count("\n") + 1
            hits.append((line, label, m.group(0).strip()[:60], fix))

    words = len(re.findall(r"\b\w+\b", text))
    dashes = len(re.findall(r"[—–]", text))
    if words and dashes / words * 500 > 1:
        hits.append((0, "dash density", f"{dashes} dashes in {words} words", "at most 1 per 500 words"))

    # forced rule of three: three comma-separated items before "and"
    threes = len(re.findall(r"\b\w+,\s+\w+,?\s+and\s+\w+\b", text))
    if threes >= 4:
        hits.append((0, "rule of three", f"{threes} three-item lists", "vary to one, two or four"))

    # symmetry: paragraphs all within a narrow length band
    ps = [len(p.split()) for p in paragraphs(text) if len(p.split()) > 15]
    if len(ps) >= 4:
        spread = (max(ps) - min(ps)) / max(ps)
        if spread < 0.35:
            hits.append((0, "uniform paragraphs", f"{len(ps)} paragraphs, {min(ps)}-{max(ps)} words", "make it lumpy"))

    # wall of text
    for i, p in enumerate(paragraphs(text)):
        if len(p.split()) > 120:
            hits.append((text[:text.find(p)].count("\n") + 1, "wall of text", f"{len(p.split())} words", "break or cut"))

    hits.sort(key=lambda h: h[0])
    print(f"\n=== {name} ===")
    if not hits:
        print("clean")
        return 0
    for line, label, snippet, fix in hits:
        loc = f"L{line}" if line else "  —"
        print(f"{loc:>6}  {label:<26} {snippet!r}  -> {fix}")
    print(f"\n{len(hits)} flags")
    return len(hits)

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    total = 0
    for a in args:
        if a == "-":
            total += check("stdin", sys.stdin.read())
        else:
            total += check(a, open(a).read())
    return 0 if total == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
