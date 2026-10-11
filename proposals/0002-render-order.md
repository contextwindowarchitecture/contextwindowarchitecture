# CEP-0002: Render a slot in its rank order

| CEP | 0002 |
| --- | --- |
| Title | Render a slot in its rank order |
| Authors | Melvin Hillsman ([@mrhillsman](https://github.com/mrhillsman)) |
| Champion | Melvin Hillsman, until a contributor takes it up (Abstract) |
| Sponsor | Melvin Hillsman |
| Status | Proposal |
| Type | Standards |
| Discussion | [Discussion #10](https://github.com/contextwindowarchitecture/contextwindowarchitecture/discussions/10) |
| Created | 2026-10-11 |
| Supersedes | none |

## Abstract

A route slot rule, `render_order`, is either `"id"` or `"rank"`, and defaults to `"id"`. With `"rank"`, the slot's included items render, in each placement of the slot, in the rank fitting already computes: by the route's `order_by` keys, then by `id`, highest first. With the default, every published case, payload, trace and digest stays as it is, and a route that needs stable leading bytes for a prompt cache keeps id order. On the CWA benchmark's long-context questions, the same evidence shown in rank order rather than document order answered 720 of 720 correctly, against as few as 0.817 in document order. Where the rule should live, on the route's slot rules or on the profile's placement, is open, and Rationale weighs both.

The author proposes the change and leaves the rest to contributors. Settling where the rule lives, writing the specification text and generated cases that Draft needs, and implementing it for Candidate are open to anyone, and whoever takes it to Draft becomes its champion.

## Motivation

### What the specification says now

conformance/README.md, Ordering:

> Items within a placement go by `id` in this order, with one exception: `interaction.history` renders its turns in the order they were said, by `freshness` compared as instants at full precision, and by `id` only among turns said at the same instant (R-7).

A route ranks a slot's items with `order_by` (schema/route_policy.schema.json), but only for shedding: "Rank within the slot; the lowest-ranked item sheds first (R-16)". Deduplication, supersession and the source diversity cap read the same rank to choose what to keep. Rendering does not. So a route keeps the evidence it ranks highest and then shows it by id. In examples/route-policies.json, `document-qa` sets `order_by: ["-relevance"]`, and `long-context-qa` uses the default, `["-relevance", "-freshness"]`. A retriever's ids usually follow the document a chunk came from, so both show their evidence in document order, whatever its relevance.

### Evidence

The CWA viability benchmark's Domain 2, S4, tested this ([write-up at 091eb9f](https://github.com/contextwindowarchitecture/benchmark/blob/091eb9fbaa736e6fece66932360f20b678dcb2b8/docs/domain2.md#long-context-s4)).

**Setup.**

- Synthetic corpora of fictional site documents at 0.25×, 1×, 4× and 16× an 8,192-token budget, about 3,000 to 132,000 tokens, with 10 corpora at each size.
- Six questions per corpus: a single fact, a comparison of two sites, and a fact the documents never state, each as a short answer and as multiple choice.
- Three samples per question at temperature 0, with `Qwen/Qwen3.6-35B-A3B-FP8` on vLLM 0.31.0. Every request and reply is in the benchmark's committed cache, so every result replays without a model.

**Assembly.**

- The specification at commit `16de4be`, the `long-context-qa` route's rules for `evidence.knowledge` (`min_relevance` 0.2, at least one chunk, exact deduplication, at most 8 chunks a document), and the `long-context-reinforced` profile with its repeated instructions removed.
- The retrieval arms drew on the same retriever's 64 best chunks.
- All four assemblers produced byte-identical payloads, each equal to the payload the benchmark predicted.

**Results.** The share of correct answers at each corpus size:

| Evidence order | 0.25× | 1× | 4× | 16× |
| --- | --- | --- | --- | --- |
| By id, ids following the documents (`chunk:d0042:c03`) | 0.917 | 0.950 | 0.939 | 0.817 |
| By id, ids led by the retriever's rank (`chunk:r001:d0042:c03`) | 1.000 | 1.000 | 1.000 | 1.000 |
| Conventional RAG, the same retriever, best first | 0.989 | 1.000 | 1.000 | 0.994 |
| The whole corpus in document order, no budget | 0.894 | 0.850 | 0.722 | 0.639 |

**What the table shows.**

- The first two rows keep exactly the same evidence at every budget, and every chunk an answer needed was in both payloads. Only the order differs.
- With ids that follow the documents, the misses were comparisons, where the model named the other of the two sites, and questions the documents do not answer. The whole corpus in document order missed the same questions.
- With ids led by rank, all 720 answers (240 questions, three samples each) were correct.

**The workaround, and what it costs.** An application can get rank order today by leading each id with the rank, as the second row did. But an id is meant to identify an item, not to carry an order:

- the same chunk gets another id whenever its rank changes, so traces from two calls no longer match it up, and neither does anything else keyed by id, such as a conflict group or a producer's own records;
- a reader of the trace has to know the convention to see why the evidence reads as it does;
- the rank has to be zero-padded, since ids compare by UTF-16 code units and `r10` sorts before `r9`.

**Caveats.** One model, synthetic documents, and easy retrieval: every question names its site, so every needed chunk ranked in the retriever's top three, even at 16×. The arms differ in assembly and order, not in retrieval, and harder retrieval is not tested.

## Specification

The sketch below puts the rule among the route's slot rules, as the change was first framed; Rationale weighs the profile's placement instead, and which one it becomes is open. Nothing below is applied to SPEC.md, the schemas or the conformance corpus. It is a starting point for the text the branch holds at Draft, and the champion may change it.

### What `"rank"` means

- A slot's *rank* is the one Fitting in conformance/README.md defines: its `order_by` keys, by default `["-relevance", "-freshness"]`, then `id` in UTF-16 code units, the first item ranked highest. `-relevance` ranks unscored items last.
- With `render_order: "rank"`, each placement of the slot renders the slot's included items in rank order, highest first. A slot the profile places twice renders the same order in both.
- Rank reads each item's own `relevance` and `freshness`. A variant that fitting chose does not move the item.
- `included[]` and `compressed[]` follow the rendered order, as they already follow the renderer's.
- Fitting's decisions do not change, and every fit test counts the payload as it renders, in its final order. None of the published tokenizers counts differently for a different order, because each item's rendering ends in a line break.
- Rank reads only the snapshot, so R-23's determinism holds.
- `interaction.history` may not set `render_order`: R-7 fixes the order of its turns. A route that sets it there fails its schema, and the snapshot is rejected before assembly (R-17).

### schema/route_policy.schema.json

`$defs.slot_rules` gains:

```json
"render_order": {
  "enum": ["id", "rank"],
  "description": "Order of the slot's included items within each placement (conformance/README.md, Ordering): id renders them by id; rank renders them by the slot's rank, highest first: its order_by keys, then id, as fitting ranks them (R-16). Not allowed in interaction.history, whose turns render in the order they were said (R-7). Default id."
}
```

`slots.properties` gains an entry for `interaction.history`. It repeats the `min_included` exclusion, which a slot named in `properties` does not inherit from `additionalProperties`, and excludes `render_order`:

```json
"interaction.history": {
  "allOf": [
    { "$ref": "#/$defs/slot_rules" },
    { "not": { "type": "object", "required": ["min_included"], "properties": { "min_included": true } } },
    { "not": { "type": "object", "required": ["render_order"], "properties": { "render_order": true } } }
  ]
}
```

### conformance/README.md

Ordering, second paragraph, becomes:

> Items within a placement go by `id` in this order, with two exceptions. `interaction.history` renders its turns in the order they were said, by `freshness` compared as instants at full precision, and by `id` only among turns said at the same instant (R-7). A slot whose route rules set `render_order: "rank"` renders its items in the slot's rank, highest first, as Fitting defines it: by its `order_by` keys, then by `id`. Rank reads each item's own `relevance` and `freshness`, so a variant chosen in fitting does not move it, and a slot the profile places twice renders the same order in each placement. The `history-freshness-order` case checks the first exception, and `render-order-rank` the second.

Running a case, the first bullet on array order becomes:

> `included[]` follows placement order and, within a placement, the renderer's item order, which Ordering defines: `id` order, except in `interaction.history`, whose turns go by `freshness` as instants at full precision (Timestamps) and then by `id` (R-7), and in a slot whose route sets `render_order: "rank"`, whose items go by rank. For `fixture-xml/v1` that is payload order.

Tokenizers and renderers: `fixture-xml/v1` orders the items within a placement "as Ordering says" in place of its own statement of the id and history orders, and `cwa-messages/v1` orders `system` and `tools` entries "in placement order and, within a placement, as Ordering says" in place of "by `id` within a placement". `cwa-message-blocks/v1` already follows `cwa-messages/v1`.

### SPEC.md

No requirement's text changes; R-21 already makes conformance/README.md normative for orderings. §5's prose gains one sentence after the sentence on prompt caches: "Within a placement, items go by id unless the route asks for its rank order (conformance/README.md, Ordering)."

### CHANGES.md

> - Route policy: a slot rule, render_order, id or rank, default id. With rank, the slot's included items render in each placement in the slot's rank, highest first: its order_by keys, then id, as fitting already ranks them for shedding (R-16). interaction.history may not set it, since R-7 fixes its order. Every published case, payload and digest is unchanged. The conformance README's Ordering, its trace order and its renderers say so, and the new render-order-rank and render-order-rank-messages cases and the render-order-history rejection hold it. See CEP-0002.

## Rationale and alternatives

### Where the rule lives

| | Route slot rule (as sketched) | Profile placement |
| --- | --- | --- |
| Where rank is defined | Beside `order_by`, which defines it | In another file, so a reader looks at both; the profile already names its route policy's version |
| What the file is for | The route is read by admission, conflict resolution, fitting and refusal, not by rendering | The profile places slots and picks their wrappers, which is rendering |
| Model dependence | One order for every model on the route | Placement is model-dependent and evaluated per model (§5, R-19); the evidence here comes from one model |
| Two profiles on one route | Share one order: one that wants rank and one that wants id order need two route versions | Each chooses, as `cache-first-chat` and `policy-first-chat` choose their placements on `support-chat` |
| A slot placed twice | One order for both placements | Could differ per placement, which nothing has asked for |
| Versioning | A new route version, and a new version of every profile that names it (R-20) | A new profile version: a change to placement (R-20) |
| Schema | `slot_rules` gains a member, and history is excluded | Each placement entry gains a member, excluded for history |

The case for the route is that rank is a route concept, and a route slot rule keeps its definition and its use in one place. The case for the profile is that ordering what a model reads is a placement decision, which this specification keeps model-specific and evaluated (§5, R-19); the benchmark measured one model, and another may read best last. This CEP does not choose. Its champion settles the question in the Discussion before Draft, since the answer decides which schema, which cases and which prose change.

### Other alternatives

- **Encode the rank in the id.** It works today, and the benchmark used it. Its costs are listed under Motivation: an id that changes with rank, a convention a trace reader has to know, and zero padding.
- **Make rank the default.** Every published case with two or more items in a placement outside `interaction.history`, whose rank and id orders differ, would change its payload. So would every deployed payload from an evaluated profile, which R-19 and R-20 treat as needing a new evaluation. Routes that rely on stable leading bytes for a prompt cache would lose them. A later CEP can revisit the default, before 1.0, with more evidence.
- **Best last.** Rendering the best item last, nearest the question, may suit some models. The benchmark did not test it. `render_order` is an enum, so a value such as `"rank-reversed"` can join it later without a new field, as `supersede` can gain a call-key mode.
- **Separate render keys.** A `render_by` list could order rendering by keys other than `order_by`, so that a route sheds by relevance and shows by freshness. It is more general and has no evidence behind it yet. Reusing the rank keeps one ranking per slot, and a key list can come later.
- **A position field on items.** A producer could set an item's place directly. It would be another field, under the producer's control, that duplicates `relevance`; a route rule keeps the order with the application.

### Open questions

1. Route slot rule or profile placement (above).
2. Should `long-context-qa` and `document-qa` in examples/route-policies.json adopt `"rank"` in this CEP? Each would take a new version, `illustrative/v2`, and so would the profiles that name them, `long-context-reinforced` and `document-analysis` (R-20), with the registry lock updated. Or should the examples stay as they are, and this CEP only make the rule available?
3. Should `"rank"` be allowed in every slot but `interaction.history`, or only in the evidence slots and `interaction.memory`, where items carry scores? Allowing it everywhere is simpler, and in a slot whose items carry no scores it orders them by freshness.

## Backward compatibility

- **Published corpus.** With `"id"` the default, every published case, rejection, payload, trace and digest is unchanged, and so is every published route policy, profile and lock entry.
- **Older assemblers.** `slot_rules` forbids members it does not list, so an assembler on the current schema rejects a snapshot whose route sets `render_order`, before assembly (R-17), rather than rendering it in id order without a word.
- **Registry.** Adding `render_order` to a route policy changes its content and digest, so its version must increase (conformance/README.md, Registry), and so must the version of every profile that names it (R-20).
- **Implementations.** Each listed assembler counts the new cases as not run until it runs them (Reporting results).
- **Prompt caches.** Nothing changes under the default. Under `"rank"`, a slot's bytes change when its ranks change, so a cache-ordered profile keeps rank order out of the slots whose bytes it relies on repeating.

## Conformance cases

These are sketches. Their generators write the final bytes at Draft.

- **`render-order-rank`** (R-16, R-21), with `fixture-xml/v1`, built from a table as the fitting cases are:
  - `evidence.knowledge` sets `render_order: "rank"` with the default keys. Its chunks' ids sort against their scores: `kb:b` (0.9), then `kb:d` and `kb:c` (0.7 each, `kb:d` fresher), then `kb:e` and `kb:f` (0.6 each and equally fresh, so id decides). `kb:a` (0.55) ranks lowest and is omitted for budget. The evidence renders `kb:b`, `kb:d`, `kb:c`, `kb:e`, `kb:f`.
  - `evidence.tool_results` sets `"rank"` with `order_by: ["-relevance"]`. Of its three observations, the one without a score renders last, although its id sorts first.
  - `interaction.memory` sets `render_order: "id"` and renders by id, against its rank.
  - `interaction.history` renders its turns in the order they were said, unchanged.
- **`render-order-rank-messages`** (R-16, R-21), with `cwa-messages/v1`: `governance.instructions` sets `"rank"` with `order_by: ["-freshness"]`, so its `system` entries go newest first, and `evidence.knowledge`, placed twice, sets `"rank"` with `order_by: ["freshness"]`, so both placements render oldest first.
- **`render-order-history`**, a rejection (R-7, R-17): the route sets `render_order` on `interaction.history`, so the route policy fails its schema and the snapshot is rejected before assembly.

Generators: order.py takes `ranked`, now in conflicts.py, and `placed` reads the slot's route rules, which fitting.py and messages.py pass to it. A new generator, render-order.py, holds the two cases' tables, as history.py holds its own, and all.py runs it. rejections.py adds the rejection. `check.py` derives orders and payloads from the README a second time, independently of the generators. Its `cwa-messages/v1` renderer learns rank order, and beside its check that every trace's history rows follow the order the turns were said, it checks that the rows of a slot whose route sets `"rank"` follow the slot's rank.

## Reference implementations

None yet. Implementing the rule, in one of the listed assemblers or in a new one, is open to contributors. Candidate needs two passing reports against the branch, and an issue filed in each listed assembler that fails. The Python, TypeScript, Go and Rust assemblers were all written by the specification's author, so an implementation by someone else would be this CEP's first independent evidence (proposals/README.md, Independent implementations).

## Security implications

Rank order lets an item's `relevance` and `freshness` decide where it stands within its placement. Producers control those fields, and they already control ids, which decide its place today, so no producer gains a position it could not already take. Rank never moves an item to another placement or slot, and it changes no item's `authority`, `trust` or `injection_risk`: content stays marked as R-10 requires, and an item gains no authority from where it stands (R-7). A route that ranks a slot fed by several producers interleaves scores those producers did not calibrate against each other, as fitting already does when it sheds. A route that cares lists one retriever per slot, or ranks by freshness. Only verified content with no injection risk reaches a governance slot (R-10), so rank order there reorders the application's own text.
