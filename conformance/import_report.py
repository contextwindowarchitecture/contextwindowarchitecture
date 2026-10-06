#!/usr/bin/env python3
"""Adds an implementation's conformance run to implementations/, or refreshes it.

    python3 conformance/import_report.py <checkout> <id> [--label <Language>] [--status]
    python3 conformance/import_report.py --verify [<id> ...]

The checkout is the implementation's own repository, clean, holding the conformance-report.json it publishes. The import
stores that report untouched in implementations/<id>.json, beside its source (the checkout's repository, commit and tags)
and the digest of every case as it was at the commit the report ran against, so a case published or changed since then
can be told apart (conformance/README.md, Reporting results). --status also stores the requirement statuses the checkout's
status.json claims, in implementations/<id>.status.json. A new id needs --label, the name the Assembler page gives it.

It refuses a checkout with uncommitted changes, a report that is not valid against the report schema of the commit it ran
against, and a report whose commit this repository's history does not hold, since its cases could not be read back.
--verify fetches each listed implementation's repository and confirms that the stored report is the
conformance-report.json it publishes at the stored commit; a report is the implementation's own claim (SPEC.md §1),
and this shows the registry holds that claim as made. It needs network access to GitHub.

Needs the jsonschema package, as check.py does.
"""
import argparse, hashlib, json, os, re, subprocess, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SCHEMA = "schema/conformance_report.schema.json"
ALLOWED = {"assembler": ["planned", "in progress", "implemented"], "boundary": ["planned", "in progress", "boundary-checked"], "application": ["documented"]}


def git(cwd, *args, binary=False):
    out = subprocess.run(["git", "-C", cwd, *args], capture_output=True, check=True).stdout
    return out if binary else out.decode("utf-8").strip()


def repository_of(url):
    """A remote URL as owner/repo when it is on GitHub, over HTTPS or SSH; any other URL as given; None for none."""
    if not url: return None
    m = re.match(r"^(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)([\w.-]+)/([\w.-]+?)(?:\.git)?/?$", url)
    return f"{m.group(1)}/{m.group(2)}" if m else url


def remote_of(checkout):
    """A checkout's origin remote as repository_of names it, or None when it has none, or is no git checkout."""
    try: return repository_of(git(checkout, "remote", "get-url", "origin"))
    except (subprocess.CalledProcessError, FileNotFoundError): return None


def source_of(checkout, *paths):
    """A checkout as an import records it: its repository, its commit, whether it is dirty (in paths, when given, else
    anywhere) and every tag on that commit, in name order, which the Assembler page shows beside the commit."""
    return {"repository": remote_of(checkout), "commit": git(checkout, "rev-parse", "HEAD"),
            "dirty": git(checkout, "status", "--porcelain", "--", *paths) != "",
            "tags": sorted(t for t in git(checkout, "tag", "--points-at", "HEAD").split("\n") if t)}


