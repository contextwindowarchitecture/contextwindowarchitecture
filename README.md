# Context Window Architecture

Context Window Architecture (CWA) is a draft specification for assembling every model call from typed slots. Producers emit candidate items, the application authenticates them and freezes a snapshot, and an assembler turns that snapshot into a rendered payload and a trace, deterministically and without calling a model.

This repository holds the specification by itself: its text, its JSON Schemas, its contract data, its conformance cases and its examples. [contextwindowarchitecture.io](https://contextwindowarchitecture.io) presents the same specification with guides for producers and assemblers, the evidence behind it, browser tools, and each implementation's conformance report.

## What is here

| Path | Holds |
| --- | --- |
| [SPEC.md](SPEC.md) | The normative text. The requirement index and sections 1 to 6: conformance, the model of planes, slots and items, governance, admission and fitting, placement profiles, and the trace. Each section carries its numbered requirements, and a closing section lists future work |
| [CHANGES.md](CHANGES.md) | Every revision of the draft, newest first |
| [schema/](schema) | JSON Schemas for an item, a producer batch, a conflict group, a placement profile, a route policy, a snapshot, a trace, a registry lock and a conformance report |
| [contract/requirements.json](contract/requirements.json) | Every requirement as authored: its permanent ID, section, keyword, summary and text |
| [contract/reasons.json](contract/reasons.json) | The exclusion and refusal reason codes a trace records, each with the requirement that owns it |
| [contract/slot-defaults.json](contract/slot-defaults.json) | Each slot's authority, protection tier and policy defaults, which an assembler fills in and traces (R-3) |
| [contract/model.json](contract/model.json) | The planes, slots, item fields, authority values, conflict rules, pipeline stages and tests SPEC.md lists, in the order it lists them |
| [conformance/README.md](conformance/README.md) | How to run a case, and every ordering, tie-break, boundary and algorithm step the requirements leave open (R-21) |
| [conformance/cases/](conformance/cases) | Assembler test cases: a snapshot in, the expected trace and payload out |
| [conformance/rejections/](conformance/rejections) | Snapshots that break exactly one snapshot check each; an assembler rejects them before assembly, with no trace (R-17) |
| [conformance/registry/](conformance/registry) | The profiles and route policies the cases name, and the lock that pins them |
| [examples/](examples) | An item, a producer batch, conflict groups, profiles and the route policies they name, a payload with its matching trace, and a message request with its snapshot and trace |

## Where to start

- To learn what CWA requires, read [SPEC.md](SPEC.md) from section 1, which defines the three conformance claims: a conformant producer, assembler and application.
- To write a producer, read section 2 of [SPEC.md](SPEC.md), then [schema/context_item.schema.json](schema/context_item.schema.json) and [schema/producer_batch.schema.json](schema/producer_batch.schema.json), with [examples/producer-batch.json](examples/producer-batch.json) beside them.
- To build an assembler, read [conformance/README.md](conformance/README.md) and run the cases. [assembler-template](https://github.com/contextwindowarchitecture/assembler-template) is a starting point for a port in a new language.

## Implementations

Assemblers in [Python](https://github.com/contextwindowarchitecture/assembler-python), [TypeScript](https://github.com/contextwindowarchitecture/assembler-typescript), [Go](https://github.com/contextwindowarchitecture/assembler-go) and [Rust](https://github.com/contextwindowarchitecture/assembler-rust) implement the specification. The [Assembler page](https://contextwindowarchitecture.io/assembler.html) shows the conformance report each one publishes against these cases.

## Where these files come from

The specification is authored in the [website repository](https://github.com/contextwindowarchitecture/website), and every file here is written from it: nothing is edited in this repository. Each file under the paths above is a byte-for-byte copy of the website's file at the same path. [website.lock.json](website.lock.json) names the website commit the copy was taken at and the SHA-256 of every file, and this repository's CI checks the files against that commit.

Releases here follow the website's. A tag is released only once its files match the website at the same tag, so watching this repository's releases is enough to follow the specification. While the specification is a draft, the `draft-release` tag moves to each new export.

SPEC.md is the normative text, and the [Spec page](https://contextwindowarchitecture.io/spec.html) renders it. CHANGES.md lists every revision.

To report a problem or propose a change, open an issue or pull request in the [website repository](https://github.com/contextwindowarchitecture/website).

## License

Apache License 2.0: see [LICENSE](LICENSE) and [NOTICE](NOTICE). A copy you distribute keeps both.
