"""Every whitespace class in check.py and the generators is ECMAScript's \\s (conformance/README.md, Blank strings).

    python3 -m unittest discover -s conformance/tests

The fixture-whitespace/v1 count, blank ids and deduplication keys all rest on that set, and a class that drops a member
changes no case until one holds that character. Three generators once held the class as literal characters, and all but
U+3000 and U+FEFF had become ASCII spaces.
"""
import ast, glob, os, re, unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
# What /\s/ matches in JavaScript: every code point is in the Basic Multilingual Plane.
ES_SPACE = {0x9, 0xA, 0xB, 0xC, 0xD, 0x20, 0xA0, 0x1680, *range(0x2000, 0x200B), 0x2028, 0x2029, 0x202F, 0x205F, 0x3000, 0xFEFF}
MARK = (r"\t\n\v\f\r", "\t\n\v\f\r")  # how a class opens, written in a raw string or a plain one


def classes():
    """(file:line, class) for every string literal in conformance/ that holds a whitespace class."""
    for path in sorted(glob.glob(os.path.join(ROOT, "conformance", "**", "*.py"), recursive=True)):
        if os.path.samefile(path, __file__): continue  # MARK itself
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and any(m in node.value for m in MARK):
                text = node.value
                if text.startswith("[^"): body = text[2:text.index("]")]
                elif text.startswith("["): body = text[1:text.index("]")]
                else: body = text  # a bare list of the characters, put into a class where it is used
                yield f"{os.path.relpath(path, ROOT)}:{node.lineno}", re.compile(f"[{body}]")


class Whitespace(unittest.TestCase):
    def test_every_whitespace_class_is_ecmascripts(self):
        found = list(classes())
        self.assertGreaterEqual(len(found), 9, "the classes this test holds were not found")
        for where, cls in found:
            with self.subTest(where=where):
                got = {c for c in range(0x10000) if not 0xD800 <= c <= 0xDFFF and cls.fullmatch(chr(c))}
                self.assertEqual(sorted(map(hex, got ^ ES_SPACE)), [], "code points in one set and not the other")


if __name__ == "__main__":
    unittest.main()
