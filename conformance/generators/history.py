"""Builds conformance/cases/history-freshness-order from a table of turns (R-7).

History turns render in the order they were said: by freshness, compared as instants at full precision, then by id
(conformance/README.md, Running a case). The turns' ids sort against that order, one freshness is written with an
offset, and two turns said at the same instant, spelled with fractions of different lengths, fall back to id order.
fitting.py builds the case, so its trace and payload come from the same tables as the other fitting cases.
"""
import os, sys
sys.dont_write_bytecode = True  # importing fitting must not leave a __pycache__ for implementations to vendor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fitting import POLICY_TEXT, build, item  # noqa: E402


def turn(id, body, freshness, assistant=False):
    extra = {"lineage": "generated", "authority": "untrusted"} if assistant else {}  # prior model turns (R-1)
    return item(id, "interaction.history", body, freshness=freshness, **extra)


CASE = {
    "id": "history-freshness-order",
    "rules": ["R-7"],
    "description": "History turns render in the order they were said, by freshness compared as instants at full precision, "
                   "and by id only among turns said at the same instant, whatever order their ids sort in.",
    "budget": 4096,
    "items": [
        (item("policy:v12", "governance.instructions", POLICY_TEXT), "admit"),
        (turn("turn:9", "I bought the Pro plan last week.", "2026-09-22T11:46:00Z"), "admit"),
        (turn("turn:10", "Which order should I look at?", "2026-09-22T13:47:00+02:00", assistant=True), "admit"),
        (turn("turn:12", "Order 8821.", "2026-09-22T11:48:00.25Z"), "admit"),
        (turn("turn:11", "Order 8821 is within the 30-day refund window.", "2026-09-22T11:48:00.5Z", assistant=True), "admit"),
        (turn("turn:11b", "Then please refund it.", "2026-09-22T11:48:00.500Z"), "admit"),
        (item("turn:13", "interaction.query", "How long will the refund take?"), "admit"),
    ],
}

if __name__ == "__main__":
    build(CASE)
