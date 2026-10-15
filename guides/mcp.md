# CWA for MCP adapters

> How to turn what a Model Context Protocol (MCP) server returns into Context Window Architecture (CWA) items, so that any MCP server can feed a CWA application without changing. It is non-normative: it applies R-10 and R-15 and the [producer guide](producers.md) to one protocol, and adds no requirement. Rules are cited by their permanent number (R-n) and are normative in [SPEC.md](../SPEC.md). It maps MCP revision **2026-07-28**, the current revision when it was written, https://modelcontextprotocol.io/specification/2026-07-28. A later MCP revision may need a later version of this guide.

## Where the adapter sits

The adapter belongs to the application, inside its MCP client, not to the server. A server cannot write a CWA item, because most of an item is not the server's to know: which route the call serves, the tenant and user it is scoped to, how relevant a resource is to this query, and whether the route trusts the server. CWA gives those to the application and the route policy (R-15). Putting the adapter in the client means every MCP server works as it is.

- **One producer per server.** The application lists each server it connects to as its own producer with `kind: mcp`, under an identity it binds itself: the endpoint and credentials it configured, never the `serverInfo` a server reports in `_meta`. MCP says `serverInfo` is self-reported and not for security decisions, and R-15 says the same of anything a producer claims about itself.
- **One batch per server per model call.** A snapshot holds at most one batch per producer (R-15), so the adapter gathers every observation from its server that this model call should see, from this turn and earlier ones, into one batch.
- **Everything happens before the freeze.** Every `tools/call`, `resources/read` and any extraction or variant the adapter computes runs before the application freezes the snapshot; assembly calls nothing (R-12, R-18, R-23). In a tool loop, each model call is a new snapshot.
- **Results are evidence, tool definitions are proposals.** The adapter sends `evidence.tool_results` and `evidence.knowledge` items. It never sends `governance.capabilities`; it hands tool definitions to the application's capability policy, which decides what the model may call (R-15).

| MCP | Becomes | Owner |
| --- | --- | --- |
| `tools/list`: a Tool | A proposal to the capability policy, which may emit a `governance.capabilities` item | Capability policy |
| `tools/call`: a complete result | One `evidence.tool_results` item per call, plus one per embedded resource | Adapter |
| `resources/read`: each entry in `contents` | One `evidence.knowledge` or `evidence.tool_results` item | Adapter |
| `prompts/get` | Not the adapter's: see Prompts | Application |
| An `input_required` result, elicitation | Nothing: the application finishes the exchange before the freeze | Application |
| `resources/list`, `resources/templates/list`, `prompts/list`, completion, icons | Nothing: discovery and display | Application |
| Notifications: `list_changed`, `notifications/resources/updated` | Nothing in a frozen snapshot; they invalidate the adapter's cache for the next one | Adapter |
| Sampling, roots, logging | Nothing: all three are deprecated in 2026-07-28 | |

## Tool definitions: proposals, never items

A tool's `description` and `inputSchema` are text a third party wrote, and once admitted they render with governing authority. So the adapter never places them (R-15): an item it sends to `governance.capabilities` is excluded with `capability_not_allowed` where the route lists that slot for it, and with `producer_slot_not_allowed` otherwise.

The adapter passes each Tool from `tools/list` to the capability policy. The policy checks it against the versioned allow-list for the route and user, and emits one item per admitted tool, with `authority: governing`, `trust: verified` and `injection_risk: none`, and lists its id in the snapshot's grant (R-15).

- **id.** MCP tool names are unique only within a server, and MCP tells clients that aggregate servers to prefix a server identifier. Use the producer id: `tool:crm-mcp/lookup_order`.
- **body.** The definition as the model will see it: `name`, `description`, `inputSchema`, and `outputSchema` if the application sends it, serialized canonically (RFC 8785). Leave out `title`, `icons` and `annotations`. MCP says clients must treat tool annotations as untrusted unless they come from trusted servers, and they are hints for the application, not text for the model.
- **source and source_version.** The allow-list, and its version with the SHA-256 of the body, as the producer guide suggests.
- **Pin the hash.** The grant names ids, not contents, so a server that rewrites a tool's description under the same name passes the grant. The capability policy closes that gap by keeping the hash it approved for each tool and declining a definition whose hash changed until someone reviews it. See Open questions.

