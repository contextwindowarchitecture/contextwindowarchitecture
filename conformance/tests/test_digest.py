"""conformance/generators/digest.py: numbers serialize as RFC 8785 says, which is how JavaScript's JSON.stringify writes them.

    python3 -m unittest discover -s conformance/tests
"""
import copy, json, os, sys, unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(ROOT, "conformance/generators"))
import digest  # noqa: E402

# Each value beside what Node's JSON.stringify writes for it.
NUMBERS = [
    (12345678901234567890, "12345678901234567000"),
    (-12345678901234567890, "-12345678901234567000"),
    (12345678901234567890.0, "12345678901234567000"),
    (14904135880377241600.0, "14904135880377242000"),
    (999999999999999900000.0, "999999999999999900000"),
    (9007199254740993, "9007199254740992"),
    (2 ** 53, "9007199254740992"),
    (-2 ** 53, "-9007199254740992"),
    (2.0 ** 53 + 2, "9007199254740994"),
    (-0.0, "0"),
    (1e21, "1e+21"),
    (1e-7, "1e-7"),
    (0.1, "0.1"),
    (123.456, "123.456"),
]


class Numbers(unittest.TestCase):
    def test_numbers_serialize_as_javascript_writes_them(self):
        for value, want in NUMBERS:
            with self.subTest(value=value):
                self.assertEqual(digest.jcs(value), want)

    def test_the_digest_of_a_score_beyond_2_53_is_the_one_assemblers_compute(self):
        # threshold-beyond-2-53 with every score 12345678901234567890 and no threshold: the digest the Python,
        # TypeScript, Go and Rust assemblers and an independent RFC 8785 implementation all report for it.
        with open(os.path.join(ROOT, "conformance/cases/threshold-beyond-2-53/snapshot.json"), encoding="utf-8") as f:
            snapshot = copy.deepcopy(json.load(f))
        for batch in snapshot["batches"]:
            for item in batch["items"]:
                if "relevance" in item: item["relevance"] = 12345678901234567890
        snapshot["route_policy"]["slots"]["evidence.knowledge"]["min_relevance"] = 0
        self.assertEqual(digest.snapshot_digest(snapshot), "2752b53885eeca3eacdf4af2e9a3bb6276206ec390f4f882fdb7491b3059f84c")


if __name__ == "__main__":
    unittest.main()
