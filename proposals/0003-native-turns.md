# CEP-0003: Render turns and tool exchanges as platform messages

| CEP | 0003 |
| --- | --- |
| Title | Render turns and tool exchanges as platform messages |
| Authors | Melvin Hillsman ([@mrhillsman](https://github.com/mrhillsman)) |
| Champion | Melvin Hillsman |
| Sponsor | Melvin Hillsman |
| Status | Proposal |
| Type | Standards |
| Discussion | [Discussion #15](https://github.com/contextwindowarchitecture/contextwindowarchitecture/discussions/15); related: [issue #2](https://github.com/contextwindowarchitecture/contextwindowarchitecture/issues/2) |
| Created | 2026-10-22 |
| Supersedes | none |

## Abstract

CWA renders every prior turn and every tool result as XML inside a single user message (R-7, R-10). For reasoning models this has three costs:

- the model's reasoning from one step of a tool loop does not reach the next step, although the providers require it within a tool-use turn and recommend it across turns;
- untrusted tool output reaches the model in the user role, which the instruction hierarchy ranks above tool output;
- the model's own tool calls and their results reach it as a transcript it was not trained on, and parallel calls lose their pairing.

This CEP adds an optional renderer, `cwa-native-turns/v1`. Under it, a profile can place `interaction.history` and `interaction.query` with a new wrap, `turns`, and the renderer then emits:

- prior turns and the query as user and assistant messages;
- the model's tool calls and the reasoning that came with them as parts of assistant messages;
- each call's result as a result part bound to its call.

A tool result still renders inside its slot's wrapper and keeps its `untrusted_content` marking. Every other slot stays XML-wrapped material.

To support this, the CEP makes these changes:

| What changes | Change |
| --- | --- |
| Item fields | Three optional fields: `parts`, `call_id` and `reasoning_tokens` |
| R-27 (new) | A call and its results form an *exchange*, included whole or not at all |
| R-7, R-10 | Amended to allow native roles only under a renderer that renders turns |
| R-2, R-16 | Amended for `parts` and for reasoning that no tokenizer can count |
| Reason codes | Three new codes |

`cwa-messages/v1`, `cwa-message-blocks/v1`, `fixture-xml/v1` and every published case, payload, trace and digest stay as they are.

## Motivation

### What the specification says now

R-7:

> Prior turns in interaction.history MUST render inside the profile's history wrapper as a transcript, in the order they were said [...]. They never render as platform user or assistant messages; only interaction.query renders as the live user turn.

R-10:

> User-controlled quoted material, attachments, retrieved chunks, memory and tool output MUST be marked injection_risk: untrusted_content, [...] and, when supplied as items of their own, rendered inside their slot's wrapper, never in a platform system or tool role (R-7).

conformance/README.md, `cwa-messages/v1`:

> `messages`: exactly one message, `{"role": "user", "content": text}`. [...] Prior turns are part of this transcript and never become messages of their own; the query is the only live user turn (R-7).

`cwa-message-blocks/v1` keeps the rule: its entries "are content parts of the one user message, never messages of their own (R-7)". §1 has a conformant application hand over "text assigned none in a single user message, where the query alone is the live turn, and no text of its own".

R-2 requires a non-blank string `body` on every item. An assistant step that only calls a tool has no text. The item schema has no field for a call id or for a reasoning block, and it sets `additionalProperties: false`.

### What goes wrong

**1. Reasoning does not survive a tool loop.** Each step of a CWA tool loop is a new snapshot (R-12, R-23). The model's previous step comes back as a history item, and its reasoning is lost. Both large providers say not to do this:

- **Anthropic's thinking guide** ([Preserving thinking blocks](https://platform.claude.com/docs/en/build-with-claude/thinking#preserving-thinking-blocks)):
  - It says: "Required: within a tool-use turn, pass thinking blocks back. Recommended: across turns, pass everything back."
  - Within the latest assistant message, the thinking blocks "must match what the model generated in the original request: you can't rearrange, edit, or partially drop them"; a modified block is rejected with a 400 error.
  - Claude Opus 4.5 and later Opus models, Claude Sonnet 4.6 and later Sonnet models, and the 5-series models keep prior turns' thinking blocks in context by default.
  - With the default `display: "omitted"`, the readable `thinking` field is empty. The `signature` carries the encrypted reasoning "for multi-turn continuity", so a transcript cannot carry it even in principle.
- **OpenAI's reasoning guide** ([Reasoning models](https://developers.openai.com/api/docs/guides/reasoning)):
  - It says: "we highly recommend you pass back any reasoning items returned with the last function call", and "you should pass back all reasoning items, function call items, and function call output items".
  - GPT-5.6 models "default to rendering available reasoning from earlier turns."

CWA's own integration shows the cost. The landing page's OpenAI Agents SDK seam (CHANGES.md, 2026-09-30) uses `call_model_input_filter` to replace the SDK's input before every model call with the system entries and the one user message. That is what §1 requires. It also discards, on every step of the agent's loop, the reasoning items and function-call items the SDK would have passed back.

**2. Tool output is placed in a higher-privilege role.** The instruction hierarchy that providers train for ranks system above user, and user above third-party content such as tool output ([Wallace et al., 2024, arXiv:2404.13208](https://arxiv.org/abs/2404.13208)). R-10 keeps tool output out of the tool role, but the only place left for it is the user message. A model trained on the hierarchy reads an `<observation>` in the user role with more privilege than the same text in a tool result. The XML wrapper and the marking are a convention the model may or may not honour. The role is what the model was trained on.

**3. The structure does not match the model's training.** Agentic post-training uses alternating messages, with calls paired to results by id. A transcript of `<history speaker="assistant">` elements inside one user message is a different shape. The model's own calls also vanish from that transcript: it sees an `<observation>` with no call before it. When a step makes parallel calls, nothing ties each result to its call except ids the application has to invent.

### Evidence, and what is missing

The evidence for points 1 and 3 is what the providers document, not a measurement in CWA's benchmark. The evidence for point 2 is a published training method. This CEP does not claim a measured effect. Before Candidate, its champion runs the benchmark described here, and the CEP records the result whichever way it falls:

- **Arms:**
  - `cwa-messages/v1` with the `cache-first-chat` placement;
  - `cwa-native-turns/v1` with the same placement and history and query on `turns`;
  - the provider's own message loop with no assembly, as a ceiling.
- **Models:** at least one keep-all Claude model with adaptive thinking and one OpenAI reasoning model, at the providers' default reasoning settings.
- **Tasks:** multi-step tool tasks of 3 to 15 calls each, with parallel calls in some, and a judge that scores the final state.
- **Measures:**
  - task success;
  - malformed or repeated calls;
  - input tokens and cached input tokens per task;
  - success rate of injected instructions planted in tool results, AgentDojo-style, to test point 2 directly.
- **Caveat stated in advance:** if point 2 does not hold, the change still stands on points 1 and 3. Its security section would then say that native roles neither help nor hurt injection resistance.

### Relation to issue #2

Issue #2 covers an application that hands its payload to an agent runtime it does not control. CWA then assembles only the first context, and the runtime builds every later call. This CEP covers the opposite case: an application that runs its own loop and assembles every call. That includes the Agents SDK seam above. The two are complementary. With this CEP, an application that could hand its loop to a runtime because CWA's single message lost its reasoning can keep the loop and stay conformant.

## Specification

This is an outline at Proposal. Nothing below is applied to SPEC.md, the schemas or the conformance corpus yet.

### Terms

- **Step:** an `interaction.history` item with `lineage: generated` that carries `parts`. It records one model response: its reasoning, its text and its calls, in the order the model produced them.
- **Exchange:** a step whose parts include one or more calls, together with every `evidence.tool_results` item whose `call_id` names one of those calls.
- **Current trajectory:** every history item said later than the query, compared by `freshness` as instants at full precision (R-7). Under `cwa-native-turns/v1`, every such item MUST be a step with at least one call; a snapshot with any other history item said after the query is rejected. A model response with no call ends the trajectory, and the application writes it into history before the next query.
- **Latest exchange:** the exchange whose step is the last item of the current trajectory.

### Item fields (schema/context_item.schema.json)

**`parts`** (array, at least one entry). It is allowed only on `interaction.history` items with `lineage: generated`, and an item carries either `body` or `parts`, never both. Each entry is one of:

```json
{ "type": "text", "text": "Let me check order 8821." }
{ "type": "reasoning", "format": "anthropic.thinking", "data": "<opaque string>" }
{ "type": "call", "call_id": "toolu_01", "name": "lookup_order", "input": "{\"order_id\":\"8821\"}" }
```

- `text` is a non-blank string.
- `format` is an application-defined, non-blank string naming the provider shape of `data`.
- `data` is an opaque, non-empty string. An application keeps the provider's block in it exactly as received, for example as its RFC 8785 serialization. The assembler never reads, escapes, trims or compares it.
- `call_id` is a non-blank string, unique across every call in the snapshot.
- `input` is the call's arguments as a JSON text.

**`reasoning_tokens`** (integer, at least 0). It is required when any part has type `reasoning`, and not allowed otherwise. It is the number of input tokens the provider counts for the item's reasoning parts, normally taken from the usage the provider reported for the response that produced them. R-18 already requires this kind of precomputed value.

**`call_id`** (non-blank string). It is allowed only on `evidence.tool_results` items.

`variants` is not allowed on an item that carries `parts`, since reasoning cannot be shortened.

### R-2 (amended)

The first sentence becomes:

> Every item MUST carry id, slot, source, source_version, authority, freshness and trust, and exactly one of body and parts, and MUST satisfy the published context_item.schema.json.

An item with neither `body` nor `parts` is excluded with `missing_field:body`. R-24's body comparison skips items that carry `parts`.

### R-7 (amended)

The third and fourth sentences become:

> Prior turns in interaction.history MUST render in the order they were said: by freshness, which for a turn records when it was said (R-2), compared as instants at full precision, and by id among turns said at the same instant. Under a renderer that renders turns as messages (conformance/README.md, Tokenizers and renderers), each turn renders as a platform message of its speaker: a turn with lineage: generated as an assistant message and any other turn as a user message, and interaction.query renders as the user message that opens the current trajectory; no other slot's item takes the user or assistant role except as a content part the renderer assigns to such a message. Under any other renderer, turns render inside the profile's history wrapper as a transcript and never as platform user or assistant messages; only interaction.query renders as the live user turn.

An assembler MUST exclude with `producer_slot_not_allowed` any item that carries `parts` from a producer whose kind is not `interaction`, whatever the route lists.

### R-10 (amended)

The phrase "never in a platform system or tool role (R-7)" becomes:

> never in a platform system role, and in a platform tool role only as the result of a call the payload renders (R-27), still inside its slot's wrapper and still marked (R-7).

### R-16 (amended)

Two sentences are added after "with the declared tokenizer":

> A call renders its name and input as text. A reasoning part is not text the tokenizer can read: the assembler counts each included item's reasoning_tokens in place of its reasoning parts.

One sentence is added to the shedding rules:

> The members of an exchange (R-27) are omitted together, at the place in tier order and rank that the exchange's step takes, and each is recorded over_budget.

### R-27 (new): Tool calls and their results render as exchanges

> Every call_id in a snapshot's parts MUST be unique, every evidence.tool_results item's call_id MUST name a call in a step, and every call MUST have exactly one evidence.tool_results item naming it; a snapshot that breaks any of these is rejected before assembly (R-17). An assembler MUST include an exchange whole or not at all. When any member of an exchange other than the latest is excluded, the assembler MUST exclude every other member with reason exchange_incomplete, stage assembler and exchange naming the step. The latest exchange is protected (R-16), and when any of its members is excluded the assembler MUST refuse with trajectory_incomplete. R-24, R-25 and R-26 do not apply to exchange members. Under a renderer that does not render turns as messages, an item that carries parts MUST be excluded with parts_not_renderable, and call_id has no effect.

### Reason codes (contract/reasons.json)

| Code | Kind | Where in the order | Rule | Text |
| --- | --- | --- | --- | --- |
| `parts_not_renderable` | exclusion | after `slot_unplaced` | R-27 | The item carries parts, and the snapshot's renderer does not render turns as messages. |
| `exchange_incomplete` | exclusion | after `source_diversity_cap`, before `over_budget` | R-27 | Another member of the item's exchange was excluded, so the whole exchange is excluded. The record's exchange names the step. |
| `trajectory_incomplete` | refusal | after `protected_slot_unplaced` | R-27 | A member of the latest exchange was excluded, so the model would see a call without its result, or a result without its call. |

schema/trace.schema.json: an `excluded[]` record gains `exchange` (the step's id) when its reason is `exchange_incomplete`.

### conformance/README.md: `cwa-native-turns/v1`, under Optional

The payload is the RFC 8785 serialization, in UTF-8, of an object with three members:

- `system` and `tools`: exactly as `cwa-messages/v1` builds them.
- `messages`: an array of `{"role": "user" | "assistant", "content": [part, ...]}`, where adjacent parts with the same role always form one message, so roles alternate. Each part carries the `id` of the item it comes from. The renderer emits parts in this order:
  1. **Lead parts:** each occurrence placed with an `xml:` wrap before the `turns` placements, as `{"type": "text", "id", "text"}`, rendered exactly as `cwa-messages/v1` writes it into its text. These are user parts.
  2. **Prior turns, in R-7's order:**
     - a user turn is a user part, `{"type": "text", "id", "text": body}`;
     - a generated turn with a `body` is an assistant text part;
     - a step is assistant parts, one per entry in its `parts`, in order;
     - an included exchange's results follow its step as user parts, in the order of its calls: `{"type": "result", "id", "call_id", "text"}`, where `text` is the result rendered as `fixture-xml/v1` renders it under the tag of the profile's `evidence.tool_results` placement.
  3. **The query:** a user part, `{"type": "text", "id", "text": body}`.
  4. **The current trajectory:** each step and its results, as in item 2.
  5. **Tail parts:** each occurrence placed with an `xml:` wrap after the `turns` placements, as user parts, rendered as in item 1.

  A reasoning part renders as `{"type": "reasoning", "id", "format", "data"}` and a call as `{"type": "call", "id", "call_id", "name", "input"}`. Turn and query bodies are not escaped, since the message boundary delimits them. A result's body is escaped as `fixture-xml/v1` escapes it. A surfaced conflict member's text is wrapped in `<conflict group="…">` as `cwa-messages/v1` wraps a system entry.

  Because the trajectory always ends with the latest exchange's results, and the tail parts follow them, the last message is always a user message. No payload ends in an assistant message, so none can act as a prefill.

**Realizability.** A profile is realizable when:

- every `system` and `tools` rule of `cwa-messages/v1` holds;
- `interaction.query` is placed exactly once, with wrap `turns`;
- `interaction.history`, when placed, is placed exactly once, with wrap `turns`, immediately before the query;
- no other slot takes `turns`;
- `evidence.tool_results` is placed, with an `xml:` wrap, whenever the profile places `interaction.history`. Its position renders only the results that are not exchange members.

**Count.** `result.input_tokens` is the tokenizer's count of every `text`, every call's `name` and `input`, and every system and tool entry's `text`, plus the `reasoning_tokens` of each included step. Per-item `tokens` count, for a step, its text parts, call names and inputs plus its `reasoning_tokens`; for a turn or query, its body; for a result, its escaped body. Roles, part types, ids, `format`, `data` and JSON punctuation are not counted, and `budget.margin_percent` covers them (R-16).

**Item order.** `included[]` follows the order of parts. An exchange's results appear after its step, not at the `evidence.tool_results` placement.

**Mapping.** An application maps the payload to a provider's request, for example:

| CWA part | Anthropic Messages | OpenAI Responses |
| --- | --- | --- |
| `call` | `tool_use` block | `function_call` item |
| `result` | `tool_result` block | `function_call_output` item |
| `reasoning` | the `thinking` or `redacted_thinking` block held in `data` | the `reasoning` item held in `data` |

The mapping adds no text, as §1 requires.

### Example payload (abridged)

```json
{
  "messages": [
    {"role": "user", "content": [
      {"type": "text", "id": "user:profile", "text": "<user_profile id=\"user:profile\">\nplan=pro; region=EU\n</user_profile>\n"},
      {"type": "text", "id": "turn:16", "text": "Is my order refundable?"}
    ]},
    {"role": "assistant", "content": [
      {"type": "text", "id": "turn:17", "text": "Which order?"}
    ]},
    {"role": "user", "content": [
      {"type": "text", "id": "turn:18", "text": "8821. Can you just process it now?"}
    ]},
    {"role": "assistant", "content": [
      {"type": "reasoning", "id": "step:19", "format": "anthropic.thinking", "data": "{\"signature\":\"Eos...\",\"thinking\":\"\",\"type\":\"thinking\"}"},
      {"type": "call", "id": "step:19", "call_id": "toolu_01", "name": "lookup_order", "input": "{\"order_id\":\"8821\"}"}
    ]},
    {"role": "user", "content": [
      {"type": "result", "id": "obs:order-8821", "call_id": "toolu_01", "text": "<observation id=\"obs:order-8821\">\n{\"total\": 240, ...}\n</observation>\n"},
      {"type": "text", "id": "task:refund_request", "text": "<task id=\"task:refund_request\">\nverify_eligibility=pending\n</task>\n"}
    ]}
  ],
  "system": [{"id": "policy:v12", "text": "You are Ada, a support agent for Northwind."}],
  "tools": [{"id": "tool:lookup_order", "text": "{\"name\": \"lookup_order\", ...}"}]
}
```

### SPEC.md

- §1's handoff clause gains: "or, under a renderer that renders turns as messages, in the messages it renders".
- §2's `interaction.history` rule and §3.1 cite R-27.
- The test list in §6.1 gains a native-turns row: a step's reasoning reaches the next call unchanged, and a tool result renders in the tool role, inside its wrapper and marked.

### CHANGES.md

> - cwa-native-turns/v1, a renderer published as optional: prior turns and the query render as user and assistant messages, the model's steps carry their reasoning and calls as parts, and each call's result renders bound to its call, still inside its slot's wrapper and marked (R-7, R-10). Items gain parts, reasoning_tokens and call_id; R-27 includes a call and its results whole or not at all, protects the latest exchange, and adds parts_not_renderable, exchange_incomplete and trajectory_incomplete. R-2 and R-16 say how parts are carried and counted. Every published case, payload and digest is unchanged. See CEP-0003.

## Rationale and alternatives

**Why split the trajectory from prior turns by freshness, and not with a new slot.** An `interaction.trajectory` slot would make the split explicit. But it changes the closed set of eleven slots (R-1), the slot defaults, every producer guide and every route schema, and it would duplicate history's order rule. The query already records when it was said, and R-7 already orders turns by that instant. A history item said later than the query is, by definition, part of the work answering it. The cost is that the split depends on the application's clock. Within one application the query and the steps come from the same clock. Open question 1 asks whether that is enough.

**Why protect only the latest exchange.** Anthropic rejects a request whose latest assistant message has modified thinking. That is a hard constraint on one message. Earlier steps are recommended, not required. Protecting the whole trajectory would make a long loop refuse with `protected_content_over_budget` once it outgrew the window. Leaving earlier exchanges compressible lets fitting drop them, oldest first, as whole exchanges. The provider then sees a shorter but well-formed turn.

**Why an exchange is the unit.** Every provider rejects a call without its result. Dropping a result for budget, supersession or a lost conflict, while its call still renders, produces a request that fails. A unit with one place in the rank and one cascade code keeps every such case well-formed and visible in the trace.

**Why exempt exchange members from R-24, R-25 and R-26.** Those rules thin repeated evidence. An exchange records what the model did. Superseding an older `lookup_order` result would also remove the step that made the call, which is a different decision from keeping evidence fresh. A route that wants old results gone omits them through fitting or through history's own bounds.

**Why opaque reasoning with a declared count.** The assembler cannot read encrypted reasoning, and the providers forbid altering it. Anything other than carrying it byte for byte, with a count the producer takes from the provider, either breaks the request or invents a number.

**Alternatives not taken:**

- **Keep the transcript (status quo).** This costs everything under Motivation. `cwa-message-blocks/v1` already solved caching, but none of the three points above.
- **Append native turns outside CWA.** An application assembles the first context and appends the provider's own loop. Its trace and hash then no longer describe what the model read, and §1's application claim is lost. This is what issue #2 names for runtimes, applied where it is not necessary.
- **One renderer per provider** (`cwa-anthropic/v1`, `cwa-openai-responses/v1`). This is simpler to map, but the specification is provider-neutral and every assembler would carry each provider's shape. A neutral part model with an application-side mapping keeps that out of the assembler, as `cwa-messages/v1` already does for roles.
- **Render prior turns natively but keep tool exchanges as text.** This avoids R-27 for prior turns. But Anthropic recommends passing everything back across turns, and keep-all models and GPT-5.6 read prior-turn reasoning by default, so it would discard the reasoning those models now keep.
- **Make native rendering a route rule.** Whether a model reads turns better as messages or as a transcript is a placement question, which §5 and R-19 make model-dependent and evaluated per profile. A wrap value keeps it in the profile, beside `system` and `tools`.

### Open questions

1. **The split by freshness.** Should the trajectory be marked explicitly, for example by a step's `answers` field naming the query's id, rather than by comparing freshness?
2. **Steps under other renderers.** Should a step under `cwa-messages/v1` be excluded, as sketched, or render as text, with its text parts and each call as `<call id name>input</call>`? The second lets an application switch renderers without losing steps, but it changes a required renderer.
3. **Shedding prior history.** When fitting drops the oldest turns, should it drop whole rounds (a user turn and every model turn after it) so the first message is always a user message? Some providers require that, and the renderer cannot add text to fix it.
4. **Allowed reasoning formats.** Should a route list the reasoning `format`s it accepts? A format the provider does not verify, such as plain reasoning text for a self-hosted model, is text the model reads as its own thinking.
5. **Server-side tools.** A provider's own tools return blocks inside the assistant message. Are they `reasoning`-like opaque parts, or out of scope for v1?
6. **Required or optional.** This CEP publishes the renderer as optional. Should a later CEP make it required, once independent assemblers carry it?

## Backward compatibility

- **Published corpus.** No published case uses `parts`, `call_id`, `reasoning_tokens` or `turns`, so every case, rejection, payload, trace and digest is unchanged. New reason codes are inserted in the order, but they apply only to items that carry the new fields, so no published case's earliest code changes.
- **Required renderers.** `parts_not_renderable` is the one change under `cwa-messages/v1`, `cwa-message-blocks/v1` and `fixture-xml/v1`. Its case uses a required renderer, so every listed assembler must implement that exclusion. This applies even to one that leaves `cwa-native-turns/v1` out.
- **Older assemblers.** The item schema forbids members it does not list, so an assembler on the current schema excludes an item carrying `parts` or `call_id` with `invalid_structure`. It never renders such an item silently in the wrong shape.
- **Registry.** A profile that adopts `turns` is a new profile version (R-20), evaluated before deployment (R-19). No published profile changes. An example profile, `native-turns-chat/v1` on `support-chat`, may be added unevaluated, as `cache-first-chat/v1` was.
- **Implementations.** Each listed assembler counts the new cases as not run until it runs them. An assembler that leaves the renderer out skips its cases (Reporting results) and still stops on an application renderer under its ID (R-16).
- **Producers and applications.** A producer of kind `interaction` that records steps keeps each provider block unchanged and records the provider's reasoning token count. An application maps parts to its provider's request without adding text.

## Conformance cases

These are sketches. A new generator, `conformance/generators/native.py`, writes them, `all.py` runs it, and `check.py` derives each payload a second time from the README.

Cases:

- **`native-render`** (R-7, R-10, R-16, R-27), with `cwa-native-turns/v1`:
  - lead parts;
  - two prior rounds, one holding an exchange with two parallel calls whose results' ids sort against their call order;
  - the query;
  - a two-step trajectory, each step with reasoning, text and calls in the order produced;
  - tail parts.

  It holds role alternation, merging of adjacent parts, results in call order, escaping of results only, and `reasoning_tokens` in the count.
- **`native-exchange-cascade`** (R-27): a prior exchange's result loses a fact group and its step is excluded `exchange_incomplete`. A second prior exchange's result is unmarked (`untrusted_content_unmarked`) and its step follows it.
- **`native-fitting`** (R-16, R-27): budget pressure omits the oldest prior exchange whole, each member `over_budget`, before a later compressible turn. The latest exchange stays, protected.
- **`native-exemptions`** (R-24, R-25, R-26): a route sets `supersede: source`, `dedupe: exact` and `max_per_source: 1` on `evidence.tool_results`. Exchange members are untouched, and results that are not exchange members are thinned as before.
- **`native-trajectory-incomplete`** (R-27, R-17): the latest exchange's result is unmarked, so assembly refuses with `trajectory_incomplete`.
- **`native-latest-over-budget`** (R-16, R-17): the latest exchange alone exceeds the budget, so assembly refuses with `protected_content_over_budget`.
- **`parts-not-renderable`** (R-27), with `cwa-messages/v1`: a step is excluded `parts_not_renderable`. Its result's `call_id` has no effect, and the result renders as today.

Rejections:

- **`native-unrealizable-split`:** history and query are not adjacent.
- **`native-call-unanswered`:** a call has no result.
- **`native-result-unmatched`:** a result names no call.
- **`native-call-id-repeated`:** two calls share a `call_id`.
- **`native-step-without-call`:** a generated turn with no call is said after the query.

## Reference implementations

None yet. Candidate needs passing reports from two assemblers against the branch, and an issue in each listed assembler that fails. The Python, TypeScript, Go and Rust assemblers were all written by the specification's author. The `parts_not_renderable` exclusion is the only part every one of them must carry. An implementation by someone else would be this CEP's first independent evidence (proposals/README.md, Independent implementations).

## Security implications

- **Tool output moves to a lower-privilege role.** A result renders where trained models give third-party content the least authority, and it keeps its wrapper and its `untrusted_content` marking (R-10), so nothing the current renderers give it is taken away. Whether this lowers injection success is measured before Candidate (Motivation).
- **Forged assistant turns.** A producer that controls history can now place text in the assistant role, where a model reads it as its own words. That is the mechanism of many-shot and fake-history jailbreaks. Three safeguards apply:
  - only a producer of kind `interaction`, authenticated and bound outside the items (R-15), may send steps;
  - provider-signed reasoning is tamper-evident, since Anthropic rejects modified thinking blocks with a 400 error;
  - plain text and calls are not tamper-evident. An application that cannot trust its history store should keep `xml:` history.
- **Forged calls and results.** A forged exchange can make the model believe it already took an action. R-5 still holds: the application enforces invariants and tool permissions outside the model, so a forged exchange changes what the model believes, not what it may do.
- **Opaque data.** The assembler passes `data` unread. A `format` the provider does not verify lets whoever writes it supply text the model reads as its own reasoning. Open question 4 asks whether routes should allow-list formats. Until then, an application treats unverified reasoning formats as it treats untrusted text.
- **Account and tenant binding.** Some providers bind reasoning blocks to the account that produced them; Anthropic says Claude Sonnet 5.5 and Claude Haiku 5.5 thinking blocks "work only in the account that produced them". Scope rules (R-2) still keep one tenant's steps out of another's snapshot, and the provider's binding is a second check.
- **No prefill path.** Every payload ends in a user message, so a step can never become a prefill.
- **Declared counts.** `reasoning_tokens` is producer-declared. Under-declaring it can push a payload past the model's window although the trace says it fits. Producers take it from the provider's reported usage, and `budget.margin_percent` should cover the difference. Over-declaring, as when a provider strips older reasoning itself, errs on the safe side.
