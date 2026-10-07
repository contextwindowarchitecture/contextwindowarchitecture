"""Builds conformance/cases/threshold-beyond-2-53 and digest-beyond-2-53 from tables of intended outcomes.

Every number in a snapshot is a double (R-2; conformance/README.md, Numbers). In threshold-beyond-2-53, with
min_relevance 9007199254740993, which rounds to 2^53, a score of 9007199254740992 is equal and passes,
9007199254740991 is below_threshold, and 9007199254740993 ties with 9007199254740992 on rank, so under budget pressure
the tied item with the later id is omitted first. In digest-beyond-2-53 the numbers have more than 17 significant
digits: 12345678901234567890, 12345678901234566500 and 1.2345678901234567e+19 are all the double 12345678901234567168,
which RFC 8785 writes as 12345678901234567000, its threshold, so all three pass, and 12345678901234566000 is the double
below and below_threshold. Its snapshot digest is what a digest that wrote each double's exact value would miss
(Snapshot digest). Expected results come from the INTENT column and the omissions, not from admission or fitting logic,
so a case can fail an implementation; the generator only checks that each payload fits after the omissions and, when
there are any, not before them.
"""
import copy, hashlib, json, os, re, sys
sys.dont_write_bytecode = True  # importing digest must not leave a __pycache__ for implementations to vendor
from digest import snapshot_digest  # noqa: E402
U16 = lambda s: s.encode("utf-16-be")  # strings order by UTF-16 code units (conformance/README.md, Ordering)

WEB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
DEFAULTS = json.load(open(os.path.join(WEB, "contract/slot-defaults.json")))
POLICY = ["token_budget", "variants", "conflict_policy", "lineage", "eligibility", "injection_risk"]
T = "2026-09-22T12:00:00Z"
TWO_53 = 2 ** 53
BIG = 12345678901234567890  # the double nearest it is 12345678901234567168, which ECMAScript writes 12345678901234567000

def item(id, slot, body, **fields):
    d = {"id": id, "slot": slot, "source": "src:" + id, "source_version": "1", "authority": DEFAULTS[slot]["authority"],
         "trust": "verified" if slot.startswith("governance.") else "unverified", "freshness": "2026-09-22T11:59:30Z", "body": body}
    for f in POLICY:
        d[f] = copy.deepcopy(DEFAULTS[slot][f])
    d.update(fields)
    return d

QUERY = ("conversation", "interaction", item("turn:18", "interaction.query", "Can I refund my Pro plan?"), "admit")
POLICY_ITEM = ("policy-registry", "policy", item("policy:v12", "governance.instructions", "Follow verified application policy."), "admit")

# Each case: (producer id, kind, item, intended outcome) rows, where the outcome is "admit" or the one reason the item must
# be excluded for, and the admitted ids budget pressure omits, in the order it omits them.
CASES = [
    {
        "id": "threshold-beyond-2-53", "profile": "numbers-fixture", "route_policy_version": "numbers/v1", "min_relevance": TWO_53 + 1,
        "rows": [
            QUERY,
            # 2^53 equals the threshold once both are doubles: equal passes (R-13).
            ("policy-corpus", "retrieval", item("kb:a", "evidence.knowledge", "Refunds within 30 days return to the original card.", relevance=TWO_53), "admit"),
            # 2^53 + 1 is the same double as 2^53, so kb:a and kb:b tie on rank and kb:b, the later id, sheds first (R-16).
            ("policy-corpus", "retrieval", item("kb:b", "evidence.knowledge", "Annual plans refund pro rata after 30 days end.", relevance=TWO_53 + 1), "admit"),
            # 2^53 - 1 is exact in a double and below the threshold.
            ("policy-corpus", "retrieval", item("kb:c", "evidence.knowledge", "Refunds take five business days.", relevance=TWO_53 - 1), "below_threshold"),
            POLICY_ITEM,
        ],
        "omitted": ["kb:b"], "tied": ("kb:a", "kb:b"),
        "rules": ["R-2", "R-13", "R-16", "R-21", "R-22"],
        "description": "Every number is a double: against min_relevance 9007199254740993, a score of 9007199254740992 is equal and passes, 9007199254740991 is below_threshold, and 9007199254740993 ties with 9007199254740992 on rank, so budget pressure omits the tied item with the later id.",
    },
    {
        "id": "digest-beyond-2-53", "profile": "digest-beyond-2-53", "route_policy_version": "digest-beyond-2-53/v1", "min_relevance": 12345678901234567000,
        "rows": [
            QUERY,
            # More than 17 significant digits: the double is 12345678901234567168, which equals the threshold's.
            ("policy-corpus", "retrieval", item("kb:a", "evidence.knowledge", "Refunds within 30 days return to the original card.", relevance=BIG), "admit"),
            # The same double written as a fraction with an exponent.
            ("policy-corpus", "retrieval", item("kb:b", "evidence.knowledge", "Annual plans refund pro rata after 30 days end.", relevance=float(BIG)), "admit"),
            # Below the threshold as an exact integer, but nearer 12345678901234567168 than the double below, so it passes.
            ("policy-corpus", "retrieval", item("kb:c", "evidence.knowledge", "Refunds take five business days.", relevance=12345678901234566500), "admit"),
            # Nearer the double below, 12345678901234565120, so it is below the threshold.
            ("policy-corpus", "retrieval", item("kb:d", "evidence.knowledge", "Refunds reach debit cards within ten days.", relevance=12345678901234566000), "below_threshold"),
            POLICY_ITEM,
        ],
        "omitted": [], "tied": None,
        "rules": ["R-2", "R-13", "R-22"],
        "description": "Every number is a double, and the snapshot digest writes each as JavaScript does: 12345678901234567890, 12345678901234566500 and 1.2345678901234567e+19 are all the double 12345678901234567168, which RFC 8785 writes as 12345678901234567000, so each meets min_relevance 12345678901234567000, while 12345678901234566000 rounds to the double below and is below_threshold.",
    },
]