`tools/list` results carry `ttlMs` and may be followed by `notifications/tools/list_changed`. Both only tell the adapter when to fetch the list again before a later freeze; neither changes a snapshot already frozen.

The tool guard still checks every call the model makes against the same allow-list and user before the adapter sends `tools/call` (R-5, R-15). The capability item tells the model what it may call; the guard enforces it.

## Tool results: evidence.tool_results

A `tools/call` result with `resultType: "complete"` becomes one observation item for the call. MCP results that lack `resultType`, from servers of earlier revisions, count as complete.

| Item field | From |
| --- | --- |
| `id` | The id of the model's tool call in the application, which is unique and links the observation to the call that asked for it. JSON-RPC request ids are only unique while a request is in flight. |
| `slot` | `evidence.tool_results` |
| `authority` | `observation`, or `untrusted` where the application wants the result kept out of any instruction group's peers (R-1) |
| `trust` | `unverified`. It proves nothing either way (R-15). |
| `injection_risk` | `untrusted_content`. A route that lists the server with `verified: true` permits leaving it off (R-10, R-15); it never requires that, and the marker costs nothing in an evidence slot. |
| `body` | `structuredContent`, serialized canonically, when present; otherwise the call's `text` blocks in order, joined by a blank line. MCP asks servers that return `structuredContent` to repeat it as text, so taking both would send it twice. |
| `source` | The thing observed, so repeated reads of it share a source and `supersede: source` keeps the newest (R-25). Use a domain name where the adapter knows one (`crm:orders/8821`); otherwise the tool name and its arguments serialized canonically. Arguments can hold personal data, so hash them where they would. |
| `source_version` | `sha256:` and the SHA-256 of the body, unless the result names a version of its own |
| `freshness` | When the adapter received the result |
| `expires` | Left out. Tool results carry no caching hints; the route's `max_age_seconds` bounds their age (R-3). |
| `scope` | The request's scope keys under which the call ran. A call made with a user's credentials observed that user's data, so carry `tenant` and `user` at least. |
| `lineage` | `verbatim`, or `extracted` where the body was converted from something else |

The rest of the result:

- **`isError: true`** is still an observation: the tool ran and failed, and MCP asks clients to show such errors to the model so it can correct itself. Emit it like any other result.
- **A JSON-RPC error** means nothing was observed. The adapter emits no item; the application decides whether to retry before the freeze.
- **An embedded resource** (`type: "resource"`) is its own item, mapped as under Resources, with the resource's `uri` as its source. It has its own provenance, and one call that returns several documents is several items, never one blob (R-13).
- **A resource link** (`type: "resource_link"`) is a pointer, not content. The adapter may read it with `resources/read` before the freeze and emit it as its own item; otherwise the link's `uri`, `name` and `description` stay in the call's body as text.
- **Images and audio** have no text, and an item's body is text. See Open questions.

Retrieved chunks that a tool returns are still evidence, and an MCP server that is really a retriever is better listed as such. A producer of kind `retrieval` must emit one scored item per chunk and report the near-duplicates it drops (R-13); an `mcp` producer is not bound by that, but nothing stops it from following it.

## Resources: evidence.knowledge or evidence.tool_results

Each entry in a `resources/read` result's `contents` becomes one item. The slot depends on why the application read it:

- A resource the user picked, or the application chose as reference material for the question, goes to `evidence.knowledge` with `authority: reference_only`. It needs a `relevance` score (R-13), which the adapter or the application computes against the query before the freeze. The MCP `priority` annotation is the server's opinion of importance, not relevance to this query: use it, if at all, as one input to the reranker.
- A resource read during a tool loop, as an observation of the world's current state, goes to `evidence.tool_results` with `authority: observation`.

