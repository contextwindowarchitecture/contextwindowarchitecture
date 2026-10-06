"""Every generated case, rejection and registry file is what conformance/generators/all.py writes from the generators.

    python3 -m unittest discover -s conformance/tests
"""
import filecmp, os, shutil, subprocess, sys, tempfile, unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
GENERATED = ["conformance/cases", "conformance/rejections", "conformance/registry"]


def listing(base):
    return sorted(os.path.relpath(os.path.join(d, f), base) for d, _, files in os.walk(base) for f in files if "__pycache__" not in d)


class Regenerate(unittest.TestCase):
    def test_regenerating_every_case_changes_nothing(self):
        with tempfile.TemporaryDirectory(prefix="cwa-regenerate-") as copy:
            for path in ["schema", "contract", "examples", "conformance"]:
                shutil.copytree(os.path.join(ROOT, path), os.path.join(copy, path), ignore=shutil.ignore_patterns("__pycache__"))
            subprocess.run([sys.executable, "-B", os.path.join(copy, "conformance/generators/all.py")], check=True, capture_output=True)
            for path in GENERATED:
                before, after = os.path.join(ROOT, path), os.path.join(copy, path)
                self.assertEqual(listing(after), listing(before), f"{path}: files added or removed")
                changed = [f for f in listing(before) if not filecmp.cmp(os.path.join(before, f), os.path.join(after, f), shallow=False)]
                self.assertEqual(changed, [], f"{path}: regenerated differently")


if __name__ == "__main__":
    unittest.main()
