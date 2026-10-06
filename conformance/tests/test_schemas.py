"""The published schemas and reason registry say what the specification says: each valid document passes, and each
change that breaks a rule fails, one change at a time. The website's JavaScript suite holds the same documents to the
same rules through its own validators.

    python3 -m unittest discover -s conformance/tests
"""
import copy, glob, json, math, os, re, sys, unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.dont_write_bytecode = True
from jsonschema import Draft202012Validator, FormatChecker  # noqa: E402
from referencing import Registry, Resource  # noqa: E402


def load(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f: return json.load(f)


SCHEMAS = {}
for path in glob.glob(os.path.join(ROOT, "schema", "*.json")):
    with open(path, encoding="utf-8") as f: schema = json.load(f)
    SCHEMAS[os.path.basename(path)] = schema
REGISTRY = Registry().with_resources((s["$id"], Resource.from_contents(s)) for s in SCHEMAS.values())
VALIDATORS = {name: Draft202012Validator(s, registry=REGISTRY, format_checker=FormatChecker()) for name, s in SCHEMAS.items()}
valid = lambda name, doc: VALIDATORS[name].is_valid(doc)
REASONS = load("contract/reasons.json")
TRACE = load("examples/trace.json")
SNAPSHOT = load("conformance/cases/fixture-three-slot/snapshot.json")
POLICY = SNAPSHOT["route_policy"]


class Mutations(unittest.TestCase):
    def holds(self, name, base, mutations):
        """base is valid against the schema, and each mutation, applied alone to a copy, makes it invalid."""
        self.assertTrue(valid(name, base), [e.message for e in VALIDATORS[name].iter_errors(base)][:3])
        for i, mutate in enumerate(mutations):
            candidate = copy.deepcopy(base)
            mutate(candidate)
            self.assertFalse(valid(name, candidate), f"{name}: mutation {i} still valid")


def put(path, value):
    """A mutation that sets a nested member: put(('a', 'b'), 1) sets doc['a']['b'] = 1."""
    def apply(doc):
        for key in path[:-1]: doc = doc[key]
        doc[path[-1]] = value
    return apply


def drop(path):
    def apply(doc):
        for key in path[:-1]: doc = doc[key]
        del doc[path[-1]]
    return apply


class Reasons(unittest.TestCase):
    def test_exclusions_after_admission_follow_the_pipeline_and_refusals_the_order_assembly_checks_them(self):
        exclusions = [r["code"] for r in REASONS if r["kind"] == "exclusion"]
        self.assertEqual(exclusions[-6:], ["conflict_deferred", "conflict_lost", "superseded", "duplicate_content", "source_diversity_cap", "over_budget"])
        self.assertEqual([r["code"] for r in REASONS if r["kind"] == "refusal"],
                         ["required_slot_missing", "protected_slot_unplaced", "conflict_unresolved", "protected_content_over_budget", "slot_floor_over_budget", "evidence_required"])

    def test_each_late_exclusion_belongs_to_the_requirement_that_defines_it(self):
        by_code = {r["code"]: r for r in REASONS}
        for code, rule in [("source_diversity_cap", "R-26"), ("superseded", "R-25"), ("duplicate_content", "R-24"), ("slot_floor_over_budget", "R-17")]:
            self.assertEqual(by_code[code]["rule"], rule, code)
        for code in ("source_diversity_cap", "superseded", "duplicate_content"): self.assertEqual(by_code[code]["kind"], "exclusion")


class Trace(Mutations):
    def row(self, **row):
        return {**copy.deepcopy(TRACE), "excluded": TRACE["excluded"] + [row]}

    def test_superseded_by_names_the_newest_item_and_only_a_superseded_row_carries_it(self):
        base = dict(item_id="obs:old", reason="superseded", stage="assembler", slot="evidence.tool_results", superseded_by="obs:new")
        self.assertTrue(valid("trace.schema.json", self.row(**base)))
        unnamed = {k: v for k, v in base.items() if k != "superseded_by"}
        for row in [unnamed, {**base, "reason": "duplicate_content", "duplicate_of": "obs:new"}, {**base, "duplicate_of": "obs:new"}, {**base, "superseded_by": " "}]:
            self.assertFalse(valid("trace.schema.json", self.row(**row)), row)

    def test_duplicate_of_names_the_item_kept_and_only_a_duplicate_content_row_carries_it(self):
        base = dict(item_id="kb:b", reason="duplicate_content", stage="assembler", slot="evidence.knowledge", duplicate_of="kb:a")
        self.assertTrue(valid("trace.schema.json", self.row(**base)))
        unnamed = {k: v for k, v in base.items() if k != "duplicate_of"}
        for row in [unnamed, {**base, "reason": "over_budget"}, {**base, "duplicate_of": " "}]:
            self.assertFalse(valid("trace.schema.json", self.row(**row)), row)

    def test_a_source_diversity_cap_row_names_nothing_kept(self):
        base = dict(item_id="kb:a#4", reason="source_diversity_cap", stage="assembler", slot="evidence.knowledge")
        self.assertTrue(valid("trace.schema.json", self.row(**base)))
        for extra in ({"duplicate_of": "kb:a#1"}, {"superseded_by": "kb:a#1"}):
            self.assertFalse(valid("trace.schema.json", self.row(**base, **extra)), extra)

    def test_a_budget_reserves_an_integer_margin_of_at_most_100_and_the_trace_repeats_it(self):
        for margin, ok in [(0, True), (15, True), (100, True), (-1, False), (101, False), (7.5, False), ("10", False)]:
            snapshot = copy.deepcopy(SNAPSHOT); snapshot["budget"]["margin_percent"] = margin
            trace = copy.deepcopy(TRACE); trace["budget"]["margin_percent"] = margin
            self.assertEqual(valid("snapshot.schema.json", snapshot), ok, f"snapshot {margin!r}")
            self.assertEqual(valid("trace.schema.json", trace), ok, f"trace {margin!r}")

    def test_profiles_and_traces_name_the_specification_they_follow(self):
        fixture = load("examples/fixture-profile.json")
        for spec in (None, "cwa/1", "cwa/v2", "draft"):
            profile, trace = copy.deepcopy(fixture), copy.deepcopy(TRACE)
            if spec is None: del profile["spec"]; del trace["context"]["spec"]
            else: profile["spec"] = spec; trace["context"]["spec"] = spec
            self.assertFalse(valid("profile.schema.json", profile), spec)
            self.assertFalse(valid("trace.schema.json", trace), spec)


class Snapshot(Mutations):
    def test_snapshots_bind_identity_per_batch_and_reject_undeclared_fields_but_carry_raw_items(self):
        def push(doc): doc["batches"][0]["items"].append("not an object")
        self.holds("snapshot.schema.json", SNAPSHOT, [drop(("assembly_time",)), put(("batches", 0, "producer", "kind"), "self-declared"), put(("clock",), "now"),
                                                     drop(("batches", 1, "producer")), put(("batches", 0, "producer", "verified_server"), True), push])
        raw = copy.deepcopy(SNAPSHOT)
        raw["batches"][0]["items"][0]["surprise"] = 1
        del raw["batches"][1]["items"][0]["body"]
        self.assertTrue(valid("snapshot.schema.json", raw), "an invalid item is refused at admission (R-2), not by the snapshot")


class RoutePolicy(Mutations):
    def test_fact_precedence_and_unresolved_conflict_actions(self):
        full = {**copy.deepcopy(POLICY), "on_unresolved_instruction": "surface",
                "facts": {"refund.window": {"precedence": ["policy-corpus", "crm-mcp"], "scope": ["tenant"], "freshness_tiebreak": True, "on_unresolved": "request_context"},
                          "order.status": {"precedence": ["crm-mcp"], "on_unresolved": "refuse"}}}
        def blank_key(p): p["facts"][" "] = p["facts"]["order.status"]
        self.holds("route_policy.schema.json", full, [
            put(("on_unresolved_instruction",), "ignore"), drop(("facts", "order.status", "on_unresolved")), drop(("facts", "order.status", "precedence")),
            put(("facts", "order.status", "precedence"), []), put(("facts", "refund.window", "precedence"), ["crm-mcp", "crm-mcp"]),
            put(("facts", "refund.window", "scope"), ["org"]), put(("facts", "refund.window", "freshness_tiebreak"), "yes"),
            put(("facts", "refund.window", "authority"), ["governing"]), blank_key])

    def test_producers_slot_rules_overrides_and_upgrades_use_closed_vocabularies(self):
        full = {**copy.deepcopy(POLICY), "clock_skew_seconds": 5,
                "slots": {"evidence.knowledge": {"min_relevance": 0.82, "max_age_seconds": 7776000, "required_scope": ["tenant"]}, "interaction.memory": {"source_prefix": "turn:"}},
                "default_overrides": {"evidence.knowledge": {"token_budget": 420}}, "tier_upgrades": {"state.user": "protected"}}
        self.holds("route_policy.schema.json", full, [
            drop(("producers",)), put(("producers", "x"), {"kind": "oracle", "slots": ["state.task"]}), put(("producers", "x"), {"kind": "mcp", "slots": []}),
            put(("slots", "evidence.web"), {}), put(("slots", "evidence.knowledge", "max_age"), "P90D"), put(("slots", "evidence.knowledge", "required_scope"), ["org"]),
            put(("tier_upgrades", "state.user"), "droppable"), put(("default_overrides", "evidence.knowledge"), {"tier": "protected"}), put(("default_overrides", "state.task"), {})])

    def test_required_slots_evidence_minimums_and_a_fitting_order(self):
        full = {**copy.deepcopy(POLICY), "parser": True, "requires_evidence": True,
                "slots": {"evidence.knowledge": {"priority": 10, "order_by": ["-relevance", "freshness"], "min_included": 2}, "interaction.history": {"priority": -1, "order_by": ["-freshness"]}},
                "fitting_order": [{"slot": "evidence.knowledge", "action": "omit"}, {"slot": "interaction.history", "action": "compress"}]}
        def repeat(p): p["fitting_order"].append({"slot": "evidence.knowledge", "action": "omit"})
        self.holds("route_policy.schema.json", full, [
            put(("parser",), "yes"), put(("slots", "evidence.knowledge", "priority"), 1.5), put(("slots", "evidence.knowledge", "order_by"), ["relevance"]),
            put(("slots", "evidence.knowledge", "order_by"), []), put(("slots", "evidence.knowledge", "min_included"), 0), put(("slots", "interaction.history", "min_included"), 1),
            drop(("requires_evidence",)), put(("requires_evidence",), False), repeat, put(("fitting_order", 0, "action"), "truncate"),
            put(("fitting_order", 0, "slot"), "evidence.web"), put(("fitting_order", 0, "priority"), 1)])
        tool = copy.deepcopy(full); tool["slots"]["evidence.tool_results"] = {"min_included": 1}
        self.assertTrue(valid("route_policy.schema.json", tool), "both evidence slots accept a minimum")
        none = copy.deepcopy(full); del none["slots"]["evidence.knowledge"]["min_included"]; none["requires_evidence"] = False
        self.assertTrue(valid("route_policy.schema.json", none), "a route without minimums need not require evidence")

    def slot_rule(self, slots, mutations):
        self.holds("route_policy.schema.json", {**copy.deepcopy(POLICY), "slots": slots}, mutations)

    def test_a_floor_of_at_least_one_token_beside_a_cap(self):
        self.slot_rule({"interaction.history": {"min_tokens": 200, "max_tokens": 100}, "governance.examples": {"min_tokens": 1}},
                       [put(("slots", "interaction.history", "min_tokens"), v) for v in (0, 2.5, None)] + [put(("slots", "governance.examples", "min_tokens"), "1")])

    def test_a_whole_number_of_items_per_source_at_least_one(self):
        self.slot_rule({"evidence.knowledge": {"max_per_source": 2, "dedupe": "exact"}, "interaction.memory": {"max_per_source": 1}},
                       [put(("slots", "evidence.knowledge", "max_per_source"), v) for v in (0, 1.5, None)] + [put(("slots", "interaction.memory", "max_per_source"), "1")])

    def test_supersede_by_source_only(self):
        self.slot_rule({"evidence.tool_results": {"supersede": "source", "dedupe": "exact"}, "evidence.knowledge": {"supersede": "source"}},
                       [put(("slots", "evidence.knowledge", "supersede"), v) for v in (True, "call_key", None)] + [put(("slots", "evidence.tool_results", "supersede"), ["source"])])

    def test_exact_deduplication_only(self):
        self.slot_rule({"evidence.knowledge": {"dedupe": "exact"}, "interaction.memory": {"dedupe": "exact", "max_tokens": 40}},
                       [put(("slots", "evidence.knowledge", "dedupe"), v) for v in (True, "near", None)] + [put(("slots", "interaction.memory", "dedupe"), ["exact"])])

    def test_max_tokens_a_whole_number_of_tokens(self):
        self.slot_rule({"evidence.knowledge": {"max_tokens": 400}, "state.task": {"max_tokens": 0}},
                       [put(("slots", "evidence.knowledge", "max_tokens"), v) for v in (-1, 1.5, None)] + [put(("slots", "state.task", "max_tokens"), "0")])


class Report(Mutations):
    REPORT = {"implementation": {"name": "contextwindowarchitecture-assembler", "version": "0.0.1", "language": "python"},
              "contract": {"repository": "contextwindowarchitecture/website", "commit": "a" * 40, "dirty": False},
              "cases": [{"id": "fixture-three-slot", "rules": ["R-16", "R-21"], "outcome": "passed"}, {"id": "messages-render", "rules": ["R-7"], "outcome": "failed", "detail": "no cwa-messages/v1 renderer"}]}

    def test_a_report_records_one_outcome_per_case_and_why_any_did_not_pass(self):
        n = len(load("contract/requirements.json"))
        def flag(r): r["cases"][0]["passed"] = True
        self.holds("conformance_report.schema.json", self.REPORT, [
            put(("cases", 0, "outcome"), "failed"), put(("cases", 1, "detail"), ""), put(("cases", 0, "outcome"), "partial"), put(("cases", 0, "rules"), [f"R-{n + 1}"]),
            put(("cases", 0, "rules"), ["R-1\n"]), put(("cases", 0, "rules"), []), put(("contract", "commit"), "abc1234"), put(("contract", "commit"), "a" * 40 + "\n"),
            drop(("contract", "repository")), put(("contract", "repository"), "website"), put(("contract", "repository"), "a/b\n"),
            put(("contract",), {"website_commit": "a" * 40, "dirty": False}), drop(("implementation", "version")), put(("implementation", "name"), "\ufeff"), flag, drop(("contract", "dirty"))])
        for i in range(1, n + 1):
            self.assertTrue(valid("conformance_report.schema.json", {**self.REPORT, "cases": [{**self.REPORT["cases"][0], "rules": [f"R-{i}"]}]}), f"R-{i}")

    def test_rejection_cases_are_rejected_failed_or_skipped(self):
        row = {"id": "profile-route-mismatch", "rules": ["R-17", "R-20"]}
        for extra, ok in [({"outcome": "rejected"}, True), ({"outcome": "failed", "detail": "assembled a payload"}, True), ({"outcome": "skipped", "detail": "renderer fixture-xml/v1"}, True),
                          ({"outcome": "failed"}, False), ({"outcome": "accepted", "detail": "assembled a payload"}, False), ({"outcome": "passed"}, False)]:
            self.assertEqual(valid("conformance_report.schema.json", {**self.REPORT, "rejections": [{**row, **extra}]}), ok, extra)


class Lock(Mutations):
    def test_the_lock_schema_rejects_a_bad_digest_an_extra_member_a_missing_list_and_a_wrong_type(self):
        self.holds("registry_lock.schema.json", load("conformance/registry/lock.json"), [
            put(("profiles", 0, "sha256"), "ABC"), put(("profiles", 0, "extra"), 1), drop(("route_policies",)), put(("route_policies", 0, "version"), 3)])


class Timestamps(unittest.TestCase):
    def test_every_format_in_the_published_schemas_has_a_pattern_beside_it(self):
        unpaired = []
        def walk(node, at):
            if isinstance(node, list):
                for i, v in enumerate(node): walk(v, f"{at}/{i}")
            elif isinstance(node, dict):
                if "format" in node and "pattern" not in node: unpaired.append(at)
                for k, v in node.items(): walk(v, f"{at}/{k}")
        for name, schema in SCHEMAS.items(): walk(schema, name)
        self.assertEqual(unpaired, [])

    def test_the_date_pattern_holds_the_shape_on_its_own(self):
        date = re.compile(SCHEMAS["profile.schema.json"]["properties"]["evaluation"]["properties"]["date"]["anyOf"][0]["pattern"])
        for value, ok in [("2026-09-22", True), ("yesterday", False), ("2026-9-22", False), ("2026-09-22T00:00:00Z", False), ("2026-09-22\n", False), ("２０２６-09-22", False)]:
            self.assertEqual(bool(date.search(value)), ok, repr(value))

    def test_a_date_time_whose_date_does_not_exist_has_the_shape_but_fails_the_asserted_format(self):
        item = load("examples/context-item.json")
        shape = re.compile(SCHEMAS["context_item.schema.json"]["properties"]["freshness"]["pattern"])
        for date in ("2026-02-30", "2026-13-01", "2026-01-00", "2023-02-29"):
            freshness = f"{date}T12:00:00Z"
            self.assertTrue(shape.search(freshness), freshness)
            errors = list(VALIDATORS["context_item.schema.json"].iter_errors({**item, "freshness": freshness}))
            self.assertTrue(any(list(e.absolute_path) == ["freshness"] and e.validator == "format" for e in errors), freshness)
        self.assertTrue(valid("context_item.schema.json", {**item, "freshness": "2024-02-29T12:00:00Z"}), "a leap day exists")
        snapshot = load("conformance/cases/admission-reasons/snapshot.json")
        bad = next(i for b in snapshot["batches"] for i in b["items"] if i.get("id") == "kb:bad-date")
        self.assertEqual(bad["freshness"], "2026-02-30T12:00:00Z")
        expected = load("conformance/cases/admission-reasons/expected.trace.json")
        self.assertEqual(next(r for r in expected["excluded"] if r["item_id"] == "kb:bad-date")["reason"], "invalid_structure")


if __name__ == "__main__":
    unittest.main()