| Item field | From |
| --- | --- |
| `id` | Unique in the snapshot across reads, since two reads of one URI can share a snapshot: the producer, the URI and a counter for the read, for example |
| `source` | The resource's `uri`. Notifications name resources by URI, and supersession keeps the newest read of each (R-25). |
| `source_version` | The `lastModified` annotation where present, otherwise `sha256:` and the SHA-256 of the body |
| `freshness` | When the adapter received the result, not `lastModified`. The content is true as of the read; a document unchanged for a year is current, and stamping it with its modification time would make `max_age_seconds` exclude it. |
| `expires` | The time received plus `ttlMs`, when `ttlMs` is above 0; left out otherwise. MCP's TTL says how long the client may treat the read as fresh, so an adapter that reuses a cached read in a later snapshot carries that limit with it, and a stale read is excluded with `expired` where it shows, instead of passing silently. A `ttlMs` of 0 or none means re-read before each freeze, not an item that is already expired. |
| `scope` | `cacheScope: "private"` means the content depends on the caller's authorization: carry `tenant` and `user`. `"public"` content may carry less, as the route requires. |
| `body` | `text`. A `blob` has no text; see Open questions. |
| `lineage` | `verbatim`, or `extracted` |
| `injection_risk`, `trust` | As for tool results |

The `audience` annotation says who content is for. Content marked `["user"]` alone is meant for display, not for the model: the adapter hands it to the interface and emits no item. See Open questions.

`notifications/resources/updated` arrives on a `subscriptions/listen` stream and names a URI. It invalidates the adapter's cached read, so the next snapshot reads the resource again. It never alters a snapshot already frozen (R-23).

## Prompts

MCP prompts are chosen by the user and written by the server. A `prompts/get` result is a list of messages with `role: "user"` or `"assistant"`.

None of this is the adapter's to send. A producer of kind `mcp` may send only the evidence slots (R-15), and a prompt is neither evidence nor governance. The user chose it, so the application's `interaction` producer carries it, the way it carries text the user pasted: the user's choice and the user-role messages form the query, which keeps `user` authority (R-1, R-10), with the server's text delimited inside the body in a form it cannot imitate. Assistant-role messages were not said by the model; if the application keeps them, they go to `interaction.history` with `authority: untrusted`, like prior model turns (R-1). An embedded resource in a prompt message is the server's content, and the adapter emits it as evidence as under Resources.

This is the least settled part of the mapping. See Open questions.

## Verified servers

The route can list an MCP producer with `verified: true` (R-15). That is the application's decision, recorded in its route policy, and the only thing it changes is that the server's output may go unmarked (R-10). It never ranks the server's claims in a fact conflict group (R-11), it never lets the adapter send a governance slot, and it never comes from the server. MCP's own advice to trust tool annotations only from trusted servers is the same decision, and the application can make it once for both.

## Variants and size

Large results are common. The adapter can offer shorter forms as variants, computed before the freeze and cached by content hash (R-18): the first part of a long text with `method: "head"` and `lineage: "extracted"`, or the fields of a `structuredContent` object the application knows the model needs. A variant must add no fact the full result lacks (R-18). Fitting chooses among them; the adapter never trims a body to fit a budget it cannot see (R-16).

## A worked example

