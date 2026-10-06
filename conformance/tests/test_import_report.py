"""conformance/import_report.py: what an import records, what it refuses, and how a stored report is judged and counted.

    python3 -m unittest discover -s conformance/tests
"""
import contextlib, io, json, os, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(ROOT, "conformance"))
import import_report as ir  # noqa: E402


def git(cwd, *args):
    return subprocess.run(["git", "-C", cwd, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "core.hooksPath=/dev/null",
                           "-c", "commit.gpgSign=false", "-c", "tag.gpgSign=false", "-c", "tag.forceSignAnnotated=false", *args],
                          capture_output=True, check=True, text=True).stdout.strip()


def load(path):
    with open(path, encoding="utf-8") as f: return json.load(f)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f: f.write(text)


class Temp(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="cwa-import-")
        self.addCleanup(shutil.rmtree, self.dir, True)

    def repo(self, name, remote=None):
        path = os.path.join(self.dir, name)
        os.makedirs(path)
        git(path, "init", "-q")
        if remote: git(path, "remote", "add", "origin", remote)
        return path

    def commit(self, path, message="c"):
        git(path, "add", "-A")
        git(path, "commit", "-q", "-m", message)
        return git(path, "rev-parse", "HEAD")


class Claims(unittest.TestCase):
    def test_an_implemented_claim_reads_as_boundary_checked_on_a_row_scoped_boundary_and_nothing_is_widened(self):
        scopes = [{"id": f"R-{i + 1}", "scope": s} for i, s in enumerate(["assembler", "boundary", "boundary", "boundary", "assembler"])]
        claims = [{"id": f"R-{i + 1}", "status": s, "evidence": ["t"]} for i, s in enumerate(["implemented", "implemented", "boundary-checked", "in progress", "boundary-checked"])]
        under = ir.claims_under(scopes, claims)
        self.assertEqual([c["status"] for c in under], ["implemented", "boundary-checked", "boundary-checked", "in progress", "boundary-checked"])
        self.assertEqual([c["evidence"] for c in under], [c["evidence"] for c in claims])
        self.assertEqual(ir.status_problems({"requirements": [{"id": c["id"], "status": c["status"]} for c in under]}, scopes),
                         ["R-5: status 'boundary-checked' does not fit scope assembler"])


class Sources(Temp):
    def test_a_remote_names_its_github_repository_as_owner_slash_repo(self):
        for url in ["https://github.com/contextwindowarchitecture/assembler-python", "https://github.com/contextwindowarchitecture/assembler-python.git",
                    "git@github.com:contextwindowarchitecture/assembler-python.git", "ssh://git@github.com/contextwindowarchitecture/assembler-python"]:
            self.assertEqual(ir.repository_of(url), "contextwindowarchitecture/assembler-python", url)
        self.assertEqual(ir.repository_of("https://gitlab.example.org/team/assembler.git"), "https://gitlab.example.org/team/assembler.git")
        self.assertIsNone(ir.repository_of(None))

    def test_a_source_records_repository_commit_dirtiness_in_the_given_paths_and_every_tag_on_the_commit(self):
        path = self.repo("x", "git@github.com:example/assembler-x.git")
        write(os.path.join(path, "a.txt"), "1"); self.commit(path, "one")
        git(path, "tag", "earlier")
        write(os.path.join(path, "a.txt"), "2"); head = self.commit(path, "two")
        git(path, "tag", "-a", "-m", "annotated", "v0.1.0"); git(path, "tag", "draft-release")
        self.assertEqual(ir.source_of(path), {"repository": "example/assembler-x", "commit": head, "dirty": False, "tags": ["draft-release", "v0.1.0"]})
        write(os.path.join(path, "b.txt"), "untracked")
        self.assertTrue(ir.source_of(path)["dirty"])
        self.assertFalse(ir.source_of(path, "a.txt")["dirty"])
        git(path, "checkout", "-q", "earlier")
        self.assertEqual(ir.source_of(path)["tags"], ["earlier"])


class Stored(unittest.TestCase):
    def test_every_listed_report_is_stored_whole_from_a_clean_checkout_and_valid_where_it_ran(self):
        index = load(os.path.join(ROOT, "implementations", "index.json"))
        self.assertTrue(index)
        for i in index:
            entry = load(os.path.join(ROOT, "implementations", f"{i['id']}.json"))
            self.assertEqual(ir.entry_problems(entry, ROOT), [], i["id"])
            self.assertRegex(entry["source"]["repository"], r"^[\w.-]+/[\w.-]+$")
            self.assertFalse(entry["report"]["contract"]["dirty"])

    def test_a_stored_entry_that_is_not_whole_or_came_from_a_dirty_checkout_has_problems(self):
        entry = load(os.path.join(ROOT, "implementations", "python.json"))
        self.assertTrue(ir.entry_problems({**entry, "extra": 1}, ROOT))
        self.assertTrue(ir.entry_problems({**entry, "source": {**entry["source"], "dirty": True}}, ROOT))
        self.assertTrue(ir.entry_problems({**entry, "source": {**entry["source"], "tags": ["b", "a"]}}, ROOT))


