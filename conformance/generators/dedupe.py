"""Builds the deduplication conformance cases (R-24) from tables of intended outcomes.

Each case lists its candidates, the conflict groups it declares, and "duplicates": each item it
intends deduplication to exclude, with the item kept in its place. conflicts.py builds the snapshot,
trace and payload, and checks the table against conformance/README.md's Deduplication section.
"""
import os, sys
sys.dont_write_bytecode = True  # importing conflicts must not leave a __pycache__ for implementations to vendor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conflicts import CONV, CORPUS, CRM, QUERY, POLICY_TEXT, REG, STATE, WIKI, build, kb  # noqa: E402
from fitting import item  # noqa: E402

KNOWLEDGE = {"min_relevance": 0.5, "required_scope": ["tenant"], "dedupe": "exact"}
CHUNK = "Pro plans refund in full within 30 days."
USER = {"scope": {"tenant": "acme", "user": "u_91"}}

CASES = [
    {
        "id": "dedupe-exact",
        "rules": ["R-21", "R-22", "R-24"],
        "description": "In the slots a route asks, bodies equal once whitespace runs collapse are excluded as duplicate_content, keeping the highest-ranked copy "
                       "(relevance before id, id on a tie); normalization forms and case still differ, equal bodies in different slots are both kept, "
                       "and a slot without dedupe keeps repeated turns.",
        "policy": {"slots": {"evidence.knowledge": KNOWLEDGE, "evidence.tool_results": {"dedupe": "exact"}}},
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), REG, "admit"),
            (kb("kb:a", CHUNK, relevance=0.9), CORPUS, "admit"),
            (kb("kb:mirror", CHUNK, relevance=0.95), CORPUS, "admit"),
            (kb("kb:spaced", "\ufeff\u3000Pro plans\trefund in full\u00a0within\n30 days.  ", relevance=0.6), CORPUS, "admit"),
            (kb("kb:case", "pro plans refund in full within 30 days.", relevance=0.6), CORPUS, "admit"),
            (kb("kb:cafe-nfc", "Caf\u00e9 purchases refund to store credit.", relevance=0.7), CORPUS, "admit"),
            (kb("kb:cafe-nfd", "Cafe\u0301 purchases refund to store credit.", relevance=0.7), CORPUS, "admit"),
            (kb("kb:tie-2", "Refunds go to the original payment method.", relevance=0.8), CORPUS, "admit"),
            (kb("kb:tie-1", "Refunds go to the original payment method.", relevance=0.8), CORPUS, "admit"),
            (item("obs:old", "evidence.tool_results", CHUNK, freshness="2026-09-22T11:50:00Z"), CRM, "admit"),
            (item("obs:new", "evidence.tool_results", CHUNK, freshness="2026-09-22T11:58:00Z"), CRM, "admit"),
            (item("turn:15", "interaction.history", "Yes, please."), CONV, "admit"),
            (item("turn:17", "interaction.history", "Yes, please."), CONV, "admit"),
            (item("turn:18", "interaction.query", QUERY), CONV, "admit"),
        ],
        "groups": [],
        "duplicates": {"kb:a": "kb:mirror", "kb:spaced": "kb:mirror", "kb:tie-2": "kb:tie-1", "obs:old": "obs:new"},
    },
    {
        "id": "dedupe-producer-reported",
        "rules": ["R-13", "R-21", "R-22", "R-24"],
        "description": "A retriever that dropped a near-duplicate reports it as duplicate_content at stage producer, naming the candidate it kept, and the trace "
                       "carries that row as reported ahead of the assembler's rows; the kept candidate can still be removed later by the route's own exact dedupe.",
        "policy": {"slots": {"evidence.knowledge": KNOWLEDGE}},
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), REG, "admit"),
            (kb("kb:a", CHUNK, relevance=0.9), CORPUS, "admit"),
            (kb("wiki:refund", CHUNK, relevance=0.8), WIKI, "admit"),
            (kb("wiki:fees", "Refunds carry no processing fee.", relevance=0.7), WIKI, "admit"),
            (item("turn:18", "interaction.query", QUERY), CONV, "admit"),
        ],
        "producer_excluded": {WIKI: [{"item_id": "wiki:refund-paraphrase", "reason": "duplicate_content", "stage": "producer", "duplicate_of": "wiki:refund"}]},
        "groups": [],
        "duplicates": {"wiki:refund": "kb:a"},
    },
    {
        "id": "dedupe-exemptions",
        "rules": ["R-6", "R-11", "R-16", "R-21", "R-24"],
        "description": "Deduplication runs after conflict resolution and never excludes a protected item or one a conflict group names: a fact group's winner "
                       "stays over a higher-ranked ungrouped copy, a moot group still exempts its member, and a slot the route raised to protected keeps both copies.",
        "policy": {"tier_upgrades": {"state.user": "protected"},
                   "slots": {"evidence.knowledge": KNOWLEDGE, "state.user": {"dedupe": "exact"}},
                   "facts": {"refund.window": {"precedence": [CORPUS], "on_unresolved": "refuse"}}},
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), REG, "admit"),
            (item("user:plan", "state.user", "plan=pro since 2026-09-01", **USER), STATE, "admit"),
            (item("user:plan-sync", "state.user", "plan=pro since 2026-09-01", **USER), STATE, "admit"),
            (kb("kb:window", "Refunds are accepted within 30 days of purchase.", relevance=0.7), CORPUS, "admit"),
            (kb("wiki:window", "Refunds are accepted within 14 days of purchase.", relevance=0.9), WIKI, "admit"),
            (kb("kb:window-copy", "Refunds are accepted within 30 days of purchase.", relevance=0.99), CORPUS, "admit"),
            (kb("kb:fee", "Refunds carry no processing fee.", relevance=0.6), CORPUS, "admit"),
            (kb("kb:fee-copy", "Refunds carry no processing fee.", relevance=0.95), CORPUS, "admit"),
            (kb("kb:stale", "Refunds carry a 5% processing fee.", relevance=0.2), CORPUS, "below_threshold"),
            (item("turn:18", "interaction.query", QUERY), CONV, "admit"),
        ],
        "groups": [
            {"id": "f-window", "kind": "fact", "fact": "refund.window", "items": ["kb:window", "wiki:window"],
             "decided_by": "policy", "resolution": "resolved", "winner": "kb:window", "excluded": {"wiki:window": "conflict_lost"}},
            {"id": "g-fee", "kind": "instruction", "items": ["kb:fee", "kb:stale"], "decided_by": "moot", "resolution": "moot"},
        ],
        "duplicates": {"kb:fee-copy": "kb:fee", "kb:window-copy": "kb:window"},
    },
    {
        "id": "dedupe-evidence-required",
        "rules": ["R-12", "R-17", "R-21", "R-24"],
        "description": "On a route that requires two knowledge items, deduplication leaves one, so assembly refuses with evidence_required and recovery request_context, "
                       "since nothing was omitted for budget; the refused trace keeps the duplicate_content row.",
        "policy": {"requires_evidence": True, "slots": {"evidence.knowledge": {**KNOWLEDGE, "min_included": 2}}},
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), REG, "admit"),
            (kb("kb:a", CHUNK, relevance=0.9), CORPUS, "admit"),
            (kb("kb:b", CHUNK + "\n", relevance=0.8), CORPUS, "admit"),
            (item("turn:18", "interaction.query", QUERY), CONV, "admit"),
        ],
        "groups": [],
        "duplicates": {"kb:b": "kb:a"},
        "refuse": "evidence_required", "recovery": "request_context",
    },
]

if __name__ == "__main__":
    for case in CASES:
        build(case)
