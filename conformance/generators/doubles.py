"""Builds conformance/cases/threshold-beyond-2-53 from a table of intended outcomes.

Every number in a snapshot is a double (R-2; conformance/README.md, Numbers). With min_relevance 9007199254740993,
which rounds to 2^53, a score of 9007199254740992 is equal and passes, 9007199254740991 is below_threshold, and
9007199254740993 ties with 9007199254740992 on rank, so under budget pressure the tied item with the later id is
omitted first. Expected results come from the INTENT column and the omission below, not from admission or fitting
logic, so the case can fail an implementation; the generator only checks that the payload fits after the omission
and not before it.
"""
import copy, hashlib, json, os, re, sys
sys.dont_write_bytecode = True  # importing digest must not leave a __pycache__ for implementations to vendor
from digest import snapshot_digest  # noqa: E402
U16 = lambda s: s.encode("utf-16-be")  # strings order by UTF-16 code units (conformance/README.md, Ordering)

WEB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
OUT = os.path.join(WEB, "conformance/cases/threshold-beyond-2-53")
DEFAULTS = json.load(open(os.path.join(WEB, "contract/slot-defaults.json")))
POLICY = ["token_budget", "variants", "conflict_policy", "lineage", "eligibility", "injection_risk"]
T = "2026-09-22T12:00:00Z"
TWO_53 = 2 ** 53

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
    # 2^53 equals the threshold once both are doubles: equal passes (R-13).
    ("policy-corpus", "retrieval", item("kb:a", "evidence.knowledge", "Refunds within 30 days return to the original card.", relevance=TWO_53), "admit"),
    # 2^53 + 1 is the same double as 2^53, so kb:a and kb:b tie on rank and kb:b, the later id, sheds first (R-16).
    ("policy-corpus", "retrieval", item("kb:b", "evidence.knowledge", "Annual plans refund pro rata after 30 days end.", relevance=TWO_53 + 1), "admit"),
    # 2^53 - 1 is exact in a double and below the threshold.
    ("policy-corpus", "retrieval", item("kb:c", "evidence.knowledge", "Refunds take five business days.", relevance=TWO_53 - 1), "below_threshold"),
    ("policy-registry", "policy", item("policy:v12", "governance.instructions", "Follow verified application policy."), "admit"),
]
OMITTED = ["kb:b"]  # in the order budget pressure omits them

route_policy = {
    "route": "support-chat", "version": "numbers/v1",
    "producers": {
        "conversation": {"kind": "interaction", "slots": ["interaction.query"]},
        "policy-corpus": {"kind": "retrieval", "slots": ["evidence.knowledge"]},
        "policy-registry": {"kind": "policy", "slots": ["governance.instructions"]},
    },
    "slots": {"evidence.knowledge": {"min_relevance": TWO_53 + 1}},
}
placement = ["governance.instructions", "evidence.knowledge", "interaction.query"]
profile = {"spec": "cwa/draft", "id": "numbers-fixture", "version": 1, "route": "support-chat", "model_family": None,
           "route_policy_version": "numbers/v1", "placement": [{"slot": s, "wrap": "xml:" + s} for s in placement],
           "evaluation": {"status": "unevaluated", "suite": None, "date": None, "result": None, "artifact": None}}

WS = re.compile(r"[^\t\n\v\f\r    -     　﻿]+")
esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def render(items):
    parts, included = [], []
    for slot in placement:
        for it in sorted((i for i in items if i["slot"] == slot), key=lambda i: U16(i["id"])):
            body = esc(it["body"])
            parts.append(f'<{slot} id="{esc(it["id"]).replace(chr(34), "&quot;")}">\n{body}\n</{slot}>\n')
            included.append({"slot": slot, "item_id": it["id"], "tokens": len(WS.findall(body)), "source_version": it["source_version"], "eligibility": it["eligibility"]})
    payload = "".join(parts).encode()
    return payload, included, len(WS.findall(payload.decode()))

admitted = [it for _, _, it, intent in ROWS if intent == "admit"]
kept = [it for it in admitted if it["id"] not in OMITTED]
payload, included, input_tokens = render(kept)
_, _, before = render(admitted)
budget = {"input": input_tokens, "reserved_output": 1200}
assert before > budget["input"], "the payload must not fit before the omission"
by_id = {it["id"]: it for it in admitted}
assert len(WS.findall(by_id["kb:a"]["body"])) == len(WS.findall(by_id["kb:b"]["body"])), "the tied items must be the same size, so only rank decides"

batches = {}
for producer, kind, it, _ in ROWS:
    batches.setdefault((producer, kind), []).append(it)
snapshot = {
    "assembly_time": T, "scope": {"tenant": "acme"},
    "budget": budget, "profile": profile, "route_policy": route_policy,
    "tokenizer": "fixture-whitespace/v1", "renderer": "fixture-xml/v1",
    "batches": [{"producer": {"id": p, "kind": k}, "items": items, "excluded": []} for (p, k), items in batches.items()],
    "conflicts": [],
}
excluded = sorted(((p, it["id"], intent, it["slot"]) for p, _, it, intent in ROWS if intent != "admit"), key=lambda r: (U16(r[0]), U16(r[1])))
trace = {
    "trace_id": "threshold-beyond-2-53",
    "profile": {"id": profile["id"], "version": profile["version"]},
    "budget": budget,
    "result": {"input_tokens": input_tokens, "hash": hashlib.sha256(payload).hexdigest()},
    "included": included, "compressed": [],
    "excluded": [{"item_id": rid, "reason": reason, "stage": "assembler", "slot": slot} for _, rid, reason, slot in excluded]
                + [{"item_id": i, "reason": "over_budget", "stage": "assembler", "slot": by_id[i]["slot"]} for i in OMITTED],
    "conflicts": [], "refused": {"bool": False, "reason": None},
    "context": {"spec": "cwa/draft", "assembly_time": T, "route_policy_version": route_policy["version"], "tokenizer": "fixture-whitespace/v1",
                "renderer": "fixture-xml/v1", "snapshot_digest": snapshot_digest(snapshot)},
    "defaults_filled": [],
}
case = {"id": "threshold-beyond-2-53", "rules": ["R-2", "R-13", "R-16", "R-21", "R-22"],
        "description": "Every number is a double: against min_relevance 9007199254740993, a score of 9007199254740992 is equal and passes, 9007199254740991 is below_threshold, and 9007199254740993 ties with 9007199254740992 on rank, so budget pressure omits the tied item with the later id."}
os.makedirs(OUT, exist_ok=True)
for name, value in [("snapshot.json", snapshot), ("expected.trace.json", trace), ("case.json", case)]:
    open(os.path.join(OUT, name), "w").write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
open(os.path.join(OUT, "expected.payload.txt"), "wb").write(payload)
print(f"{len(ROWS)} candidates: {len(kept)} included, {len(excluded)} excluded at admission, {len(OMITTED)} omitted; budget {budget['input']}, before {before}; {trace['result']}")