class ReportSchema(Temp):
    def test_a_report_is_judged_by_the_report_schema_at_the_commit_it_ran_against(self):
        root = self.repo("spec", "https://github.com/contextwindowarchitecture/website.git")
        schema = load(os.path.join(ROOT, ir.SCHEMA))
        before = json.loads(json.dumps(schema))
        before["properties"]["contract"] = {"type": "object", "properties": {"website_commit": {"type": "string", "pattern": "^[0-9a-f]{40}$"}, "dirty": {"type": "boolean"}},
                                            "required": ["website_commit", "dirty"], "additionalProperties": False}
        write(os.path.join(root, ir.SCHEMA), json.dumps(before)); old = self.commit(root, "website_commit")
        write(os.path.join(root, ir.SCHEMA), json.dumps(schema)); now = self.commit(root, "repository and commit")
        report = lambda contract: {"implementation": {"name": "x", "version": "1"}, "contract": contract, "cases": [{"id": "a", "rules": ["R-1"], "outcome": "passed"}]}
        named = "contextwindowarchitecture/website"
        self.assertIsNone(ir.report_errors(report({"website_commit": old, "dirty": False}), root), "the old shape at the old commit")
        self.assertIsNotNone(ir.report_errors(report({"website_commit": now, "dirty": False}), root), "the old shape at the new commit")
        self.assertIsNone(ir.report_errors(report({"repository": named, "commit": now, "dirty": False}), root), "the new shape at the new commit")
        self.assertIsNotNone(ir.report_errors(report({"repository": named, "commit": old, "dirty": False}), root), "the new shape at the old commit")
        self.assertIsNotNone(ir.report_errors(report({"repository": named, "dirty": False}), root), "no commit at all")
        self.assertIsNotNone(ir.report_errors(report({"repository": named, "commit": "b" * 40, "dirty": False}), root), "a commit this history lacks")


class Import(Temp):
    def setUp(self):
        super().setUp()
        self.root = self.repo("spec", "https://github.com/example/spec.git")
        for path in (ir.SCHEMA, "contract/assembler-scope.json"): os.makedirs(os.path.dirname(os.path.join(self.root, path)), exist_ok=True); shutil.copy(os.path.join(ROOT, path), os.path.join(self.root, path))
        write(os.path.join(self.root, "conformance/cases/a/case.json"), '{"id": "a"}')
        write(os.path.join(self.root, "conformance/rejections/r/case.json"), '{"id": "r"}')
        self.ran = self.commit(self.root, "cases")
        write(os.path.join(self.root, "conformance/cases/a/case.json"), '{"id": "a", "changed": true}'); self.commit(self.root, "a changes")
        write(os.path.join(self.root, "implementations/index.json"), json.dumps([{"id": "python", "label": "Python"}]))
        self.checkout = self.repo("impl", "https://github.com/example/assembler-x.git")
        self.report = {"implementation": {"name": "x", "version": "1"}, "contract": {"repository": "example/spec", "commit": self.ran, "dirty": False},
                       "cases": [{"id": "a", "rules": ["R-1"], "outcome": "passed"}], "rejections": [{"id": "r", "rules": ["R-17"], "outcome": "rejected"}]}
        self.put(self.report)

    def put(self, report):
        write(os.path.join(self.checkout, "conformance-report.json"), json.dumps(report))
        scopes = load(os.path.join(ROOT, "contract/assembler-scope.json"))
        write(os.path.join(self.checkout, "status.json"), json.dumps({"requirements": [{"id": s["id"], "status": "implemented" if s["scope"] != "application" else "documented", "evidence": ["t1", "t2"]} for s in scopes]}))
        return self.commit(self.checkout)

    def run_import(self, *args):
        with contextlib.redirect_stdout(io.StringIO()): ir.main([self.checkout, *args], root=self.root)
        return load(os.path.join(self.root, "implementations", f"{args[0]}.json"))

    def test_an_import_stores_the_report_whole_beside_its_source_and_the_digests_of_the_cases_it_ran(self):
        head = git(self.checkout, "rev-parse", "HEAD")
        git(self.checkout, "tag", "draft-release")
        entry = self.run_import("python", "--status")
        self.assertEqual(entry["source"], {"repository": "example/assembler-x", "commit": head, "dirty": False, "tags": ["draft-release"]})
        self.assertEqual(entry["report"], self.report)
        self.assertEqual(entry["cases_at_run"], ir.case_digests_at(self.ran, self.root))
        self.assertEqual(ir.entry_problems(entry, self.root), [])
        self.assertEqual(ir.tally(entry["report"], entry["cases_at_run"], ir.case_digests_now(self.root)), {"a": "stale", "r": "passed"}, "a changed after the run")
        status = load(os.path.join(self.root, "implementations", "python.status.json"))
        scopes = load(os.path.join(self.root, "contract/assembler-scope.json"))
        self.assertEqual(ir.status_problems(status, scopes), [], "implemented on a boundary row reads as boundary-checked")
        self.assertEqual({r["tests"] for r in status["requirements"]}, {2})

    def test_a_new_implementation_needs_a_label_and_joins_the_index(self):
        with self.assertRaises(SystemExit): self.run_import("zig")
        self.run_import("zig", "--label", "Zig")
        self.assertEqual(load(os.path.join(self.root, "implementations", "index.json")),
                         [{"id": "python", "label": "Python"}, {"id": "zig", "label": "Zig"}])

    def test_an_import_refuses_a_dirty_checkout_an_invalid_report_and_a_commit_this_history_lacks(self):
        write(os.path.join(self.checkout, "scratch.txt"), "uncommitted")
        with self.assertRaises(SystemExit): self.run_import("python")
        os.remove(os.path.join(self.checkout, "scratch.txt"))
        self.put({**self.report, "cases": [{"id": "a", "rules": ["R-1"], "outcome": "partial"}]})
        with self.assertRaises(SystemExit): self.run_import("python")
        self.put({**self.report, "contract": {**self.report["contract"], "commit": "b" * 40}})
        with self.assertRaises(SystemExit): self.run_import("python")
        self.put({**self.report, "contract": {**self.report["contract"], "repository": "example/elsewhere"}})
        with self.assertRaises(SystemExit): self.run_import("python")
        self.assertFalse(os.path.exists(os.path.join(self.root, "implementations", "python.json")), "nothing was stored")


