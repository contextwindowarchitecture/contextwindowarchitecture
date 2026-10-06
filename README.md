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
| [contract/assembler-scope.json](contract/assembler-scope.json) | What an assembler can verify of each requirement by itself, and what rests on a producer or the application |
| [guides/](guides) | How to build a producer, and how to use or build an assembler |
| [conformance/README.md](conformance/README.md) | How to run a case, and every ordering, tie-break, boundary and algorithm step the requirements leave open (R-21) |
| [conformance/cases/](conformance/cases) | Assembler test cases: a snapshot in, the expected trace and payload out |
| [conformance/rejections/](conformance/rejections) | Snapshots that break exactly one snapshot check each; an assembler rejects them before assembly, with no trace (R-17) |
| [conformance/check.py](conformance/check.py), [generators/](conformance/generators), [tests/](conformance/tests) | The contract's own checks, the generators that write the cases (`generators/all.py` runs them all), and the tests of the schemas and the import tool; [import_report.py](conformance/import_report.py) adds an implementation's report to implementations/ |
| [conformance/registry/](conformance/registry) | The profiles and route policies the cases name, and the lock that pins them |
| [implementations/](implementations) | Each listed implementation's conformance report as its own repository publishes it, with the commit it came from and the digests of the cases it ran |
| [examples/](examples) | An item, a producer batch, conflict groups, profiles and the route policies they name, a payload with its matching trace, and a message request with its snapshot and trace |

## Where to start

- To learn what CWA requires, read [SPEC.md](SPEC.md) from section 1, which defines the three conformance claims: a conformant producer, assembler and application.
- To write a producer, read section 2 of [SPEC.md](SPEC.md), then [schema/context_item.schema.json](schema/context_item.schema.json) and [schema/producer_batch.schema.json](schema/producer_batch.schema.json), with [examples/producer-batch.json](examples/producer-batch.json) beside them.
- To build an assembler, read [conformance/README.md](conformance/README.md) and run the cases. [assembler-template](https://github.com/contextwindowarchitecture/assembler-template) is a starting point for a port in a new language.

## Implementations

Assemblers in [Python](https://github.com/contextwindowarchitecture/assembler-python), [TypeScript](https://github.com/contextwindowarchitecture/assembler-typescript), [Go](https://github.com/contextwindowarchitecture/assembler-go) and [Rust](https://github.com/contextwindowarchitecture/assembler-rust) implement the specification. [implementations/](implementations) holds the conformance report each one publishes, and the [Assembler page](https://contextwindowarchitecture.io/assembler.html) counts each against these cases. To list another, see Reporting results in [conformance/README.md](conformance/README.md).

## How this repository is maintained

The specification is written here. [contextwindowarchitecture.io](https://contextwindowarchitecture.io), the assemblers and the demo each copy these files at a commit they pin, so a change reaches them when they take the new commit.

While the specification is a draft, the `draft-release` tag moves with each change, and each tag is released once its checks pass. Watching this repository's releases is enough to follow the specification.

## Contributing

Ask a question in [Discussions](https://github.com/contextwindowarchitecture/contextwindowarchitecture/discussions). Report a problem with the text, a schema or a case as an issue. To propose a change, open a pull request; [CONTRIBUTING.md](CONTRIBUTING.md) says what one needs.

Checking a change takes Python 3.11 or newer and nothing else from this project:

```sh
uv run python conformance/check.py          # verify
uv run python conformance/check.py --write  # rewrite what is derived from the contract files
uv run python -m unittest discover -s conformance/tests
```

Files in this repository before 2026-10-05 were written in the [website repository](https://github.com/contextwindowarchitecture/website); their earlier history is there, up to commit `d6875d3`.

## License

Apache License 2.0: see [LICENSE](LICENSE) and [NOTICE](NOTICE). A copy you distribute keeps both.
