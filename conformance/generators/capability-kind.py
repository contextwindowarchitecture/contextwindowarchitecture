"""Builds conformance/cases/capability-policy-kind from a table of intended outcomes.

The capability grant names a producer the route lists with kind policy. The route capability policy is
the grant's producer listed with kind capability_policy (R-15), so its tool is excluded with
capability_not_allowed although the allow-list names it. Expected results come from the INTENT column,
not from admission logic, so the case can fail an implementation.
"""
import copy, hashlib, json, os, re, sys
sys.dont_write_bytecode = True  # importing digest must not leave a __pycache__ for implementations to vendor
from digest import snapshot_digest  # noqa: E402
U16 = lambda s: s.encode("utf-16-be")  # strings order by UTF-16 code units (conformance/README.md, Ordering)

WEB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
OUT = os.path.join(WEB, "conformance/cases/capability-policy-kind")
DEFAULTS = json.load(open(os.path.join(WEB, "contract/slot-defaults.json")))
POLICY = ["token_budget", "variants", "conflict_policy", "lineage", "eligibility", "injection_risk"]
T = "2026-09-22T12:00:00Z"

def item(id, slot, body, **fields):
    d = {"id": id, "slot": slot, "source": "src:" + id, "source_version": "1", "authority": DEFAULTS[slot]["authority"],
         "trust": "verified" if slot.startswith("governance.") else "unverified", "freshness": "2026-09-22T11:59:30Z", "body": body}
    for f in POLICY:
        d[f] = copy.deepcopy(DEFAULTS[slot][f])
    d.update(fields)
    return d

# (producer id, kind, item, intended outcome): "admit" or the one reason it must be excluded for.
ROWS = [
    ("conversation", "interaction", item("turn:18", "interaction.query", "Can I refund my Pro plan?"), "admit"),
    ("policy-registry", "policy", item("policy:v12", "governance.instructions", "Follow verified application policy."), "admit"),
    # The grant names tool-registry, the allow-list names the tool, but the route lists tool-registry with kind policy.
    ("tool-registry", "policy", item("cap:issue_refund", "governance.capabilities", "issue_refund(order_id: string, amount: number)",
                                    source="capability-policy:support-chat@v3", source_version="v3"), "capability_not_allowed"),
]

route_policy = {
    "route": "support-chat", "version": "capability-kind/v1",
    "producers": {
        "conversation": {"kind": "interaction", "slots": ["interaction.query"]},
        "policy-registry": {"kind": "policy", "slots": ["governance.instructions"]},
        "tool-registry": {"kind": "policy", "slots": ["governance.capabilities"]},
    },
}
placement = ["governance.instructions", "governance.capabilities", "interaction.query"]
profile = {"spec": "cwa/draft", "id": "capability-kind-fixture", "version": 1, "route": "support-chat", "model_family": None,
           "route_policy_version": "capability-kind/v1", "placement": [{"slot": s, "wrap": "xml:" + s} for s in placement],
           "evaluation": {"status": "unevaluated", "suite": None, "date": None, "result": None, "artifact": None}}

batches = {}
for producer, kind, it, _ in ROWS:
    batches.setdefault((producer, kind), []).append(it)
snapshot = {
    "assembly_time": T, "scope": {"tenant": "acme", "user": "u_91"},
    "budget": {"input": 8192, "reserved_output": 1200}, "profile": profile, "route_policy": route_policy,
    "tokenizer": "fixture-whitespace/v1", "renderer": "fixture-xml/v1",
    "batches": [{"producer": {"id": p, "kind": k}, "items": items, "excluded": []} for (p, k), items in batches.items()],
    "capabilities": {"policy_producer": "tool-registry", "allow_list_version": "v3", "allowed_ids": ["cap:issue_refund"]},
    "conflicts": [],
}

admitted = [it for _, _, it, intent in ROWS if intent == "admit"]
excluded = sorted(((p, it["id"], intent, it["slot"]) for p, _, it, intent in ROWS if intent != "admit"), key=lambda r: (U16(r[0]), U16(r[1])))

WS = re.compile(r"[^\t\n\v\f\r \u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]+")
esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
parts, included = [], []
for slot in placement:
    for it in sorted((i for i in admitted if i["slot"] == slot), key=lambda i: U16(i["id"])):
        body = esc(it["body"])
        parts.append(f'<{slot} id="{esc(it["id"]).replace(chr(34), "&quot;")}">\n{body}\n</{slot}>\n')
        included.append({"slot": slot, "item_id": it["id"], "tokens": len(WS.findall(body)), "source_version": it["source_version"], "eligibility": it["eligibility"]})
payload = "".join(parts).encode()
trace = {
    "trace_id": "capability-policy-kind",
    "profile": {"id": profile["id"], "version": profile["version"]},
    "budget": snapshot["budget"],
    "result": {"input_tokens": len(WS.findall(payload.decode())), "hash": hashlib.sha256(payload).hexdigest()},
    "included": included, "compressed": [],
    "excluded": [{"item_id": rid, "reason": reason, "stage": "assembler", "slot": slot} for _, rid, reason, slot in excluded],
    "conflicts": [], "refused": {"bool": False, "reason": None},
    "context": {"spec": "cwa/draft", "assembly_time": T, "route_policy_version": route_policy["version"], "tokenizer": "fixture-whitespace/v1",
                "renderer": "fixture-xml/v1", "snapshot_digest": snapshot_digest(snapshot)},
    "defaults_filled": [],
}
case = {"id": "capability-policy-kind", "rules": ["R-15", "R-21", "R-22"],
        "description": "The capability grant names a producer the route lists with kind policy, so its tool is excluded with capability_not_allowed although the allow-list names it: the route capability policy is the grant's producer listed with kind capability_policy."}
os.makedirs(OUT, exist_ok=True)
for name, value in [("snapshot.json", snapshot), ("expected.trace.json", trace), ("case.json", case)]:
    open(os.path.join(OUT, name), "w").write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
open(os.path.join(OUT, "expected.payload.txt"), "wb").write(payload)
print(f"{len(ROWS)} candidates: {len(admitted)} admitted, {len(excluded)} excluded; {trace['result']}")