class Digest(unittest.TestCase):
    def test_a_case_digest_is_over_its_files_names_and_hashes_in_name_order_whatever_order_they_come_in(self):
        import hashlib
        files = [("snapshot.json", b"{}"), ("case.json", b'{"id": "a"}'), ("Z.txt", b"z")]
        rows = sorted([name, hashlib.sha256(data).hexdigest()] for name, data in files)
        want = hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(ir.digest(files), want)
        self.assertEqual(ir.digest(list(reversed(files))), want)


class Verify(Temp):
    def test_a_stored_report_is_the_one_its_repository_publishes_at_the_named_commit(self):
        os.makedirs(os.path.join(self.dir, "remotes", "example"))
        impl = self.repo("remotes/example/assembler-x")
        report = {"implementation": {"name": "x", "version": "1"}, "contract": {"repository": "example/spec", "commit": "a" * 40, "dirty": False}, "cases": []}
        write(os.path.join(impl, "conformance-report.json"), json.dumps(report, indent=2))
        head = self.commit(impl)
        entry = {"source": {"repository": "example/assembler-x", "commit": head, "dirty": False, "tags": []}, "cases_at_run": None, "report": report}
        base = "file://" + os.path.join(self.dir, "remotes") + "/"
        self.assertEqual(ir.verify_entry(entry, base), [])
        self.assertTrue(ir.verify_entry({**entry, "report": {**report, "cases": [{"id": "a", "rules": ["R-1"], "outcome": "passed"}]}}, base), "a report the commit does not publish")
        self.assertTrue(ir.verify_entry({**entry, "source": {**entry["source"], "commit": "b" * 40}}, base), "a commit the repository lacks")
        self.assertTrue(ir.verify_entry({**entry, "source": {**entry["source"], "repository": "example/missing"}}, base), "a repository that does not exist")


class Tally(unittest.TestCase):
    def test_a_case_changed_or_published_after_a_run_does_not_count_as_passing(self):
        published = {"a": "d1", "b": "d2", "c": "d3", "d": "d4"}
        report = {"cases": [{"id": "a", "outcome": "passed"}, {"id": "b", "outcome": "passed"}, {"id": "c", "outcome": "failed"}], "rejections": []}
        self.assertEqual(ir.tally(report, {"a": "d1", "b": "old", "c": "d3"}, published), {"a": "passed", "b": "stale", "c": "failed", "d": "not run"})
        self.assertEqual(ir.tally(report, None, published), {"a": "stale", "b": "stale", "c": "stale", "d": "not run"})
        self.assertEqual(ir.tally({"cases": [], "rejections": [{"id": "a", "outcome": "rejected"}]}, {"a": "d1"}, {"a": "d1"}), {"a": "passed"})


if __name__ == "__main__":
    unittest.main()
