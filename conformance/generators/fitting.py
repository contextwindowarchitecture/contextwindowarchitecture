"""Builds the budget-fitting and refusal conformance cases from tables of intended outcomes.

Each case lists its candidates, the admission reason for any it excludes, the token_budget cap
actions it intends ("caps"), the max_tokens slot-cap actions it intends ("slot_caps"), and the
budget-pressure actions it intends ("actions"), each in order: ("omit", id) or
("compress", id, variant_id), or ("hold", id, "omit") or ("hold", id, "compress", variant_id) for a
reduction a slot floor withholds, which freezes the slot. Expected traces and
payloads come from those tables, not from a fitting algorithm, so the cases can fail an
implementation. The generator only checks that each table agrees with the budget: the payload
fits after the last action and not before it, each capped slot is within its cap after its last
slot-cap action and not before it, each chosen variant is the one conformance/README.md's
Fitting section selects, no reduction leaves a floored slot below min_tokens or touches a frozen
slot, each hold would have, and a slot_floor_over_budget refusal leaves only frozen or protected items.
A case may also declare conflict groups ("groups") that escalate and are surfaced; fitting may still
omit a member, and the members it keeps render marked (R-11).
"""
import copy, hashlib, json, os, re, sys
sys.dont_write_bytecode = True  # importing digest must not leave a __pycache__ for implementations to vendor
from digest import snapshot_digest  # noqa: E402
from order import placed  # noqa: E402
U16 = lambda s: s.encode("utf-16-be")  # strings order by UTF-16 code units (conformance/README.md, Ordering)

WEB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
DEFAULTS = json.load(open(os.path.join(WEB, "contract/slot-defaults.json")))
POLICY = ["token_budget", "variants", "conflict_policy", "lineage", "eligibility", "injection_risk"]
AUTH = {"governance.instructions": "governing", "governance.examples": "governing", "governance.output_contract": "governing",
        "state.user": "state", "state.task": "state", "evidence.knowledge": "reference_only", "evidence.tool_results": "observation",
        "interaction.memory": "generated", "interaction.history": "user", "interaction.query": "user"}
PRODUCER = {"governance.instructions": "policy-registry", "governance.examples": "policy-registry", "governance.output_contract": "policy-registry",
            "state.user": "state-svc", "state.task": "state-svc", "evidence.knowledge": "policy-corpus", "evidence.tool_results": "crm-mcp",
            "interaction.memory": "memory-svc", "interaction.history": "conversation", "interaction.query": "conversation"}
KINDS = {"policy-registry": "policy", "state-svc": "state", "policy-corpus": "retrieval", "crm-mcp": "mcp",
         "memory-svc": "memory", "conversation": "interaction"}