The model asks to look up order 8821 on a CRM server that the application lists as `crm-mcp`. The tool guard checks `tool:crm-mcp/lookup_order` against the allow-list, and the adapter sends `tools/call`:

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "resultType": "complete",
    "content": [
      { "type": "text", "text": "{\"order_id\": \"8821\", \"total\": 240, \"days_since_purchase\": 12}" }
    ],
    "structuredContent": { "order_id": "8821", "total": 240, "days_since_purchase": 12 },
    "isError": false
  }
}
```

It arrives at 11:59:30. For the next model call, the adapter's batch is:

```json
{
  "items": [
    {
      "id": "obs:call_01",
      "slot": "evidence.tool_results",
      "source": "crm:orders/8821",
      "source_version": "sha256:59027491febeb808ec68b74b062341be06cb5ee271438f72b2ab758a6b547251",
      "authority": "observation",
      "trust": "unverified",
      "freshness": "2026-09-22T11:59:30Z",
      "scope": { "tenant": "northwind", "user": "u_91" },
      "lineage": "verbatim",
      "injection_risk": "untrusted_content",
      "eligibility": "crm-mcp lookup_order result for the order the user named",
      "body": "{\"days_since_purchase\":12,\"order_id\":\"8821\",\"total\":240}"
    }
  ],
  "excluded": []
}
```

The application adds `producer: { id: "crm-mcp", kind: "mcp" }` when it freezes the snapshot (R-15). The tool's definition reached the model earlier, by another route: the capability policy took it from `tools/list`, checked it, and emitted `tool:crm-mcp/lookup_order` in `governance.capabilities` with `source_version` `v3+sha256:2dc2c63222f9deb3bc10fe0a1cb3a510158ce1093d9d2e63a2ca41c56513dfb4`, the allow-list version and the hash of the definition it approved.

## Open questions

The mapping above rests on choices the specification leaves open. Each is a candidate for a later revision, and producer fixtures (the last item) would need the first ones settled.

1. **Source or call key.** Supersession groups observations by `source` (R-25). For a read, the thing read is the right key. For a call with side effects, such as adding an item to a basket twice, two calls with the same arguments are two events, and superseding one loses it. The specification's Future work already describes a producer call key, which MCP tool calls are the first producer to need.
2. **Content for the user only.** MCP content marked `audience: ["user"]` is not for the model. R-9 asks producers to report each entry they suppress, and no exclusion code means "addressed to the user"; `not_eligible` is reserved for age (R-3). This guide treats such content as never a candidate. A code for it would make the choice visible in the trace.
3. **Images, audio and blobs.** An item's body is non-blank text. An adapter can emit a description or an extraction made before the freeze (R-18), with `lineage: "extracted"` or `"generated"`, or the application can send the binary to the model outside CWA, untraced. Neither is a mapping; a typed body or an attachment reference would be.
4. **Prompts.** No producer kind fits text the server wrote and the user chose. The interaction producer can carry it as above, but that puts server text inside an item with `user` authority, which R-10 permits for pasted material and nothing written for prompts.
5. **Pinning the capability grant.** The grant names allowed ids (R-15). Naming the `source_version` too would let an assembler exclude a tool whose definition changed after review, instead of leaving it to the capability policy.
6. **Hints from servers.** A server that wants to help could put a stable source, a version or precomputed variants in `_meta` under a vendor prefix such as `io.contextwindowarchitecture/`, which MCP does not reserve. Each would be the server's claim, and a server's variants cannot be checked against R-18's rule that they add no fact, so the adapter would take them only from verified servers. No such keys are defined.
7. **Producer fixtures.** The conformance cases test assemblers: a snapshot in, a trace and payload out. Nothing tests producers. A set of MCP responses with the producer batch each should yield would let two adapters be checked against each other, once the choices above are made.

## Sources

- MCP 2026-07-28: https://modelcontextprotocol.io/specification/2026-07-28
- Tools: https://modelcontextprotocol.io/specification/2026-07-28/server/tools
- Resources and annotations: https://modelcontextprotocol.io/specification/2026-07-28/server/resources
- Prompts: https://modelcontextprotocol.io/specification/2026-07-28/server/prompts
- Caching (`ttlMs`, `cacheScope`): https://modelcontextprotocol.io/specification/2026-07-28/server/utilities/caching
- `_meta` and `resultType`: https://modelcontextprotocol.io/specification/2026-07-28/basic/index
- Deprecated features: https://modelcontextprotocol.io/specification/2026-07-28/deprecated
- Producer guide: [producers.md](producers.md)
- Requirements: [SPEC.md](../SPEC.md)
- Item schema: [schema/context_item.schema.json](../schema/context_item.schema.json)
- Producer-batch schema: [schema/producer_batch.schema.json](../schema/producer_batch.schema.json)
- Route-policy schema, where `verified` and `supersede` live: [schema/route_policy.schema.json](../schema/route_policy.schema.json)
