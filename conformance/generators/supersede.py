"""Builds the supersession conformance cases (R-25) from tables of intended outcomes.

Each case lists its candidates, the conflict groups it declares, and "superseded": each item it
intends supersession to exclude, with the latest item kept for the same producer and source.
conflicts.py builds the snapshot, trace and payload, and checks the table against
conformance/README.md's Supersession section.
"""
import os, sys
sys.dont_write_bytecode = True  # importing conflicts must not leave a __pycache__ for implementations to vendor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conflicts import CONV, CORPUS, CRM, QUERY, POLICY_TEXT, REG, STATE, build, kb  # noqa: E402
from fitting import item  # noqa: E402

KNOWLEDGE = {"min_relevance": 0.5, "required_scope": ["tenant"]}
BILLING = "billing-mcp"
USER = {"scope": {"tenant": "acme", "user": "u_91"}}


def obs(id, source, freshness, body):
    return item(id, "evidence.tool_results", body, source=source, freshness=freshness)


CASES = [
    {
        "id": "supersede-observations",
        "rules": ["R-2", "R-15", "R-21", "R-22", "R-25"],
        "description": "In a slot the route asks, only the latest observation per authenticated producer and source is kept: instants compare at full precision, "
                       "so equal instants written differently tie and all stay while a microsecond later wins; another producer's item with the same source "
                       "is untouched, and a slot without supersede keeps an older version.",
        "producers": {BILLING: ("mcp", ["evidence.tool_results"])},
        "policy": {"slots": {"evidence.knowledge": KNOWLEDGE, "evidence.tool_results": {"supersede": "source"}}},
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), REG, "admit"),
            (obs("obs:order-1", "crm:order/42", "2026-09-22T11:50:00Z", "order 42: processing"), CRM, "admit"),
            (obs("obs:order-2", "crm:order/42", "2026-09-22T11:55:00Z", "order 42: packed"), CRM, "admit"),
            (obs("obs:order-3", "crm:order/42", "2026-09-22T11:58:00Z", "order 42: shipped"), CRM, "admit"),
            (obs("obs:order-3b", "crm:order/42", "2026-09-22T11:58:00.000Z", "order 42: shipped, carrier assigned"), CRM, "admit"),
            (obs("obs:order-3c", "crm:order/42", "2026-09-22T13:58:00+02:00", "order 42: shipped from Berlin"), CRM, "admit"),
            (obs("obs:refund-a", "crm:refund/7", "2026-09-22T11:59:00Z", "refund 7: requested"), CRM, "admit"),
            (obs("obs:refund-b", "crm:refund/7", "2026-09-22T11:59:00.000001Z", "refund 7: approved"), CRM, "admit"),
            (obs("obs:customer", "crm:customer/91", "2026-09-22T11:00:00Z", "customer 91: pro plan"), CRM, "admit"),
            (obs("obs:billing-42", "crm:order/42", "2026-09-22T11:40:00Z", "order 42: paid by card"), BILLING, "admit"),
            (kb("kb:policy-v1", "Refunds are accepted within 14 days.", source="kb:refund-policy", freshness="2026-08-01T00:00:00Z"), CORPUS, "admit"),
            (kb("kb:policy-v2", "Refunds are accepted within 30 days.", source="kb:refund-policy", freshness="2026-09-01T00:00:00Z"), CORPUS, "admit"),
            (item("turn:18", "interaction.query", QUERY), CONV, "admit"),
        ],
        "groups": [],
        "superseded": {"obs:order-1": "obs:order-3", "obs:order-2": "obs:order-3", "obs:refund-a": "obs:refund-b"},
    },
    {
        "id": "supersede-exemptions",
        "rules": ["R-6", "R-11", "R-16", "R-21", "R-24", "R-25"],
        "description": "Supersession runs after conflict resolution and before deduplication, and never excludes a protected item or one a conflict group names: "
                       "a stale fact-group winner stays beside the newer observation, a slot raised to protected keeps its stale item, and a stale copy of a "
                       "newer body is recorded as superseded, not as a duplicate.",
        "policy": {"tier_upgrades": {"state.user": "protected"},
                   "slots": {"evidence.knowledge": KNOWLEDGE, "state.user": {"supersede": "source"},
                             "evidence.tool_results": {"supersede": "source", "dedupe": "exact"}},
                   "facts": {"order.status": {"precedence": [CRM], "on_unresolved": "refuse"}}},
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), REG, "admit"),
            (item("user:plan-old", "state.user", "plan=basic", source="crm:user/91", freshness="2026-09-22T11:00:00Z", **USER), STATE, "admit"),
            (item("user:plan-new", "state.user", "plan=pro", source="crm:user/91", freshness="2026-09-22T11:30:00Z", **USER), STATE, "admit"),
            (obs("obs:status-old", "crm:status/42", "2026-09-22T11:40:00Z", "order 42 status: packed"), CRM, "admit"),
            (obs("obs:status-new", "crm:status/42", "2026-09-22T11:58:00Z", "order 42 status: shipped"), CRM, "admit"),
            (kb("kb:status", "Orders ship within two days.", relevance=0.8), CORPUS, "admit"),
            (obs("obs:ship-old", "crm:ship/1", "2026-09-22T11:50:00Z", "shipment 1: in transit"), CRM, "admit"),
            (obs("obs:ship-new", "crm:ship/1", "2026-09-22T11:58:00Z", "shipment 1: in transit"), CRM, "admit"),
            (obs("obs:ship-mirror", "crm:ship-mirror/1", "2026-09-22T11:57:00Z", "shipment 1:  in transit"), CRM, "admit"),
            (item("turn:18", "interaction.query", QUERY), CONV, "admit"),
        ],
        "groups": [
            {"id": "f-status", "kind": "fact", "fact": "order.status", "items": ["kb:status", "obs:status-old"],
             "decided_by": "policy", "resolution": "resolved", "winner": "obs:status-old", "excluded": {"kb:status": "conflict_lost"}},
        ],
        "superseded": {"obs:ship-old": "obs:ship-new"},
        "duplicates": {"obs:ship-mirror": "obs:ship-new"},
    },
    {
        "id": "supersede-evidence-required",
        "rules": ["R-12", "R-17", "R-21", "R-25"],
        "description": "On a route that requires two tool results, supersession leaves one, so assembly refuses with evidence_required and recovery "
                       "request_context, since nothing was omitted for budget; the refused trace keeps the superseded row.",
        "policy": {"requires_evidence": True, "slots": {"evidence.knowledge": KNOWLEDGE,
                                                        "evidence.tool_results": {"supersede": "source", "min_included": 2}}},
        "items": [
            (item("policy:v12", "governance.instructions", POLICY_TEXT), REG, "admit"),
            (obs("obs:order-1", "crm:order/42", "2026-09-22T11:50:00Z", "order 42: packed"), CRM, "admit"),
            (obs("obs:order-2", "crm:order/42", "2026-09-22T11:58:00Z", "order 42: shipped"), CRM, "admit"),
            (item("turn:18", "interaction.query", QUERY), CONV, "admit"),
        ],
        "groups": [],
        "superseded": {"obs:order-1": "obs:order-2"},
        "refuse": "evidence_required", "recovery": "request_context",
    },
]

if __name__ == "__main__":
    for case in CASES:
        build(case)
