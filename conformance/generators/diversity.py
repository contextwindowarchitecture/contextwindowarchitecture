"""Builds the source diversity conformance cases (R-26) from tables of intended outcomes.

Each case lists its candidates, the conflict groups it declares, and "capped": the items it intends the
source diversity cap to exclude. conflicts.py builds the snapshot, trace and payload, and checks the
table against conformance/README.md's Source diversity section.
"""
import os, sys
sys.dont_write_bytecode = True  # importing conflicts must not leave a __pycache__ for implementations to vendor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conflicts import CONV, CORPUS, CRM, QUERY, POLICY_TEXT, REG, STATE, WIKI, build, kb  # noqa: E402
from fitting import item  # noqa: E402

KNOWLEDGE = {"min_relevance": 0.5, "required_scope": ["tenant"]}
USER = {"scope": {"tenant": "acme", "user": "u_91"}}


def obs(id, source, freshness, body):
    return item(id, "evidence.tool_results", body, source=source, freshness=freshness)


CASES = [
    {
        "id": "diversity-cap",
        "rules": ["R-13", "R-15", "R-21", "R-22", "R-24", "R-26"],
        "description": "A slot capped at two items per producer and source keeps each document's two highest-ranked chunks, after deduplication so a "
                       "duplicate never takes a place; another producer's chunks from the same source are counted apart, a one-chunk document is "
                       "untouched, and an uncapped slot keeps every item.",
        "policy": {"slots": {"evidence.knowledge": {**KNOWLEDGE, "max_per_source": 2, "dedupe": "exact"}}},
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), REG, "admit"),
            (kb("kb:a1", "Pro plans refund in full within 30 days.", source="doc:refunds", relevance=0.9), CORPUS, "admit"),
            (kb("kb:a1-copy", "Pro plans refund in full within 30 days.", source="doc:refunds", relevance=0.95), CORPUS, "admit"),
            (kb("kb:a2", "Annual plans refund pro rata.", source="doc:refunds", relevance=0.85), CORPUS, "admit"),
            (kb("kb:a3", "Refunds go to the original payment method.", source="doc:refunds", relevance=0.8), CORPUS, "admit"),
            (kb("kb:a4", "Refunds take up to five business days.", source="doc:refunds", relevance=0.7), CORPUS, "admit"),
            (kb("kb:b1", "Invoices are issued monthly.", source="doc:billing", relevance=0.6), CORPUS, "admit"),
            (kb("wiki:a1", "Refund requests need the order number.", source="doc:refunds", relevance=0.9), WIKI, "admit"),
            (kb("wiki:a2", "Gift cards are not refundable.", source="doc:refunds", relevance=0.8), WIKI, "admit"),
            (obs("obs:1", "crm:order/42", "2026-09-22T11:50:00Z", "order 42: processing"), CRM, "admit"),
            (obs("obs:2", "crm:order/42", "2026-09-22T11:55:00Z", "order 42: packed"), CRM, "admit"),
            (obs("obs:3", "crm:order/42", "2026-09-22T11:58:00Z", "order 42: shipped"), CRM, "admit"),
            (item("turn:18", "interaction.query", QUERY), CONV, "admit"),
        ],
        "groups": [],
        "duplicates": {"kb:a1": "kb:a1-copy"},
        "capped": ["kb:a3", "kb:a4"],
    },
    {
        "id": "diversity-exemptions",
        "rules": ["R-6", "R-11", "R-16", "R-21", "R-24", "R-25", "R-26"],
        "description": "The cap never excludes a protected item or one a conflict group names, and those take places first: a low-ranked fact-group winner "
                       "leaves one place for its document's other chunks, and a slot raised to protected keeps every item over its cap; rows follow "
                       "the pipeline, conflicts, supersession, deduplication, then the cap.",
        "policy": {"tier_upgrades": {"state.user": "protected"},
                   "slots": {"evidence.knowledge": {**KNOWLEDGE, "max_per_source": 2, "dedupe": "exact"},
                             "evidence.tool_results": {"supersede": "source"},
                             "state.user": {"max_per_source": 1}},
                   "facts": {"refund.window": {"precedence": [CORPUS], "on_unresolved": "refuse"}}},
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), REG, "admit"),
            (item("user:plan", "state.user", "plan=pro", source="crm:user/91", **USER), STATE, "admit"),
            (item("user:region", "state.user", "region=eu", source="crm:user/91", **USER), STATE, "admit"),
            (kb("kb:w1", "Refunds are accepted within 30 days of purchase.", source="doc:policy", relevance=0.55), CORPUS, "admit"),
            (kb("wiki:w", "Refunds are accepted within 14 days of purchase.", source="doc:policy", relevance=0.9), WIKI, "admit"),
            (kb("kb:w2", "Refunds carry no processing fee.", source="doc:policy", relevance=0.9), CORPUS, "admit"),
            (kb("kb:w2-copy", "Refunds carry no processing fee.", source="doc:policy", relevance=0.7), CORPUS, "admit"),
            (kb("kb:w3", "Refunds go to the original payment method.", source="doc:policy", relevance=0.8), CORPUS, "admit"),
            (obs("obs:old", "crm:order/42", "2026-09-22T11:50:00Z", "order 42: packed"), CRM, "admit"),
            (obs("obs:new", "crm:order/42", "2026-09-22T11:58:00Z", "order 42: shipped"), CRM, "admit"),
            (item("turn:18", "interaction.query", QUERY), CONV, "admit"),
        ],
        "groups": [
            {"id": "f-window", "kind": "fact", "fact": "refund.window", "items": ["kb:w1", "wiki:w"],
             "decided_by": "policy", "resolution": "resolved", "winner": "kb:w1", "excluded": {"wiki:w": "conflict_lost"}},
        ],
        "superseded": {"obs:old": "obs:new"},
        "duplicates": {"kb:w2-copy": "kb:w2"},
        "capped": ["kb:w3"],
    },
    {
        "id": "diversity-evidence-required",
        "rules": ["R-12", "R-17", "R-21", "R-26"],
        "description": "On a route that requires two knowledge items, a cap of one per source leaves one, so assembly refuses with evidence_required and "
                       "recovery request_context, since nothing was omitted for budget; the refused trace keeps the source_diversity_cap row.",
        "policy": {"requires_evidence": True, "slots": {"evidence.knowledge": {**KNOWLEDGE, "max_per_source": 1, "min_included": 2}}},
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), REG, "admit"),
            (kb("kb:a", "Pro plans refund in full within 30 days.", source="doc:refunds", relevance=0.9), CORPUS, "admit"),
            (kb("kb:b", "Annual plans refund pro rata.", source="doc:refunds", relevance=0.8), CORPUS, "admit"),
            (item("turn:18", "interaction.query", QUERY), CONV, "admit"),
        ],
        "groups": [],
        "capped": ["kb:b"],
        "refuse": "evidence_required", "recovery": "request_context",
    },
]

# diversity-cap with its cap written 2.0: the same double as 2, which JSON Schema also counts as an integer, so the same
# decisions, the same digest (RFC 8785 writes 2) and the same payload.
CASES.append({
    **CASES[0], "id": "integer-written-as-double",
    "rules": ["R-2", "R-26"],
    "description": "Every number is a double: a slot capped at max_per_source 2.0 is capped at 2, as in diversity-cap, whose candidates and "
                   "decisions this case repeats, so each document keeps its two highest-ranked chunks.",
    "policy": {"slots": {"evidence.knowledge": {**KNOWLEDGE, "max_per_source": 2.0, "dedupe": "exact"}}},
})

if __name__ == "__main__":
    for case in CASES:
        build(case)
