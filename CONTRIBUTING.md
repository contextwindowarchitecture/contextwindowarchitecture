# Contributing

Context Window Architecture is a draft specification, and changes to it are welcome: a correction, a sharper rule, a new conformance case, an implementation to list.

## Before you open a pull request

Ask a question in [Discussions](https://github.com/contextwindowarchitecture/contextwindowarchitecture/discussions), and report a problem as an issue first when it is not plain what the fix is. A change to what a requirement means is easier to agree in an issue than in a diff.

## What a pull request needs

- **The checks pass.** With [uv](https://docs.astral.sh/uv/) and Python 3.11 or newer:

  ```sh
  uv run python conformance/check.py
  uv run python conformance/check.py --write   # then commit whatever it rewrote
  uv run python -m unittest discover -s conformance/tests
  ```

  `check.py` holds the contract to itself: every case against the schemas and its digests, each rejection against exactly one snapshot check, the reason codes against the requirements, the examples, `SPEC.md` and the guides against the contract files, and the listed implementations' reports. The tests hold each schema to its rules one change at a time, check the import tool, and regenerate every case to show nothing changes.
- **Derived text is written, not edited.** The blocks between `generated` markers in `SPEC.md` and in `guides/` come from `contract/requirements.json`, `contract/model.json` and the other contract files. Edit those, then run `check.py --write`.
- **Cases come from their generators.** A case with a generator in `conformance/generators/` is changed there and regenerated: `python3 conformance/generators/<case>.py`, or every case with `python3 conformance/generators/all.py`. Review the diff.
- **A bullet in `CHANGES.md` for a change to the specification**: a requirement, a schema, a reason code, a rule in `conformance/README.md`, or a case. Add it to the newest revision, or start a new one dated today, newest first. `check.py --write` then dates `SPEC.md` by it. Wording that changes no rule needs none.
- **Every commit is signed off.** Add a `Signed-off-by` line with your name and email, as `git commit -s` does. It certifies that you can contribute the change under the project's licence, as the [Developer Certificate of Origin](https://developercertificate.org) sets out. CI checks each commit for it.

Pull requests are squash-merged by a maintainer.

## Listing an implementation

See Reporting results in [conformance/README.md](conformance/README.md): import the report with `conformance/import_report.py` and open a pull request with the file it writes under `implementations/`.

## Licence

Contributions are licensed under the Apache License 2.0, as the rest of this repository is: see [LICENSE](LICENSE) and [NOTICE](NOTICE).