def digest(files):
    """A case's digest: SHA-256 over its files' names and SHA-256s, in name order, as JSON with no spaces."""
    rows = [[name, hashlib.sha256(data).hexdigest()] for name, data in sorted(files, key=lambda f: f[0].encode("utf-16-be"))]
    return hashlib.sha256(json.dumps(rows, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def case_digests_now(root=ROOT):
    """Each published case's and rejection case's digest as its files are now, keyed by case id."""
    out = {}
    for kind in ("cases", "rejections"):
        base = os.path.join(root, "conformance", kind)
        for cid in sorted(os.listdir(base)) if os.path.isdir(base) else []:
            out[cid] = digest([(n, open(os.path.join(base, cid, n), "rb").read()) for n in os.listdir(os.path.join(base, cid))])
    return out


_digests_at = {}
def case_digests_at(commit, root=ROOT):
    """Each case's digest as its files were at a commit of this repository, read from git, keyed by case id."""
    if (root, commit) not in _digests_at:
        listed = [line.split("\t", 1) for line in git(root, "ls-tree", "-r", commit, "--", "conformance/cases", "conformance/rejections").split("\n") if line]
        blobs = subprocess.run(["git", "-C", root, "cat-file", "--batch"], input="".join(meta.split()[2] + "\n" for meta, _ in listed).encode(),
                               capture_output=True, check=True).stdout
        by_case, at = {}, 0
        for _, path in listed:
            header_end = blobs.index(b"\n", at)
            size = int(blobs[at:header_end].split()[2])
            _, _, cid, name = path.split("/")
            by_case.setdefault(cid, []).append((name, blobs[header_end + 1:header_end + 1 + size]))
            at = header_end + 1 + size + 1
        _digests_at[(root, commit)] = {cid: digest(files) for cid, files in by_case.items()}
    return _digests_at[(root, commit)]


def claims_under(scopes, claims):
    """A reference assembler's status claims under this repository's scopes (contract/assembler-scope.json). implemented
    means tests exercise every clause of an assembler row, so on a row since scoped boundary, a narrower scope, the same
    tests prove boundary-checked. Nothing is widened: boundary-checked on an assembler row stays, and check.py rejects it."""
    scope = {s["id"]: s["scope"] for s in scopes}
    return [{**c, "status": "boundary-checked"} if c["status"] == "implemented" and scope.get(c["id"]) == "boundary" else c for c in claims]


def ran_at(report):
    """The commit a report's cases came from. A report written before the contract member named its repository calls
    it website_commit."""
    contract = report.get("contract") if isinstance(report, dict) else None
    return (contract.get("commit") or contract.get("website_commit")) if isinstance(contract, dict) else None


def names_this_repository(report, root=ROOT):
    """Whether a report's cases came from this repository. One written before the member named its repository came
    from the website, which authored the cases then."""
    named = (report.get("contract") or {}).get("repository", "contextwindowarchitecture/website")
    return named == remote_of(root)


def report_errors(report, root=ROOT):
    """A report's errors against the report schema as it stood at the commit the report ran against, when that commit
    is this repository's, else against the schema now; None when it is valid. A report is judged by the contract it
    ran on, as its cases are, so a change to the report schema leaves stored reports valid until they run again."""
    from jsonschema import Draft202012Validator, FormatChecker
    commit = ran_at(report)
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit): return ["the report names no contract commit"]
    if names_this_repository(report, root):
        try: schema = json.loads(git(root, "show", f"{commit}:{SCHEMA}"))
        except subprocess.CalledProcessError: return [f"this repository's history does not hold {commit}"]
    else: schema = read_json(os.path.join(root, SCHEMA))
    errors = [f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}" for e in Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(report)]
    return errors or None


def imported(source, report, root=ROOT):
    """A report as implementations/ stores it: {source, cases_at_run, report}. cases_at_run holds the digests of the
    cases as they were at the commit it ran against, or null when that run cannot be tied to a clean commit here."""
    clean = not report["contract"]["dirty"] and names_this_repository(report, root)
    return {"source": source, "cases_at_run": case_digests_at(ran_at(report), root) if clean else None, "report": report}


def entry_problems(entry, root=ROOT):
    """What is wrong with a stored entry: its shape, its source, the report's validity, and, when the report ran against
    this repository, digests that are not the ones its history holds for that commit."""
    if not isinstance(entry, dict) or sorted(entry) != ["cases_at_run", "report", "source"]: return ["carries something other than source, cases_at_run and report"]
    out, source, report = [], entry["source"], entry["report"]
    if not isinstance(source, dict) or sorted(source) != ["commit", "dirty", "repository", "tags"]: return ["source needs repository, commit, dirty and tags"]
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", source["repository"] or ""): out.append(f"source.repository {source['repository']!r} is not owner/repo")
    if not re.fullmatch(r"[0-9a-f]{40}", source["commit"] or ""): out.append("source.commit is not a commit")
    if source["dirty"] is not False: out.append("came from a checkout with uncommitted changes")
    if not isinstance(source["tags"], list) or source["tags"] != sorted(set(source["tags"])) or not all(isinstance(t, str) and t for t in source["tags"]):
        out.append("source.tags are not distinct names in order")
    if (errors := report_errors(report, root)): return out + [f"report: {e}" for e in errors]
    if report["contract"]["dirty"]: out.append("ran against a contract with uncommitted changes")
    elif names_this_repository(report, root) and entry["cases_at_run"] != case_digests_at(ran_at(report), root):
        out.append("cases_at_run are not the digests of the cases at the commit the report ran against")
    return out


def status_problems(entry, scopes):
    """What is wrong with stored status claims: every requirement in order, each with a status its scope allows."""
    rows = entry.get("requirements") if isinstance(entry, dict) else None
    if not isinstance(rows, list) or len(rows) != len(scopes): return [f"needs R-1 through R-{len(scopes)}"]
    return [f"{row.get('id')}: status {row.get('status')!r} does not fit scope {s['scope']}" for row, s in zip(rows, scopes)
            if row.get("id") != s["id"] or row.get("status") not in ALLOWED[s["scope"]]]


def tally(report, at_run, published):
    """Each published case's outcome in a report: passed (or, for a rejection case, rejected), failed, stale when the
    case changed after the run, or not run when the report lacks it. Every case is stale when at_run is None."""
    passed = {c["id"]: c["outcome"] == "passed" for c in report["cases"]} | {c["id"]: c["outcome"] == "rejected" for c in report.get("rejections", [])}
    return {cid: "not run" if cid not in passed else "stale" if (at_run or {}).get(cid) != d else "passed" if passed[cid] else "failed"
            for cid, d in published.items()}


def read_json(path):
    with open(path, encoding="utf-8") as f: return json.load(f)


def verify_entry(entry, base="https://github.com/"):
    """What differs between a stored report and the conformance-report.json its repository holds at the stored
    commit; empty when they are the same document. base is where repositories are fetched from."""
    import tempfile
    repository, commit = entry["source"]["repository"], entry["source"]["commit"]
    with tempfile.TemporaryDirectory(prefix="cwa-verify-") as clone:
        if subprocess.run(["git", "clone", "-q", "--filter=blob:none", "--no-checkout", f"{base}{repository}", clone], capture_output=True).returncode:
            return [f"{repository} could not be fetched from {base}"]
        if subprocess.run(["git", "-C", clone, "cat-file", "-e", f"{commit}^{{commit}}"], capture_output=True).returncode:
            return [f"{repository} does not hold commit {commit[:7]}; push it first"]
        try: published = json.loads(git(clone, "show", f"{commit}:conformance-report.json"))
        except subprocess.CalledProcessError: return [f"{repository} has no conformance-report.json at {commit[:7]}"]
    return [] if published == entry["report"] else [f"{repository} publishes a different conformance-report.json at {commit[:7]}"]


def write_json(path, value):
    with open(path, "w", encoding="utf-8") as f: f.write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def main(argv=None, root=ROOT):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    if argv is None: argv = sys.argv[1:]
    if argv[:1] == ["--verify"]:
        index = read_json(os.path.join(root, "implementations", "index.json"))
        ids = argv[1:] or [i["id"] for i in index]
        failed = False
        for i in ids:
            problems = verify_entry(read_json(os.path.join(root, "implementations", f"{i}.json")))
            failed = failed or bool(problems)
            print(f"{i}: " + ("; ".join(problems) if problems else "the stored report is the one its repository publishes at that commit"))
        sys.exit(1 if failed else 0)
    ap.add_argument("checkout"); ap.add_argument("id")
    ap.add_argument("--label", help="the name the Assembler page gives a new implementation, such as its language")
    ap.add_argument("--status", action="store_true", help="also store the checkout's status.json claims")
    args = ap.parse_args(argv)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", args.id): sys.exit(f"{args.id}: an id is lowercase letters, digits and dashes")
    index_path = os.path.join(root, "implementations", "index.json")
    index = read_json(index_path) if os.path.exists(index_path) else []
    if args.id not in [i["id"] for i in index] and not args.label: sys.exit(f"{args.id} is new: give it a --label")
    source = source_of(args.checkout)
    if source["dirty"]: sys.exit(f"{args.checkout} has uncommitted changes; import a clean checkout")
    report = read_json(os.path.join(args.checkout, "conformance-report.json"))
    if (errors := report_errors(report, root)): sys.exit("conformance-report.json is not valid: " + "; ".join(errors[:5]))
    if not names_this_repository(report, root): sys.exit(f"the report ran against {report['contract'].get('repository')}, not this repository")
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    write_json(os.path.join(root, "implementations", f"{args.id}.json"), imported(source, report, root))
    if args.id not in [i["id"] for i in index]: write_json(index_path, index + [{"id": args.id, "label": args.label}])
    elif args.label: write_json(index_path, [{**i, "label": args.label} if i["id"] == args.id else i for i in index])
    line = f"Imported {args.id} {source['commit'][:7]}: {sum(c['outcome'] == 'passed' for c in report['cases'])} of {len(report['cases'])} passing cases"
    line += f" and {sum(c['outcome'] == 'rejected' for c in report.get('rejections', []))} of {len(report.get('rejections', []))} rejected rejection cases, run against {ran_at(report)[:7]}"
    if args.status:
        claims = read_json(os.path.join(args.checkout, "status.json"))["requirements"]
        scopes = read_json(os.path.join(root, "contract", "assembler-scope.json"))
        write_json(os.path.join(root, "implementations", f"{args.id}.status.json"),
                   {"source": source, "requirements": [{"id": c["id"], "status": c["status"], "tests": len(c["evidence"])} for c in claims_under(scopes, claims)]})
        line += f", and {len(claims)} statuses"
    print(line + ".")


if __name__ == "__main__":
    main()
