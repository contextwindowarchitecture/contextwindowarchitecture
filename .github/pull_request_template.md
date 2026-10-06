<!-- What changes, and why. Name the requirements, schemas, reason codes or cases it touches. -->

- [ ] `uv run python conformance/check.py` prints `ok`
- [ ] `uv run python conformance/check.py --write` leaves no difference
- [ ] `uv run python -m unittest discover -s conformance/tests` passes
- [ ] A change to a requirement, schema, reason code, a rule in `conformance/README.md` or a case has its bullet in `CHANGES.md`
- [ ] Every commit is signed off (`git commit -s`), certifying the [Developer Certificate of Origin](https://developercertificate.org)
