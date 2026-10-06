"""Builds conformance/registry/: the published example profiles, a few conformance route policies, the
illustrative route policies the example profiles name, and a lock pinning each by the digest
conformance/README.md's Registry section defines.

Implementations check that they compute the same digests, and conformance/check.py checks the lock against the
files it pins.
"""
import hashlib, json, os, sys

WEB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
POLICY_CASES = ["fixture-three-slot", "admission-reasons", "budget-route-order", "conflict-fact"]


def read(path):
    return json.load(open(os.path.join(WEB, path)))


def canonical(value):
    # RFC 8785 for these documents: ASCII keys, and numbers whose shortest round-trip form Python and
    # JavaScript print alike (no exponents).
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


profiles = read("examples/profiles.json") + [read("examples/fixture-profile.json")]
policies = [read(f"conformance/cases/{case}/snapshot.json")["route_policy"] for case in POLICY_CASES] + read("examples/route-policies.json")
lock = {
    "profiles": [{"id": p["id"], "version": p["version"], "sha256": digest({k: v for k, v in p.items() if k != "evaluation"})} for p in profiles],
    "route_policies": [{"route": p["route"], "version": p["version"], "sha256": digest(p)} for p in policies],
}
out = os.path.join(WEB, "conformance/registry")
os.makedirs(out, exist_ok=True)
for name, value in [("profiles.json", profiles), ("route-policies.json", policies), ("lock.json", lock)]:
    open(os.path.join(out, name), "w").write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
print(f"registry: {len(profiles)} profiles, {len(policies)} route policies")