WS = re.compile(r"[^\t\n\v\f\r \u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]+")
esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
placement = ["governance.instructions", "evidence.knowledge", "interaction.query"]

def render(items):
    parts, included = [], []
    for slot in placement:
        for it in sorted((i for i in items if i["slot"] == slot), key=lambda i: U16(i["id"])):
            body = esc(it["body"])
            parts.append(f'<{slot} id="{esc(it["id"]).replace(chr(34), "&quot;")}">\n{body}\n</{slot}>\n')
            included.append({"slot": slot, "item_id": it["id"], "tokens": len(WS.findall(body)), "source_version": it["source_version"], "eligibility": it["eligibility"]})
    payload = "".join(parts).encode()
    return payload, included, len(WS.findall(payload.decode()))

def build(c):
    rows, omitted = c["rows"], c["omitted"]
    route_policy = {
        "route": "support-chat", "version": c["route_policy_version"],
        "producers": {
            "conversation": {"kind": "interaction", "slots": ["interaction.query"]},
            "policy-corpus": {"kind": "retrieval", "slots": ["evidence.knowledge"]},
            "policy-registry": {"kind": "policy", "slots": ["governance.instructions"]},
        },
        "slots": {"evidence.knowledge": {"min_relevance": c["min_relevance"]}},
    }
    profile = {"spec": "cwa/draft", "id": c["profile"], "version": 1, "route": "support-chat", "model_family": None,
               "route_policy_version": route_policy["version"], "placement": [{"slot": s, "wrap": "xml:" + s} for s in placement],
               "evaluation": {"status": "unevaluated", "suite": None, "date": None, "result": None, "artifact": None}}

    admitted = [it for _, _, it, intent in rows if intent == "admit"]
    kept = [it for it in admitted if it["id"] not in omitted]
    payload, included, input_tokens = render(kept)
    _, _, before = render(admitted)
    budget = {"input": input_tokens, "reserved_output": 1200}
    if omitted:
        assert before > budget["input"], "the payload must not fit before the omission"
    by_id = {it["id"]: it for it in admitted}
    if c["tied"]:
        a, b = c["tied"]
        assert len(WS.findall(by_id[a]["body"])) == len(WS.findall(by_id[b]["body"])), "the tied items must be the same size, so only rank decides"

    batches = {}
    for producer, kind, it, _ in rows:
        batches.setdefault((producer, kind), []).append(it)
    snapshot = {
        "assembly_time": T, "scope": {"tenant": "acme"},
        "budget": budget, "profile": profile, "route_policy": route_policy,
        "tokenizer": "fixture-whitespace/v1", "renderer": "fixture-xml/v1",
        "batches": [{"producer": {"id": p, "kind": k}, "items": items, "excluded": []} for (p, k), items in batches.items()],
        "conflicts": [],
    }
    excluded = sorted(((p, it["id"], intent, it["slot"]) for p, _, it, intent in rows if intent != "admit"), key=lambda r: (U16(r[0]), U16(r[1])))
    trace = {
        "trace_id": c["id"],
        "profile": {"id": profile["id"], "version": profile["version"]},
        "budget": budget,
        "result": {"input_tokens": input_tokens, "hash": hashlib.sha256(payload).hexdigest()},
        "included": included, "compressed": [],
        "excluded": [{"item_id": rid, "reason": reason, "stage": "assembler", "slot": slot} for _, rid, reason, slot in excluded]
                    + [{"item_id": i, "reason": "over_budget", "stage": "assembler", "slot": by_id[i]["slot"]} for i in omitted],
        "conflicts": [], "refused": {"bool": False, "reason": None},
        "context": {"spec": "cwa/draft", "assembly_time": T, "route_policy_version": route_policy["version"], "tokenizer": "fixture-whitespace/v1",
                    "renderer": "fixture-xml/v1", "snapshot_digest": snapshot_digest(snapshot)},
        "defaults_filled": [],
    }
    case = {"id": c["id"], "rules": c["rules"], "description": c["description"]}
    out = os.path.join(WEB, "conformance/cases", c["id"])
    os.makedirs(out, exist_ok=True)
    for name, value in [("snapshot.json", snapshot), ("expected.trace.json", trace), ("case.json", case)]:
        open(os.path.join(out, name), "w").write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    open(os.path.join(out, "expected.payload.txt"), "wb").write(payload)
    print(f"{c['id']}: {len(rows)} candidates: {len(kept)} included, {len(excluded)} excluded at admission, {len(omitted)} omitted; budget {budget['input']}, before {before}; {trace['result']}")

for c in CASES:
    build(c)
