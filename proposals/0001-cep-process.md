# CEP-0001: The CEP process and project governance

| CEP | 0001 |
| --- | --- |
| Title | The CEP process and project governance |
| Authors | Melvin Hillsman ([@mrhillsman](https://github.com/mrhillsman)) |
| Champion | Melvin Hillsman |
| Sponsor | Melvin Hillsman |
| Status | Draft |
| Type | Process |
| Discussion | _to be linked: a Discussion in the Governance category_ |
| Created | 2026-10-11 |
| Supersedes | none |

## Abstract

This CEP adopts [GOVERNANCE.md](../GOVERNANCE.md) and the CWA Enhancement Proposal process in [proposals/README.md](README.md). A change to what the specification means becomes a CEP. It starts as an Idea in Discussions, becomes a file added by a pull request and numbered by it, moves through stages that each end with an artifact from CWA's own conformance suite, and is decided by a motion, a 10-day final comment period and written answers to every objection. A merged CEP is never edited, only superseded. Governance names a Lead Maintainer, maintainers and contributors, all of them individuals, a written path to becoming a maintainer, and three rules against capture by one organization, written now and in effect at stated thresholds. As the Model Context Protocol adopted its governance through SEP-932, this is the first proposal, and the process it describes decides it.

## Motivation

The process today is informal. CONTRIBUTING.md says to report a problem as an issue first when the fix is not plain, that "a change to what a requirement means is easier to agree in an issue than in a diff", and that "pull requests are squash-merged by a maintainer". That has served the fixes so far: each revision since 2026-10-04 went from an issue to a pull request with its CHANGES.md bullet. It does not say who decides a change to what the specification means, how long anyone has to object, who answers a proposal from outside, or what evidence a change needs before it lands.

Two such changes are waiting. CEP-0002 would let a route render a slot's items in rank order, on evidence from the CWA benchmark. Issue contextwindowarchitecture/contextwindowarchitecture#2 would name a new claim in §1 for applications whose payload an agent runtime sends. Deciding the first of them ad hoc would set the process by precedent.

CWA is meant to grow into a community effort, with maintainers from more than one organization. Rules that keep one organization from steering it are easiest to adopt before anyone they would bind has joined, so they are written now and take effect at thresholds. Until then, the process has to fit one maintainer: nothing in it needs a second person to exist.

## Specification

This CEP adds [GOVERNANCE.md](../GOVERNANCE.md), [proposals/README.md](README.md) and [proposals/0000-template.md](0000-template.md), and points CONTRIBUTING.md, README.md, the spec-change issue template, the issue chooser and the pull request template at them. What it decides, as of this CEP:

**Governance.**

- Roles are Lead Maintainer, maintainers, contributors and emeritus maintainers. Every role is held by a person, not by an organization, and stays with them when they change employer.
- Melvin Hillsman is the Lead Maintainer and, today, the only maintainer.
- A contributor becomes a maintainer after at least three months of sustained work, on a maintainer's nomination in Governance Discussions, after 7 days open, by the Lead Maintainer's decision while there is one maintainer and by the maintainers' afterwards. Maintainers inactive for 12 months become emeritus after being asked.
- Maintainers decide by rough consensus (RFC 7282). While every maintainer comes from one organization, the Lead Maintainer decides what consensus does not. A vote is a last resort, possible only once maintainers come from two or more organizations.
- Three rules against capture, each in effect while its threshold holds:
  - while maintainers come from two or more organizations, a change to what the specification means, and every Process CEP, needs approving reviews from maintainers of two organizations (OpenTelemetry);
  - while there are five or more maintainers, no organization holds more than two in five seats (PEP 13);
  - while maintainers come from two or more organizations, a vote gives one vote to each organization (W3C, CloudEvents).
- Every decision is recorded in public, on its pull request or in Discussions. Discussions is the venue: Ideas, Announcements and a new Governance category. A decision reached elsewhere counts once it is posted.
- Later steps, each through its own Process CEP: release freezes, working groups, more roles, a steering committee or a term for the Lead Maintainer, a foundation home with funding kept apart from technical authority, a code of conduct, and independent implementations for 1.0. No unanimity rule.

**The CEP process.**

- A CEP is needed for a change to what a requirement, a schema or the contract data, a reason code, a renderer or tokenizer, or a normative rule in conformance/README.md means, and for a change to the process or governance. Editorial fixes, broken-case fixes, new cases for existing rules, implementation listings and tooling keep the issue-then-pull-request path.
- Types are Standards and Process.
- Stages are Idea, Proposal, Draft, Candidate and Final, each left with an artifact: a Discussion; a pull request with a champion; the specification text and generated cases on the branch; passing reports from two assemblers and an issue in each listed assembler that fails; the merge with a CHANGES.md bullet. A Process CEP goes from Draft to Final and adds no bullet. A CEP may also be Postponed, Rejected, Withdrawn, Dormant (no sponsor within 60 days, revivable) or Superseded.
- An author who is not a maintainer gets a maintainer as sponsor. A maintainer answers every new CEP within 14 days. A champion may hand a CEP on to another contributor.
- A maintainer moves to merge, close or postpone. The motion is announced in Discussions and a final comment period of 10 calendar days follows. Objections are answered in writing, and a change of substance restarts the period.
- A merged CEP is never edited. A later CEP supersedes it, and the index in proposals/README.md records both.
- A CEP takes its pull request's number. CEP-0001 and CEP-0002 take reserved numbers, which GitHub gave to issues.
- Independent implementations, by people other than the specification's authors, are a milestone for 1.0, not a gate on each CEP.

**Adopting it.** This CEP is decided by the process it describes. The Lead Maintainer moves to merge, announces a final comment period of 10 days in Discussions, answers each objection in writing, and decides. No other CEP moves past Proposal until this one is Final.

## Rationale and alternatives

Each part is taken from a process that has run for years, at the smallest size that does the job here.

| Part | From | Why here |
| --- | --- | --- |
| A proposal is a file in the repository, added by pull request | Rust RFCs, PEP 1, MCP SEPs | The record sits beside the text it changes, and review uses the tools contributors already use |
| Numbered by its pull request | MCP SEPs, OpenTelemetry's OTEPs | Pull request numbers are already unique, so no one hands out numbers |
| Stages left by an artifact, with a champion | TC39, WebAssembly phases | A stage is a fact anyone can check, not a meeting's mood; CWA's artifacts are generated cases and conformance reports |
| An issue in each implementation that fails | WHATWG | A change that implementations have not taken is visible, and each knows what to change |
| A motion to merge, close or postpone, then a final comment period | Rust RFCs | Everyone who watches gets the same notice and the same time to object |
| Objections answered in writing | RFC 7282 | A decision has to address what was raised, not count heads |
| A maintainer sponsor, and a deadline to answer | MCP SEPs, PEP 1 | No proposal from outside sits in silence |
| A merged proposal is never edited; a later one supersedes it | Rust RFCs, PEP 1, fullsend's decision records | The reasons for a decision stay as they were when it was made. All three allow small amendments afterwards; a CEP allows none, so there is no line to draw |
| Membership by individuals | MCP governance | A seat cannot be bought or reassigned by an employer |
| Two organizations approve, a cap on seats, one vote per organization | OpenTelemetry, PEP 13, W3C and CloudEvents | One organization cannot change the specification alone, fill the maintainer list, or outvote the rest |
| Independent implementations for 1.0 | W3C Process, RFC 7942 | Shows that someone else reads the text the same way, without stopping changes until such implementations exist |

Alternatives considered:

- **Keep issue, then pull request, for everything.** It has no notice period and no record of objections and their answers, and it leaves each decision about meaning to be made ad hoc.
- **Decision records alone**, as fullsend keeps them. They record what was decided but tie no stage to evidence that implementations can carry the change, which a specification with a conformance suite can show.
- **Require independent implementations for each CEP.** Every listed assembler is the specification author's today, so this would stop every change until independent assemblers exist. It is a milestone for 1.0 instead, and each CEP records who wrote the implementations it cites.
- **A unanimity rule.** Waiting for every member to approve leaves proposals in limbo; Rust's teams stopped requiring every member's sign-off in 2018 for that reason. Rough consensus with written answers keeps a dissenter's argument on the record without making every decision wait for every maintainer.
- **Release freezes, working groups, a steering committee, a foundation.** Each answers a problem this project does not yet have, and each would cost one maintainer time with nothing to show for it. GOVERNANCE.md lists them as later steps.
- **A shorter or longer final comment period.** Ten days, as Rust uses, spans a weekend and a working week in every time zone. CEPs are expected to be rare, so the cost is small.
- **Number CEP-0001 and CEP-0002 by their pull requests.** Either works. Reserved numbers make the bootstrap visible in the index, and GitHub's numbers 1 and 2 are issues, so no pull request can take them.

## Backward compatibility

Nothing in the specification changes: no requirement, schema, reason code, case, payload, trace or digest. SPEC.md keeps its date, and CHANGES.md gets no bullet.

Changes already merged are not revisited. Issue contextwindowarchitecture/contextwindowarchitecture#2 proposes a new claim in §1, which would change what §1 means, so under this process it becomes the Idea for a CEP. Issues that report a broken case or an editorial problem keep their path.

## Conformance cases

None. A Process CEP changes how the specification is changed, which no case can test.

## Reference implementations

None in the sense of RFC 7942. The process is carried out first by this CEP's own decision and then by CEP-0002, which follows it from Proposal.

## Security implications

The specification's behaviour does not change. The governance rules address a different risk: that one organization, by hiring or by numbers, comes to decide what the specification means for every implementation and application that relies on it. The two-organization approval, the employer cap and one vote per organization limit that once a second organization takes part. Two existing controls stay as they are: every commit carries a Developer Certificate of Origin sign-off, and CODEOWNERS names people, never automation, so no bot can approve its own changes to the specification.