T = "2026-09-22T12:00:00Z"
SCOPE = {"tenant": "acme", "user": "u_91", "session": "s_7", "task": "refund_request"}
WS = re.compile(r"[^\t\n\v\f\r    -     　﻿]+")
count = lambda text: len(WS.findall(text))
# conformance/README.md, Tokenizers and renderers.
TOKENIZERS = {"fixture-whitespace/v1": count, "estimate-utf8/v1": lambda text: (len(text.encode("utf-8")) + 3) // 4}
# The charged count a margin reserves headroom on (R-16): n × (100 + m) / 100, rounded up.
charged = lambda n, margin: (n * (100 + margin) + 99) // 100
esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def item(id, slot, body, **fields):
    d = {"id": id, "slot": slot, "source": "src:" + id, "source_version": "1", "authority": AUTH[slot],
         "trust": "verified" if slot.startswith("governance.") else "unverified", "freshness": "2026-09-22T11:59:00Z", "body": body}
    for f in POLICY:
        d[f] = copy.deepcopy(DEFAULTS[slot][f])
    if slot == "evidence.knowledge":
        d.update(scope={"tenant": "acme"}, freshness="2026-09-12T15:30:00Z")
    if slot == "interaction.memory":
        d.update(source="turn:3", expires="2026-12-01T00:00:00Z")
    unset = fields.pop("unset", ())  # policy fields the producer leaves for the assembler to fill (R-3)
    d.update(fields)
    for f in unset:
        del d[f]
    return d


def variant(id, body, method="extract"):
    return {"id": id, "body": body, "method": method, "lineage": "extracted"}


PLACEMENT = ["governance.instructions", "governance.examples", "governance.output_contract", "state.user", "state.task",
             "evidence.knowledge", "evidence.tool_results", "interaction.memory", "interaction.history", "interaction.query"]
BASE_SLOTS = {"evidence.knowledge": {"min_relevance": 0.5, "required_scope": ["tenant"]}}


def render(placement, kept, count=count, marks={}):
    """kept: {id: (item, body)}; marks: {id: group id} for members of surfaced groups. Returns payload
    bytes and included rows, per the fixture renderer."""
    parts, included = [], []
    for slot in placement:
        for it, body in placed(slot, (v for v in kept.values() if v[0]["slot"] == slot), lambda v: v[0]):
            b = esc(body)
            mark = f' conflict="{esc(marks[it["id"]]).replace(chr(34), "&quot;")}"' if it["id"] in marks else ""
            parts.append(f'<{slot} id="{esc(it["id"]).replace(chr(34), "&quot;")}"{mark}>\n{b}\n</{slot}>\n')
            included.append({"slot": slot, "item_id": it["id"], "tokens": count(b), "source_version": it["source_version"],
                             "eligibility": it.get("eligibility", DEFAULTS[it["slot"]]["eligibility"])})
    return "".join(parts).encode(), included


def tokens(placement, kept, count=count, marks={}):
    return count(render(placement, kept, count, marks)[0].decode())


def build(case):
    name, budget, placement = case["id"], case["budget"], case.get("placement", PLACEMENT)
    tokenizer, margin = case.get("tokenizer", "fixture-whitespace/v1"), case.get("margin")
    count = TOKENIZERS[tokenizer]
    rows = case["items"]  # (item, admission intent: "admit" or a reason)
    policy = {"route": "support-chat", "version": f"{name}/v1",
              "producers": {p: {"kind": k, "slots": sorted(s for s, q in PRODUCER.items() if q == p)} for p, k in KINDS.items()},
              "slots": copy.deepcopy(BASE_SLOTS)}
    for key, value in case.get("policy", {}).items():
        if key == "slots":
            for slot, rules in value.items():
                policy["slots"].setdefault(slot, {}).update(rules)
        else:
            policy[key] = value
    # R-20: one profile id and version name one profile, so each case's profile carries the case's own id.
    profile = {"spec": "cwa/draft", "id": name, "version": 1, "route": "support-chat", "model_family": None, "route_policy_version": policy["version"],
               "placement": [{"slot": s, "wrap": "xml:" + s} for s in placement],
               "evaluation": {"status": "unevaluated", "suite": None, "date": None, "result": None, "artifact": None}}
    batches = {}
    for it, _ in rows:
        batches.setdefault(PRODUCER[it["slot"]], []).append(it)
    snapshot = {"assembly_time": T, "scope": SCOPE, "budget": {"input": budget, "reserved_output": 1024, **({"margin_percent": margin} if margin is not None else {})}, "profile": profile,
                "route_policy": policy, "tokenizer": tokenizer, "renderer": "fixture-xml/v1",
                "batches": [{"producer": {"id": p, "kind": KINDS[p]}, "items": batches[p], "excluded": []} for p in sorted(batches, key=U16)],
                "conflicts": [{k: g[k] for k in ("id", "kind", "fact", "items") if k in g} for g in case.get("groups", [])]}

    admission = sorted(((PRODUCER[it["slot"]], it["id"], r, it["slot"]) for it, r in rows if r != "admit"), key=lambda r: (U16(r[0]), U16(r[1])))
    excluded = [{"item_id": i, "reason": r, "stage": "assembler", "slot": s} for _, i, r, s in admission]
    admitted = {it["id"]: it for it, r in rows if r == "admit"}
    kept = {i: (it, it["body"]) for i, it in admitted.items()}
    # Surfaced groups keep every member through resolution; fitting may still omit one (R-11).
    for g in case.get("groups", []):
        assert (g["decided_by"], g["resolution"]) == ("escalated", "surfaced"), f"{name}: fitting cases hold surfaced groups only"
        assert sum(i in admitted for i in g["items"]) >= 2, f"{name}: {g['id']} would be moot"
    marks = {i: g["id"] for g in case.get("groups", []) for i in g["items"] if i in admitted}
    fits = lambda state: charged(tokens(placement, state, count, marks), margin or 0) <= budget
    refusal, recovery, actions, caps = case.get("refuse"), case.get("recovery"), case.get("actions", []), case.get("caps", [])
    rank = {"droppable": 0, "compressible": 1, "protected": 2}
    upgrades = policy.get("tier_upgrades", {})
    tier = lambda it: it.get("tier") or max(DEFAULTS[it["slot"]]["tier"], upgrades.get(it["slot"], "droppable"), key=rank.get)
    size = lambda body: count(esc(body))
    over_cap = lambda it: it["token_budget"] is not None and size(it["body"]) > it["token_budget"]
    protected = {i: v for i, v in kept.items() if tier(v[0]) == "protected"}
    slot_caps = {slot: rules["max_tokens"] for slot, rules in policy["slots"].items() if "max_tokens" in rules}
    # A slot's size sums included[].tokens: every occurrence of every kept item in the slot.
    slot_size = lambda state, slot: placement.count(slot) * sum(count(esc(b)) for it, b in state.values() if it["slot"] == slot)
    over_slot_cap = lambda state, slot: slot_size(state, slot) > slot_caps[slot]
    slot_key = lambda slot: (policy["slots"].get(slot, {}).get("priority", 0), U16(slot))

    # Placement (R-20): the profile places the required slots, unplaced items are excluded unless
    # protected, and an admitted protected item in an unplaced slot refuses.
    assert {"governance.instructions", "interaction.query"} <= set(placement), f"{name}: the profile must place instructions and query"
    assert not policy.get("parser") or "governance.output_contract" in placement, f"{name}: a parser route's profile must place the output contract"
    for it, r in rows:
        if r == "slot_unplaced":
            assert it["slot"] not in placement and tier(it) != "protected", f"{name}: {it['id']} is placed or protected"
    unplaced = [i for i, it in admitted.items() if it["slot"] not in placement]
    assert all(i in protected for i in unplaced), f"{name}: unprotected {unplaced} should be slot_unplaced"
    assert bool(unplaced) == (refusal == "protected_slot_unplaced") or refusal == "required_slot_missing", \
        f"{name}: protected items {unplaced} are unplaced, so the refusal is protected_slot_unplaced"

    if refusal == "protected_content_over_budget":
        assert not fits(protected) or any(over_cap(v[0]) for v in protected.values()) or \
            any(over_slot_cap(protected, s) for s in slot_caps), f"{name}: protected items fit"
    compressed = {}
    if refusal not in ("required_slot_missing", "protected_slot_unplaced", "protected_content_over_budget"):
        assert not any(over_cap(v[0]) for v in protected.values()), f"{name}: a protected item exceeds its cap"
        assert not any(over_slot_cap(protected, s) for s in slot_caps), f"{name}: protected items exceed a slot cap"
        assert {i for i, it in admitted.items() if over_cap(it)} == {a[1] for a in caps}, f"{name}: caps must list exactly the items over their cap"
        for action in caps:
            it = admitted[action[1]]
            within = [v for v in it["variants"] if size(v["body"]) <= it["token_budget"]]
            if action[0] == "omit":
                assert tier(it) == "droppable" or not within, f"{name}: {it['id']} has a variant within its cap"
                del kept[it["id"]]
                excluded.append({"item_id": it["id"], "reason": "over_budget", "stage": "assembler", "slot": it["slot"]})
            else:
                assert tier(it) == "compressible", f"{name}: only compressible items take a variant for their cap"
                chosen = max(within, key=lambda v: (size(v["body"]), -it["variants"].index(v)))
                assert chosen["id"] == action[2], f"{name}: {it['id']} should take {chosen['id']} for its cap"
                kept[it["id"]] = (it, chosen["body"])
                compressed[it["id"]] = chosen
        slot_actions = case.get("slot_caps", [])
        acted = [admitted[a[1]]["slot"] for a in slot_actions]
        assert set(acted) == {s for s in slot_caps if over_slot_cap(kept, s)}, f"{name}: slot_caps must act on exactly the slots over their cap"
        assert acted == sorted(acted, key=slot_key), f"{name}: slots are capped in shedding order"
        for action in slot_actions:
            it = admitted[action[1]]
            slot = it["slot"]
            assert over_slot_cap(kept, slot), f"{name}: {slot} is already within its cap before {action}"
            assert tier(it) != "protected", f"{name}: {it['id']} is protected"
            assert tier(it) == "droppable" or not any(tier(v[0]) == "droppable" for v in kept.values() if v[0]["slot"] == slot), \
                f"{name}: droppable items leave {slot} before {it['id']} is reduced"
            if action[0] == "omit":
                del kept[it["id"]]
                excluded.append({"item_id": it["id"], "reason": "over_budget", "stage": "assembler", "slot": slot})
                compressed.pop(it["id"], None)
            else:
                shorter = [v for v in it["variants"] if size(v["body"]) < size(kept[it["id"]][1])]
                chosen = next(v for v in shorter if v["id"] == action[2])
                within = lambda v: not over_slot_cap({**kept, it["id"]: (it, v["body"])}, slot)
                if within(chosen):
                    assert not any(within(v) for v in shorter if size(v["body"]) > size(chosen["body"])), f"{name}: a longer variant of {it['id']} is within the slot cap"
                else:
                    assert not any(within(v) for v in shorter), f"{name}: a variant of {it['id']} is within the slot cap, so the shortest is wrong"
                    assert size(chosen["body"]) == min(size(v["body"]) for v in shorter), f"{name}: {chosen['id']} is not the shortest variant"
                kept[it["id"]] = (it, chosen["body"])
                compressed[it["id"]] = chosen
        assert not any(over_slot_cap(kept, s) for s in slot_caps), f"{name}: a slot is still over its cap"
        assert fits(kept) == (not actions), f"{name}: the items {'fit' if fits(kept) else 'do not fit'} before budget pressure"

    floors = {slot: rules["min_tokens"] for slot, rules in policy["slots"].items() if "min_tokens" in rules}
    frozen = set()
    for n, action in enumerate(actions):
        it = admitted[action[1]]
        assert it["slot"] not in frozen, f"{name}: {action} reduces frozen {it['slot']}"
        if action[0] == "hold":
            assert it["slot"] in floors, f"{name}: {it['slot']} has no floor to hold"
            after = {k: v for k, v in kept.items() if k != it["id"]} if action[2] == "omit" else \
                {**kept, it["id"]: (it, next(v for v in it["variants"] if v["id"] == action[3])["body"])}
            assert slot_size(after, it["slot"]) < floors[it["slot"]], f"{name}: {action} would keep {it['slot']} at its floor"
            frozen.add(it["slot"])
            assert not fits(kept) and n < len(actions) - 1 or refusal == "slot_floor_over_budget", f"{name}: a hold ends a fitting case"
            continue
        if action[0] == "omit":
            del kept[it["id"]]
            excluded.append({"item_id": it["id"], "reason": "over_budget", "stage": "assembler", "slot": it["slot"]})
            compressed.pop(it["id"], None)
        else:
            current = count(esc(kept[it["id"]][1]))
            shorter = [v for v in it["variants"] if count(esc(v["body"])) < current]
            chosen = next(v for v in shorter if v["id"] == action[2])
            with_variant = lambda v: fits({**kept, it["id"]: (it, v["body"])})
            size = lambda v: count(esc(v["body"]))
            if with_variant(chosen):
                assert not any(with_variant(v) for v in shorter if size(v) > size(chosen)), f"{name}: a longer variant of {it['id']} fits"
            else:
                assert not any(with_variant(v) for v in shorter), f"{name}: a variant of {it['id']} fits, so the shortest is wrong"
                assert chosen == min(shorter, key=size), f"{name}: {chosen['id']} is not the shortest variant"
            kept[it["id"]] = (it, chosen["body"])
            compressed[it["id"]] = chosen
        assert it["slot"] not in floors or slot_size(kept, it["slot"]) >= floors[it["slot"]], f"{name}: {action} breaks {it['slot']}'s floor"
        ends = n == len(actions) - 1 and refusal != "slot_floor_over_budget"
        assert fits(kept) == ends, f"{name}: action {n} {action} leaves the payload {'fitting' if fits(kept) else 'over budget'}"
    if refusal == "slot_floor_over_budget":
        assert not fits(kept), f"{name}: the payload fits"
        stuck = [i for i, (x, _) in kept.items() if tier(x) != "protected" and x["slot"] not in frozen]
        assert not stuck, f"{name}: {stuck} could still be shed"

    payload, included = render(placement, kept, count, marks)
    trace = {
        "trace_id": name, "profile": {"id": profile["id"], "version": 1}, "budget": snapshot["budget"],
        "result": None if refusal else {"input_tokens": count(payload.decode()), "hash": hashlib.sha256(payload).hexdigest()},
        "included": [] if refusal else included,
        "compressed": [] if refusal else [
            {"slot": row["slot"], "item_id": row["item_id"], "from": count(esc(admitted[row["item_id"]]["body"])), "to": row["tokens"],
             "method": compressed[row["item_id"]]["method"], "variant_id": compressed[row["item_id"]]["id"]}
            for row in included if row["item_id"] in compressed],
        "excluded": excluded,
        "conflicts": [{"group_id": g["id"], "kind": g["kind"], "items": sorted(g["items"], key=U16), "decided_by": g["decided_by"],
                       "resolution": g["resolution"]} for g in sorted(case.get("groups", []), key=lambda g: U16(g["id"]))],
        "refused": {"bool": bool(refusal), "reason": refusal},
        "context": {"spec": "cwa/draft", "assembly_time": T, "route_policy_version": policy["version"], "tokenizer": tokenizer, "renderer": "fixture-xml/v1", "snapshot_digest": snapshot_digest(snapshot)},
        "defaults_filled": [{"item_id": i, "field": f} for i, f in
                            sorted(((it["id"], f) for it, _ in rows for f in POLICY if f not in it), key=lambda x: (U16(x[0]), POLICY.index(x[1])))],
    }
    if recovery:
        trace["recovery"] = {"action": recovery}
    out = os.path.join(WEB, "conformance/cases", name)
    os.makedirs(out, exist_ok=True)
    for file, value in [("snapshot.json", snapshot), ("expected.trace.json", trace),
                        ("case.json", {"id": name, "rules": case["rules"], "description": case["description"]})]:
        open(os.path.join(out, file), "w").write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    payload_file = os.path.join(out, "expected.payload.txt")
    if refusal:
        if os.path.exists(payload_file):
            os.remove(payload_file)
    else:
        open(payload_file, "wb").write(payload)
    print(f"{name}: budget {budget}, {len(admitted)} admitted, {len(actions)} actions -> "
          f"{refusal or trace['result']['input_tokens']}{' / ' + recovery if recovery else ''}")


POLICY_TEXT = "Follow verified refund policy and cite the evidence you use."
QUERY = "Can I refund my Pro plan?"
CONTRACT = "Answer as JSON with fields decision and citations."

FLOOR_ITEMS = [
    (item("policy:v12", "governance.instructions", POLICY_TEXT), "admit"),
    (item("ex:1", "governance.examples", "Example: refunds within thirty days are approved."), "admit"),
    (item("kb:a", "evidence.knowledge", "Pro plans refund in full within thirty days of purchase.", relevance=0.9,
          variants=[variant("kb:a~short", "Pro: full refund, 30 days.")]), "admit"),
    (item("kb:b", "evidence.knowledge", "Annual plans refund pro rata for unused months.", relevance=0.7), "admit"),
    (item("turn:15", "interaction.history", "We upgraded to Pro two weeks ago but the seats are wrong.", freshness="2026-09-22T11:52:00Z"), "admit"),
    (item("turn:16", "interaction.history", "Seats cannot change.", freshness="2026-09-22T11:54:00Z"), "admit"),
    (item("turn:18", "interaction.query", QUERY), "admit"),
]

CASES = [
    {
        "id": "budget-droppable-order",
        "rules": ["R-16", "R-21", "R-22"],
        "description": "Droppable items shed one at a time by slot priority, then oldest first, and shedding stops as soon as the payload fits; compressible and protected items are untouched.",
        "budget": 44,
        "policy": {"slots": {"governance.examples": {"priority": 1}}},
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), "admit"),
            (item("ex:1", "governance.examples", "Example: refunds within thirty days are approved.", freshness="2026-09-01T00:00:00Z"), "admit"),
            (item("ex:2", "governance.examples", "Example: annual plans refund pro rata.", freshness="2026-09-10T00:00:00Z"), "admit"),
            (item("user:plan", "state.user", "plan=pro since 2026-09-01", scope={"tenant": "acme", "user": "u_91"}), "admit"),
            (item("kb:a", "evidence.knowledge", "Pro plans refund in full within 30 days.", relevance=0.9), "admit"),
            (item("turn:18", "interaction.query", QUERY), "admit"),
        ],
        "actions": [("omit", "user:plan"), ("omit", "ex:1")],
    },
    {
        "id": "budget-variant-choice",
        "rules": ["R-16", "R-18", "R-21"],
        "description": "Once droppable items are gone, compressible items take variants lowest rank first: the longest variant that makes the payload fit, else the shortest; fitting stops before later slots are reached.",
        "budget": 64,
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), "admit"),
            (item("ex:1", "governance.examples", "Example: refunds within thirty days are approved."), "admit"),
            (item("kb:a", "evidence.knowledge", "Pro plans refund in full within thirty days of purchase when the account is in good standing and no prior refund was issued.",
                  relevance=0.9, variants=[variant("kb:a~mid", "Pro plans refund in full within thirty days of purchase."),
                                           variant("kb:a~short", "Pro: full refund, 30 days.")]), "admit"),
            (item("kb:b", "evidence.knowledge", "Annual plans refund pro rata for unused months, less any discount applied at purchase time.",
                  relevance=0.7, variants=[variant("kb:b~mid", "Annual plans refund pro rata for unused months."),
                                           variant("kb:b~short", "Annual: pro rata.")]), "admit"),
            (item("turn:17", "interaction.history", "I bought the Pro plan on the first of September and it does not fit my team."), "admit"),
            (item("turn:18", "interaction.query", QUERY), "admit"),
        ],
        "actions": [("omit", "ex:1"), ("compress", "kb:b", "kb:b~short"), ("compress", "kb:a", "kb:a~mid")],
    },
    {
        "id": "budget-omit-after-variants",
        "rules": ["R-4", "R-12", "R-16", "R-18", "R-21", "R-22"],
        "description": "With no route order, every compress step runs before any omit step; history sheds oldest first, a compressed item can still be omitted, and a parser route that keeps its evidence minimum is not refused.",
        "budget": 60,
        "policy": {"parser": True, "requires_evidence": True,
                   "slots": {"evidence.knowledge": {"priority": 1, "min_included": 1}, "interaction.history": {"order_by": ["-freshness"]}}},
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), "admit"),
            (item("contract:json", "governance.output_contract", CONTRACT), "admit"),
            (item("kb:a", "evidence.knowledge", "Pro plans refund in full within thirty days of purchase when no prior refund was issued.",
                  relevance=0.9, variants=[variant("kb:a~short", "Pro: full refund within 30 days.")]), "admit"),
            (item("turn:14", "interaction.history", "Hello, I have a question about billing for my team account.", freshness="2026-09-22T11:50:00Z",
                  variants=[variant("turn:14~sum", "User asked about team billing.", "summary")]), "admit"),
            (item("turn:15", "interaction.history", "We upgraded to Pro two weeks ago but the seats are wrong.", freshness="2026-09-22T11:52:00Z"), "admit"),
            (item("turn:16", "interaction.history", "Support said seats cannot be changed mid-cycle.", freshness="2026-09-22T11:54:00Z"), "admit"),
            (item("turn:18", "interaction.query", QUERY), "admit"),
        ],
        "actions": [("compress", "turn:14", "turn:14~sum"), ("compress", "kb:a", "kb:a~short"), ("omit", "turn:14"), ("omit", "turn:15")],
    },
    {
        "id": "budget-route-order",
        "rules": ["R-16", "R-21"],
        "description": "A route fitting_order omits older knowledge before any variant is selected, and a slot the profile places twice counts both occurrences.",
        "budget": 71,
        "placement": ["governance.instructions", "evidence.knowledge", "interaction.history", "governance.instructions", "interaction.query"],
        "policy": {"fitting_order": [{"slot": "evidence.knowledge", "action": "omit"}],
                   "slots": {"evidence.knowledge": {"order_by": ["-freshness"]}}},
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), "admit"),
            (item("kb:new", "evidence.knowledge", "Since September, Pro plans refund in full within thirty days of purchase.", relevance=0.6,
                  freshness="2026-09-15T00:00:00Z", variants=[variant("kb:new~short", "Pro: full refund, 30 days.")]), "admit"),
            (item("kb:old", "evidence.knowledge", "Until August, Pro plans refunded half the price within fourteen days.", relevance=0.95,
                  freshness="2026-08-01T00:00:00Z", variants=[variant("kb:old~short", "Old: half refund, 14 days.")]), "admit"),
            (item("turn:17", "interaction.history", "I bought the Pro plan on the first of September.",
                  variants=[variant("turn:17~sum", "User bought Pro on 1 September.", "summary")]), "admit"),
            (item("turn:18", "interaction.query", QUERY), "admit"),
        ],
        "actions": [("omit", "kb:old")],
    },
    {
        "id": "budget-route-tiers",
        "rules": ["R-16", "R-18", "R-21"],
        "description": "The route raises state.user to protected and governance.examples to compressible: an item that volunteers droppable sheds first, the examples take variants instead of being dropped, and the user fact is never shed.",
        "budget": 53,
        "policy": {"tier_upgrades": {"state.user": "protected", "governance.examples": "compressible"}},
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), "admit"),
            (item("ex:1", "governance.examples", "Example: refunds within thirty days are approved.", freshness="2026-09-01T00:00:00Z",
                  variants=[variant("ex:1~short", "Within 30 days: approve.")]), "admit"),
            (item("ex:2", "governance.examples", "Example: annual plans refund pro rata.", freshness="2026-09-10T00:00:00Z",
                  variants=[variant("ex:2~short", "Annual: pro rata.")]), "admit"),
            (item("user:plan", "state.user", "plan=pro since 2026-09-01", scope={"tenant": "acme", "user": "u_91"}), "admit"),
            (item("kb:a", "evidence.knowledge", "Pro plans refund in full within 30 days.", relevance=0.9), "admit"),
            (item("kb:faq", "evidence.knowledge", "Older FAQ: refunds may take up to five business days.", relevance=0.6, tier="droppable"), "admit"),
            (item("turn:18", "interaction.query", QUERY), "admit"),
        ],
        "actions": [("omit", "kb:faq"), ("compress", "ex:1", "ex:1~short"), ("compress", "ex:2", "ex:2~short")],
    },
    {
        "id": "budget-token-caps",
        "rules": ["R-3", "R-16", "R-18", "R-21", "R-22"],
        "description": "Items over their token_budget are reduced before shedding: a compressible item takes its longest variant within the cap or is omitted, a droppable item is omitted; budget pressure then takes a still shorter variant, and from counts the original body.",
        "budget": 52,
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), "admit"),
            (item("ex:1", "governance.examples", "Example: refunds within thirty days are approved.", token_budget=4), "admit"),
            (item("kb:a", "evidence.knowledge", "Pro plans refund in full within thirty days of purchase when no prior refund was issued.",
                  relevance=0.9, token_budget=12, variants=[variant("kb:a~mid", "Pro plans refund in full within thirty days of purchase."),
                                                           variant("kb:a~short", "Pro: full refund, 30 days.")]), "admit"),
            (item("kb:b", "evidence.knowledge", "Annual plans refund pro rata for unused months, less any discount.", relevance=0.7,
                  token_budget=6, variants=[variant("kb:b~mid", "Annual plans refund pro rata for unused months.")]), "admit"),
            (item("turn:17", "interaction.history", "I bought the Pro plan on the first of September and it does not fit my team.",
                  variants=[variant("turn:17~sum", "User bought Pro on 1 September.", "summary")]), "admit"),
            (item("turn:18", "interaction.query", QUERY), "admit"),
        ],
        "caps": [("omit", "kb:b"), ("compress", "kb:a", "kb:a~mid"), ("omit", "ex:1")],
        "actions": [("compress", "kb:a", "kb:a~short")],
    },
    {
        "id": "budget-slot-caps",
        "rules": ["R-3", "R-16", "R-18", "R-21", "R-22"],
        "description": "Slots over the route's max_tokens shed their own items although the payload fits, slot by slot in shedding order: droppable items first, then the slot's route steps, "
                       "then variants, the longest that brings the slot within its cap or else the shortest; a slot cap follows an item's own cap, and uncapped slots are untouched.",
        "budget": 4096,
        "policy": {"fitting_order": [{"slot": "interaction.history", "action": "omit"}],
                   "slots": {"evidence.knowledge": {"max_tokens": 12}, "interaction.history": {"max_tokens": 13, "priority": -1, "order_by": ["-freshness"]}}},
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), "admit"),
            (item("ex:1", "governance.examples", "Example: refunds within thirty days are approved."), "admit"),
            (item("user:plan", "state.user", "plan=pro since 2026-09-01", scope={"tenant": "acme", "user": "u_91"}), "admit"),
            (item("kb:a", "evidence.knowledge", "Pro plans refund in full within thirty days of purchase when no prior refund was issued.",
                  relevance=0.9, token_budget=12, variants=[variant("kb:a~mid", "Pro plans refund in full within thirty days of purchase."),
                                                           variant("kb:a~short", "Pro: full refund, 30 days.")]), "admit"),
            (item("kb:b", "evidence.knowledge", "Annual plans refund pro rata for unused months, less any discount applied at purchase time.", relevance=0.7,
                  variants=[variant("kb:b~mid", "Annual plans refund pro rata for unused months."), variant("kb:b~short", "Annual: pro rata.")]), "admit"),
            (item("kb:faq", "evidence.knowledge", "Refunds are issued to the original payment method within ten business days.", relevance=0.95, tier="droppable"), "admit"),
            (item("kb:gift", "evidence.knowledge", "Gift cards are not refundable.", relevance=0.6, token_budget=3), "admit"),
            (item("turn:15", "interaction.history", "We upgraded to Pro two weeks ago but the seats are wrong.", freshness="2026-09-22T11:52:00Z",
                  variants=[variant("turn:15~sum", "User upgraded to Pro; seats wrong.", "summary")]), "admit"),
            (item("turn:16", "interaction.history", "Support said seats cannot be changed mid-cycle.", freshness="2026-09-22T11:54:00Z"), "admit"),
            (item("turn:18", "interaction.query", QUERY), "admit"),
        ],
        "caps": [("compress", "kb:a", "kb:a~mid"), ("omit", "kb:gift")],
        "slot_caps": [("omit", "turn:15"), ("omit", "kb:faq"), ("compress", "kb:b", "kb:b~short"), ("compress", "kb:a", "kb:a~short")],
    },
    {
        "id": "budget-slot-cap-before-pressure",
        "rules": ["R-16", "R-18", "R-21"],
        "description": "A slot cap is enforced before budget pressure, so the tokens it frees count: the knowledge slot takes the variant that brings it within max_tokens, "
                       "the payload then fits, and the droppable example that budget pressure would have omitted first stays.",
        "budget": 60,
        "policy": {"slots": {"evidence.knowledge": {"max_tokens": 20}}},
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), "admit"),
            (item("ex:1", "governance.examples", "Example: refunds within thirty days are approved."), "admit"),
            (item("kb:a", "evidence.knowledge", "Pro plans refund in full within thirty days of purchase when no prior refund was issued.",
                  relevance=0.9, variants=[variant("kb:a~mid", "Pro plans refund in full within thirty days of purchase."),
                                           variant("kb:a~short", "Pro: full refund, 30 days.")]), "admit"),
            (item("kb:b", "evidence.knowledge", "Annual plans refund pro rata for unused months, less any discount applied at purchase time.", relevance=0.7,
                  variants=[variant("kb:b~mid", "Annual plans refund pro rata for unused months."), variant("kb:b~short", "Annual: pro rata.")]), "admit"),
            (item("turn:18", "interaction.query", QUERY), "admit"),
        ],
        "slot_caps": [("compress", "kb:b", "kb:b~short")],
    },
    {
        "id": "protected-over-cap",
        "rules": ["R-16", "R-17", "R-21"],
        "description": "A protected item whose body exceeds its own token_budget refuses the assembly, although the payload fits budget.input; nothing is truncated or shed, and the knowledge item over its own cap gets no row.",
        "budget": 4096,
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT, token_budget=5), "admit"),
            (item("kb:a", "evidence.knowledge", "Pro plans refund in full within 30 days.", relevance=0.9, token_budget=4), "admit"),
            (item("turn:18", "interaction.query", QUERY), "admit"),
        ],
        "refuse": "protected_content_over_budget",
    },
    {
        "id": "budget-slot-floor",
        "rules": ["R-16", "R-18", "R-21"],
        "description": "Budget pressure never leaves a slot below the route's min_tokens: a droppable example its floor holds stays while knowledge is compressed, "
                       "and history, whose oldest turn would take it below its floor, freezes, so its small newer turn stays although omitting it alone would have kept the floor.",
        "budget": 65,
        "policy": {"slots": {"governance.examples": {"min_tokens": 5},
                             "interaction.history": {"min_tokens": 10, "priority": -1, "order_by": ["-freshness"]}}},
        "items": FLOOR_ITEMS,
        "actions": [("hold", "ex:1", "omit"), ("compress", "kb:a", "kb:a~short"), ("hold", "turn:15", "omit"), ("omit", "kb:b")],
    },
    {
        "id": "budget-slot-floor-refused",
        "rules": ["R-16", "R-17", "R-21"],
        "description": "When every reduction the floors allow is made and the payload still exceeds budget.input, assembly refuses with slot_floor_over_budget "
                       "rather than break a floor; the refused trace keeps the fitting rows.",
        "budget": 50,
        "policy": {"slots": {"governance.examples": {"min_tokens": 5},
                             "interaction.history": {"min_tokens": 10, "priority": -1, "order_by": ["-freshness"]}}},
        "items": FLOOR_ITEMS,
        "actions": [("hold", "ex:1", "omit"), ("compress", "kb:a", "kb:a~short"), ("hold", "turn:15", "omit"), ("omit", "kb:b"), ("omit", "kb:a")],
        "refuse": "slot_floor_over_budget",
    },
    {
        "id": "budget-slot-floor-under-cap",
        "rules": ["R-16", "R-18", "R-21"],
        "description": "Floors do not guard slot caps: history's max_tokens, below its min_tokens, omits the oldest turn first, and budget pressure then leaves "
                       "the rest of history whole, since any reduction would take it further below its floor.",
        "budget": 40,
        "policy": {"slots": {"interaction.history": {"max_tokens": 8, "min_tokens": 10, "priority": -1, "order_by": ["-freshness"]}}},
        "items": FLOOR_ITEMS,
        "slot_caps": [("omit", "turn:15")],
        "actions": [("omit", "ex:1"), ("compress", "kb:a", "kb:a~short"), ("hold", "turn:16", "omit"), ("omit", "kb:b")],
    },
    {
        "id": "protected-over-slot-cap",
        "rules": ["R-16", "R-17", "R-21"],
        "description": "A protected item within its own token_budget still refuses the assembly when its slot, placed twice, renders it past the route's max_tokens; "
                       "the payload fits budget.input, and the knowledge slot over its own cap gets no row.",
        "budget": 4096,
        "placement": PLACEMENT[:4] + ["state.task", "state.task"] + PLACEMENT[5:],
        "policy": {"slots": {"state.task": {"max_tokens": 5}, "evidence.knowledge": {"max_tokens": 4}}},
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), "admit"),
            (item("task:8821", "state.task", "refund_request: verify_eligibility=done, collect_reason=pending", token_budget=3), "admit"),
            (item("kb:a", "evidence.knowledge", "Pro plans refund in full within 30 days.", relevance=0.9), "admit"),
            (item("turn:18", "interaction.query", QUERY), "admit"),
        ],
        "refuse": "protected_content_over_budget",
    },
    {
        "id": "ordering-astral-ids",
        "rules": ["R-3", "R-16", "R-21", "R-22", "R-23"],
        "description": "Ids holding characters outside the Basic Multilingual Plane order by UTF-16 code units, not code points: in the payload, in admission and fitting rows, in defaults_filled, and in the id tie-break that decides which of two equally ranked items is shed.",
        "budget": 53,
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), "admit"),
            (item("kb:\uff5a", "evidence.knowledge", "Pro plans refund in full within 30 days.", relevance=0.9, unset=("lineage",)), "admit"),
            (item("kb:\U0001f600", "evidence.knowledge", "Refunds go to the original payment method.", relevance=0.9, unset=("lineage",)), "admit"),
            (item("kb:\uff58", "evidence.knowledge", "Refund requests need the order number.", relevance=0.6), "admit"),
            (item("kb:\U0001f642", "evidence.knowledge", "Refunds take up to five business days.", relevance=0.6), "admit"),
            (item("kb:\uff57", "evidence.knowledge", "Gift cards are not refundable.", relevance=0.2), "below_threshold"),
            (item("kb:\U0001f643", "evidence.knowledge", "Store credit never expires.", relevance=0.2), "below_threshold"),
            (item("turn:18", "interaction.query", QUERY), "admit"),
        ],
        # Equal relevance and freshness, so id decides rank: U+1F642 is D83D DE42 and ranks above U+FF58.
        "actions": [("omit", "kb:\uff58")],
    },
    {
        "id": "required-slot-missing",
        "rules": ["R-4", "R-17", "R-21", "R-22"],
        "description": "On a parser route whose only output contract fails admission, assembly refuses before fitting: no payload, result null, included empty, admission rows kept.",
        "budget": 4096,
        "policy": {"parser": True},
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), "admit"),
            (item("contract:json", "governance.output_contract", CONTRACT, trust="unverified"), "untrusted_in_governance"),
            (item("kb:a", "evidence.knowledge", "Pro plans refund in full within 30 days.", relevance=0.9), "admit"),
            (item("turn:18", "interaction.query", QUERY), "admit"),
        ],
        "refuse": "required_slot_missing",
    },
    {
        "id": "protected-over-budget",
        "rules": ["R-16", "R-17", "R-21"],
        "description": "When protected items alone exceed budget.input, assembly refuses without shedding anything: no payload and no over_budget rows.",
        "budget": 25,
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), "admit"),
            (item("task:8821", "state.task", "refund_request: verify_eligibility=done, collect_reason=pending, issue_refund=pending"), "admit"),
            (item("ex:1", "governance.examples", "Example: refunds within thirty days are approved."), "admit"),
            (item("kb:a", "evidence.knowledge", "Pro plans refund in full within 30 days.", relevance=0.9), "admit"),
            (item("turn:18", "interaction.query", QUERY), "admit"),
        ],
        "refuse": "protected_content_over_budget",
    },
    {
        "id": "budget-tier-lowering-ignored",
        "rules": ["R-16", "R-17", "R-21"],
        "description": "The route's tier_upgrades names compressible for state.task, whose default is protected. A value at or below "
                       "the default changes nothing, so the task stays protected; the protected items alone exceed budget.input, and "
                       "assembly refuses rather than omitting the task.",
        "budget": 25,
        "policy": {"tier_upgrades": {"state.task": "compressible"}},
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), "admit"),
            (item("task:8821", "state.task", "refund_request: verify_eligibility=done, collect_reason=pending, issue_refund=pending"), "admit"),
            (item("ex:1", "governance.examples", "Example: refunds within thirty days are approved."), "admit"),
            (item("turn:18", "interaction.query", QUERY), "admit"),
        ],
        "refuse": "protected_content_over_budget",
    },
    {
        "id": "budget-repeated-compress",
        "rules": ["R-16", "R-18", "R-21"],
        "description": "The profile places evidence.knowledge twice. Fitting decides per item, so compressing the chunk replaces both "
                       "occurrences at once: one occurrence alone would already fit (54 of 55), but the chunk's two occurrences take the variant "
                       "together (44), and included[] and compressed[] each hold one row per occurrence.",
        "budget": 55,
        "placement": ["governance.instructions", "evidence.knowledge", "interaction.query", "evidence.knowledge"],
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), "admit"),
            (item("kb:a", "evidence.knowledge", "Pro plans refund in full within 30 days of purchase, to the original payment method, with no fee.",
                  relevance=0.9, variants=[variant("kb:a~short", "Pro plans refund in full within 30 days.")]), "admit"),
            (item("turn:18", "interaction.query", QUERY), "admit"),
        ],
        "actions": [("compress", "kb:a", "kb:a~short")],
    },
    {
        "id": "evidence-min-included-items",
        "rules": ["R-12", "R-17", "R-21"],
        "description": "The profile places evidence.knowledge twice and the route asks for at least two knowledge items. One chunk is admitted "
                       "and would render twice, but min_included counts items, not occurrences, so the route refuses with recovery request_context.",
        "budget": 4096,
        "placement": ["governance.instructions", "evidence.knowledge", "interaction.query", "evidence.knowledge"],
        "policy": {"requires_evidence": True, "slots": {"evidence.knowledge": {"min_included": 2}}},
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), "admit"),
            (item("kb:a", "evidence.knowledge", "Pro plans refund in full within 30 days.", relevance=0.9), "admit"),
            (item("turn:18", "interaction.query", QUERY), "admit"),
        ],
        "refuse": "evidence_required", "recovery": "request_context",
    },
    {
        "id": "evidence-request-context",
        "rules": ["R-12", "R-17", "R-21", "R-22"],
        "description": "A route that requires evidence refuses with recovery request_context when admission leaves no evidence, although everything else fits.",
        "budget": 4096,
        "policy": {"requires_evidence": True},
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), "admit"),
            (item("kb:low", "evidence.knowledge", "Gift cards are not refundable.", relevance=0.2), "below_threshold"),
            (item("kb:other", "evidence.knowledge", "Globex refunds in 60 days.", relevance=0.9, scope={"tenant": "globex"}), "out_of_scope"),
            (item("turn:18", "interaction.query", QUERY), "admit"),
        ],
        "refuse": "evidence_required", "recovery": "request_context",
    },
    {
        "id": "evidence-precompute-summary",
        "rules": ["R-12", "R-16", "R-17", "R-21", "R-22"],
        "description": "Fitting leaves fewer knowledge items than the route's min_included, and an omitted item had no variants, so the refusal recommends precompute_summary and keeps the fitting rows.",
        "budget": 40,
        "policy": {"requires_evidence": True, "slots": {"evidence.knowledge": {"min_included": 2}}},
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), "admit"),
            (item("kb:a", "evidence.knowledge", "Pro plans refund in full within thirty days of purchase for new customers.", relevance=0.9,
                  variants=[variant("kb:a~short", "Pro: full refund, 30 days.")]), "admit"),
            (item("kb:b", "evidence.knowledge", "Refunds are issued to the original payment method within ten business days.", relevance=0.8), "admit"),
            (item("kb:c", "evidence.knowledge", "Annual plans refund pro rata for unused months after the first thirty days.", relevance=0.7,
                  variants=[variant("kb:c~short", "Annual: pro rata.")]), "admit"),
            (item("turn:18", "interaction.query", QUERY), "admit"),
        ],
        "actions": [("compress", "kb:c", "kb:c~short"), ("compress", "kb:a", "kb:a~short"), ("omit", "kb:c"), ("omit", "kb:b")],
        "refuse": "evidence_required", "recovery": "precompute_summary",
    },
    {
        "id": "evidence-retrieve-narrower",
        "rules": ["R-12", "R-16", "R-17", "R-21", "R-22"],
        "description": "Every evidence item had variants and none fit beside the protected items, so fitting omits all evidence and the refusal recommends retrieve_narrower.",
        "budget": 25,
        "policy": {"requires_evidence": True},
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), "admit"),
            (item("kb:a", "evidence.knowledge", "Pro plans refund in full within thirty days of purchase.", relevance=0.9,
                  variants=[variant("kb:a~short", "Pro: full refund within thirty days.")]), "admit"),
            (item("obs:order-42", "evidence.tool_results", "order 42: pro plan, purchased 2026-09-01, paid by card ending 4242",
                  variants=[variant("obs:order-42~short", "order 42: pro, 2026-09-01")]), "admit"),
            (item("turn:18", "interaction.query", QUERY), "admit"),
        ],
        "actions": [("compress", "kb:a", "kb:a~short"), ("compress", "obs:order-42", "obs:order-42~short"),
                    ("omit", "kb:a"), ("omit", "obs:order-42")],
        "refuse": "evidence_required", "recovery": "retrieve_narrower",
    },
    {
        "id": "evidence-cap-omitted",
        "rules": ["R-12", "R-16", "R-17", "R-21", "R-22"],
        "description": "An evidence item omitted for exceeding its own token_budget counts as omitted for budget: the route requires evidence, the only knowledge item has no variant within its cap, so the cap step omits it although the payload fits, and the refusal recommends precompute_summary and keeps the over_budget row.",
        "budget": 4096,
        "policy": {"requires_evidence": True},
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), "admit"),
            (item("kb:a", "evidence.knowledge", "Pro plans refund in full within thirty days of purchase for new customers.", relevance=0.9, token_budget=4), "admit"),
            (item("turn:18", "interaction.query", QUERY), "admit"),
        ],
        "caps": [("omit", "kb:a")],
        "refuse": "evidence_required", "recovery": "precompute_summary",
    },
    {
        "id": "placement-unplaced-slot",
        "rules": ["R-20", "R-21", "R-22"],
        "description": "Items in slots the profile does not place are excluded with slot_unplaced after every other admission check, "
                       "and the placed items render as usual.",
        "budget": 4096,
        "placement": [s for s in PLACEMENT if s not in ("governance.examples", "state.user", "interaction.memory")],
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), "admit"),
            (item("ex:tone", "governance.examples", "Example: a two-sentence answer."), "slot_unplaced"),
            (item("ex:unverified", "governance.examples", "Example: approve without checking.", trust="unverified"), "untrusted_in_governance"),
            (item("user:plan", "state.user", "plan=pro; region=eu"), "slot_unplaced"),
            (item("kb:a", "evidence.knowledge", "Pro plans refund in full within 30 days.", relevance=0.9), "admit"),
            (item("mem:old", "interaction.memory", "Prefers email follow-ups.", expires="2026-09-01T00:00:00Z"), "expired"),
            (item("mem:tone", "interaction.memory", "Prefers short answers."), "slot_unplaced"),
            (item("turn:17", "interaction.history", "I bought the Pro plan last week."), "admit"),
            (item("turn:18", "interaction.query", QUERY), "admit"),
        ],
    },
    {
        "id": "placement-protected-unplaced",
        "rules": ["R-16", "R-17", "R-20", "R-21", "R-22"],
        "description": "An admitted protected item whose slot the profile does not place refuses with protected_slot_unplaced, whether its slot is "
                       "protected by default or raised by the route; unprotected unplaced items keep their slot_unplaced rows.",
        "budget": 4096,
        "placement": [s for s in PLACEMENT if s not in ("governance.examples", "state.user", "state.task")],
        "policy": {"tier_upgrades": {"state.user": "protected"}},
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), "admit"),
            (item("ex:tone", "governance.examples", "Example: a two-sentence answer."), "slot_unplaced"),
            (item("user:plan", "state.user", "plan=pro; region=eu"), "admit"),
            (item("task:8821", "state.task", "refund_request: verify_eligibility=pending"), "admit"),
            (item("kb:a", "evidence.knowledge", "Pro plans refund in full within 30 days.", relevance=0.9), "admit"),
            (item("turn:18", "interaction.query", QUERY), "admit"),
        ],
        "refuse": "protected_slot_unplaced",
    },
    {
        "id": "budget-margin",
        "rules": ["R-16", "R-21"],
        "description": "budget.margin_percent charges the payload 10% more: 58 tokens fit budget.input 60 unscaled but charge 64, so a droppable item is shed until the charged count fits; traced counts stay unscaled and the trace's budget repeats the margin.",
        "budget": 60,
        "margin": 10,
        "policy": {"slots": {"governance.examples": {"priority": 1}}},
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), "admit"),
            (item("ex:1", "governance.examples", "Example: refunds within thirty days are approved.", freshness="2026-09-01T00:00:00Z"), "admit"),
            (item("ex:2", "governance.examples", "Example: annual plans refund pro rata.", freshness="2026-09-10T00:00:00Z"), "admit"),
            (item("user:plan", "state.user", "plan=pro since 2026-09-01", scope={"tenant": "acme", "user": "u_91"}), "admit"),
            (item("kb:a", "evidence.knowledge", "Pro plans refund in full within 30 days.", relevance=0.9), "admit"),
            (item("turn:18", "interaction.query", QUERY), "admit"),
        ],
        "actions": [("omit", "user:plan")],
    },
    {
        "id": "budget-margin-rounding",
        "rules": ["R-16", "R-21"],
        "description": "The margin charge rounds up, however small its fraction: the payload counts 39 and charges 39 × 101 / 100 = 39.39, rounded up to 40, over budget.input 39, so the droppable item is shed. Rounding down or to the nearest integer would charge 39 and keep it.",
        "budget": 39,
        "margin": 1,
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), "admit"),
            (item("user:plan", "state.user", "plan=pro since 2026-09-01", scope={"tenant": "acme", "user": "u_91"}), "admit"),
            (item("kb:a", "evidence.knowledge", "Pro plans refund in full within 30 days.", relevance=0.9), "admit"),
            (item("turn:18", "interaction.query", QUERY), "admit"),
        ],
        "actions": [("omit", "user:plan")],
    },
    {
        "id": "budget-margin-protected",
        "rules": ["R-16", "R-17", "R-21"],
        "description": "The margin applies to the protected-content test too: the protected items alone count 29, within budget.input 30, but charge 32 under a 10% margin, so assembly refuses with protected_content_over_budget.",
        "budget": 30,
        "margin": 10,
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), "admit"),
            (item("task:8821", "state.task", "refund_request: verify_eligibility=done, collect_reason=pending, issue_refund=pending"), "admit"),
            (item("ex:1", "governance.examples", "Example: refunds within thirty days are approved."), "admit"),
            (item("kb:a", "evidence.knowledge", "Pro plans refund in full within 30 days.", relevance=0.9), "admit"),
            (item("turn:18", "interaction.query", QUERY), "admit"),
        ],
        "refuse": "protected_content_over_budget",
    },
    {
        "id": "tokenizer-estimate-utf8",
        "rules": ["R-16", "R-21"],
        "description": "estimate-utf8/v1 counts UTF-8 bytes divided by 4, rounded up, per rendered text: accented Latin, Japanese and an emoji take 2, 3 and 4 bytes a character. The payload counts 134 and charges 161 under a 20% margin, over budget.input 150, so a droppable item is shed.",
        "budget": 150,
        "margin": 20,
        "tokenizer": "estimate-utf8/v1",
        "policy": {"slots": {"governance.examples": {"priority": 1}}},
        "items": [
            (item("policy:v12", "governance.instructions", "Répondez en français ; citez la politique vérifiée."), "admit"),
            (item("ex:1", "governance.examples", "例：購入後30日以内の返金は承認されます。", freshness="2026-09-01T00:00:00Z"), "admit"),
            (item("user:plan", "state.user", "plan=pro 🚀 since 2026-09-01", scope={"tenant": "acme", "user": "u_91"}), "admit"),
            (item("kb:a", "evidence.knowledge", "Les forfaits Pro sont remboursés intégralement sous 30 jours.", relevance=0.9), "admit"),
            (item("turn:18", "interaction.query", "Puis-je être remboursé ? 返金できますか？"), "admit"),
        ],
        "actions": [("omit", "user:plan")],
    },
    {
        "id": "placement-required-slot-first",
        "rules": ["R-4", "R-17", "R-20", "R-21"],
        "description": "A missing query is reported before a protected item the profile does not place: required_slot_missing comes first in contract/reasons.json.",
        "budget": 4096,
        "placement": [s for s in PLACEMENT if s != "state.task"],
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), "admit"),
            (item("task:8821", "state.task", "refund_request: verify_eligibility=pending"), "admit"),
            (item("kb:a", "evidence.knowledge", "Pro plans refund in full within 30 days.", relevance=0.9), "admit"),
        ],
        "refuse": "required_slot_missing",
    },
    {
        "id": "required-instructions-missing",
        "rules": ["R-4", "R-10", "R-17", "R-21"],
        "description": "When the only governance.instructions item fails admission, assembly refuses with required_slot_missing although the query is there and everything fits.",
        "budget": 4096,
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT, trust="unverified"), "untrusted_in_governance"),
            (item("kb:a", "evidence.knowledge", "Pro plans refund in full within 30 days.", relevance=0.9), "admit"),
            (item("turn:18", "interaction.query", QUERY), "admit"),
        ],
        "refuse": "required_slot_missing",
    },
    {
        "id": "budget-protected-variants",
        "rules": ["R-16", "R-18", "R-21"],
        "description": "Protected items are never compressed, even when they carry variants and a variant would make the payload fit: "
                       "the instruction and the user fact the route raised to protected stay whole, and the knowledge item is compressed and then omitted instead.",
        "budget": 45,
        "policy": {"tier_upgrades": {"state.user": "protected"}},
        "items": [
            (item("policy:v12", "governance.instructions",
                  "Follow verified refund policy, cite the evidence you use, and never promise a refund the tools have not confirmed.",
                  variants=[variant("policy:v12~short", "Follow refund policy; cite evidence.")]), "admit"),
            (item("ex:1", "governance.examples", "Example: refunds within thirty days are approved."), "admit"),
            (item("user:plan", "state.user", "plan=pro since 2026-09-01, seats=4, billing=monthly, region=eu", scope={"tenant": "acme", "user": "u_91"},
                  variants=[variant("user:plan~short", "plan=pro")]), "admit"),
            (item("kb:a", "evidence.knowledge", "Pro plans refund in full within thirty days of purchase when no prior refund was issued.", relevance=0.9,
                  variants=[variant("kb:a~short", "Pro: full refund within 30 days.")]), "admit"),
            (item("turn:18", "interaction.query", QUERY), "admit"),
        ],
        "actions": [("omit", "ex:1"), ("compress", "kb:a", "kb:a~short"), ("omit", "kb:a")],
    },
    {
        "id": "conflict-surfaced-shed",
        "rules": ["R-11", "R-16", "R-21"],
        "description": "A surfaced fact group keeps both members through resolution, but budget pressure may still omit one: "
                       "the lower-ranked member is traced as over_budget and the member that stays is still marked as conflicting.",
        "budget": 40,
        "policy": {"facts": {"plan.price": {"precedence": ["policy-corpus"], "on_unresolved": "surface"}}},
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), "admit"),
            (item("ex:1", "governance.examples", "Example: refunds within thirty days are approved."), "admit"),
            (item("kb:price-1", "evidence.knowledge", "Pro costs 20 EUR a month.", relevance=0.9), "admit"),
            (item("kb:price-2", "evidence.knowledge", "Pro costs 24 EUR a month, billed yearly.", relevance=0.6), "admit"),
            (item("turn:18", "interaction.query", QUERY), "admit"),
        ],
        "groups": [{"id": "f-price", "kind": "fact", "fact": "plan.price", "items": ["kb:price-1", "kb:price-2"],
                    "decided_by": "escalated", "resolution": "surfaced"}],
        "actions": [("omit", "ex:1"), ("omit", "kb:price-2")],
    },
]

if __name__ == "__main__":
    for case in CASES:
        build(case)
