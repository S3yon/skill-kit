"""Run: python3 -m unittest discover tests"""
import pathlib, subprocess, sys, unittest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "skills/writing-check/scripts/slop_check.py"

def run(text):
    r = subprocess.run([sys.executable, str(SCRIPT), "-"], input=text, capture_output=True, text=True)
    return r.returncode, r.stdout

class SlopCheck(unittest.TestCase):
    def test_clean_text_passes(self):
        code, out = run("We moved the build to a faster runner. It now takes four minutes.\n")
        self.assertEqual(code, 0)
        self.assertIn("clean", out)

    def test_each_pattern_is_caught(self):
        cases = {
            "dash inside a sentence": "The fix was simple — we cached it.",
            "it's not X, it's Y": "It's not a bug, it's a feature.",
            "not only ... but also": "It is not only fast but also cheap.",
            "significance inflation": "This release is a testament to the team.",
            "copula avoidance": "The file serves as the index.",
            "tier-one vocabulary": "We leverage the cache.",
            "filler construction": "We did it in order to save time.",
            "hedge stacking": "This may potentially help.",
            "stock opener or closer": "Let's dive in.",
        }
        for label, text in cases.items():
            with self.subTest(label=label):
                code, out = run(text + "\n")
                self.assertEqual(code, 1)
                self.assertIn(label, out)

    def test_hyphen_bullets_are_not_dashes(self):
        code, out = run("Two things changed\n- the cache\n- the runner\n")
        self.assertEqual(code, 0, out)

    def test_no_arguments_prints_usage(self):
        r = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("Usage", r.stdout)

if __name__ == "__main__":
    unittest.main()
