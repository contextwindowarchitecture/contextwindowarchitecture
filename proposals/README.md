# CWA Enhancement Proposals

A CWA Enhancement Proposal (CEP) is how a change to what the specification means is proposed, tested and decided. Each CEP is a Markdown file in this directory, added by a pull request and numbered by it. [CEP-0001](0001-cep-process.md) adopted this process, and [GOVERNANCE.md](../GOVERNANCE.md) says who the maintainers are and how they decide.

## When a CEP is needed

A change needs a CEP when it changes what one of these means, or adds or withdraws one:

- a requirement (R-n) in SPEC.md and contract/requirements.json;
- a schema in schema/, or the contract data a requirement reads, such as contract/slot-defaults.json;
- a reason code in contract/reasons.json;
- a published renderer or tokenizer;
- a normative rule in conformance/README.md: an ordering, tie-break, boundary or algorithm step, which R-21 makes normative;
- this process or GOVERNANCE.md, as a Process CEP.

These keep the path CONTRIBUTING.md describes, an issue first when the fix is not plain and then a pull request:

- an editorial fix: wording that changes no rule, a link, a typo;
- a broken case: a case, rejection or generator that does not match the rules as they are written;
- a new case that tests what the rules already say;
- an implementation listing, or a report imported again;
- a change to the checks or tools that changes no rule.

A change that settles a question the rules leave open, so that an implementation following another reasonable reading would now fail, changes what they mean and needs a CEP. When it is not plain which path applies, ask in the issue; a maintainer says which, and why.

## Types

- **Standards**: a change to what the specification means. It goes through every stage.
- **Process**: a change to this process or to GOVERNANCE.md. It goes from Draft to Final, since no case or assembler tests it, and it adds no CHANGES.md bullet, since CHANGES.md records the specification's revisions and dates SPEC.md.

## Stages

A CEP moves on when it has the artifact its stage asks for, not when a meeting agrees. The artifacts come from CWA's own conformance suite where one can show the change works.

| Stage | Where it is | To move on, it needs |
| --- | --- | --- |
| Idea | A Discussion in the Ideas category | A pull request adding the CEP file, with a champion named |
| Proposal | The pull request | The specification text and the cases that test it, generated on the branch |
| Draft | The pull request, with its text and cases | Passing conformance reports from at least two assemblers, and an issue in each listed assembler that fails |
| Candidate | The pull request, with its reports | A motion to merge, a final comment period, and the merge with a CHANGES.md bullet |
| Final | Merged | Nothing: the file is never edited again |

**Idea.** A Discussion in the Ideas category that states the problem, who it affects and the evidence: a snapshot, a trace, a benchmark result with its setup. It needs no solution yet. An issue that reports the problem serves as well, and either one is linked from the CEP. A maintainer answers within 14 days.

**Proposal.** A pull request that adds `proposals/0000-short-title.md`, copied from [0000-template.md](0000-template.md), with its preamble filled in, its Motivation written and its Specification at least outlined. Once the pull request has a number, the author renames the file to that number, zero-padded to four digits: pull request 42 adds `proposals/0042-short-title.md`. The preamble names a *champion*, who carries the CEP through its stages, usually the author. A maintainer labels the pull request `cep` and names a sponsor at triage (Owners).

**Draft.** The branch holds the change as it would merge: the edits to SPEC.md, the contract files, the schemas and conformance/README.md, and the cases and rejections that test it, written by generators in conformance/generators. `check.py` and the tests pass, and the CEP's Specification and Conformance cases sections describe what the branch holds. A Process CEP's branch holds the documents it changes.

**Candidate.** At least two assemblers, run against the branch's head commit, pass every published case and reject every published rejection, skipping only what Reporting results in conformance/README.md allows. Their reports are linked from the pull request. For each assembler listed in implementations/ that does not yet pass, an issue in its repository links the CEP and names the cases it fails. These reports are evidence for the decision and are not imported into implementations/: after the merge, each assembler runs the merged commit, and its report is imported as usual. When the branch's text, schemas or cases change after this, the reports are run again.

**Final.** A motion to merge has passed its final comment period (Decisions). The last commit on the branch sets the status to Final and, for a Standards CEP, adds a bullet to CHANGES.md that names the CEP. A maintainer squash-merges it.

A CEP can also end, or wait, in one of these:

- **Postponed**: a motion to postpone passed; the change is worth making, but not now. The pull request is closed, and a later motion can reopen it at the stage it had.
- **Rejected**: a motion to close passed. The pull request is closed, and the decision gives the reasons.
- **Withdrawn**: its champion withdrew it before Final. Anyone may take it up as its champion, under the same number.
- **Dormant**: no maintainer agreed to sponsor it within 60 days of its pull request opening. The pull request is closed and labelled `dormant`. It is revived, at the stage it had and under the same number, when a maintainer agrees to sponsor it.
- **Superseded**: a later CEP replaced a Final one. The index below records it; the earlier file is not edited.

## Owners

- **Authors** write the CEP.
- **The champion** carries it through its stages: answers review, keeps its status current and gathers the artifacts each stage needs. A champion may hand the CEP on: a contributor who agrees on its pull request becomes the champion, and the preamble names them.
- **The sponsor** is a maintainer who triages it, reviews it and moves the motion. Once there are two or more maintainers, a maintainer's own CEP has another maintainer as its sponsor.

No proposal waits in silence. Within 14 days of a pull request adding a CEP, a maintainer agrees to sponsor it, asks for changes, or says why no maintainer will sponsor it now. An author who has no answer by then asks in Governance Discussions, and the Lead Maintainer answers within 7 days. A CEP still without a sponsor 60 days after its pull request opened becomes Dormant.

## Decisions

**The motion.** A maintainer, normally the sponsor, moves on the pull request for one disposition:

- **merge**, once a Standards CEP is a Candidate or a Process CEP is a Draft;
- **close**, at any stage, which makes it Rejected;
- **postpone**, at any stage.

The motion summarizes the discussion and lists every objection raised so far, each with its written answer.

**The final comment period.** The sponsor announces the motion in the Announcements category of Discussions, with its disposition, a link and the date the period ends, and labels the pull request `fcp`. The period lasts 10 calendar days, as Rust's does. Anyone may comment, on the pull request or on the announcement.

**Objections are answered, not outvoted.** An objection raised during the period is answered in writing on the pull request (RFC 7282). When the answer changes the substance of the proposal, the period starts again; otherwise the objection and its answer join the motion's list and the period runs on. A CEP can be decided with an objection still standing, but only once that objection has been answered, and the decision says why it does not prevail. A change of wording alone does not restart the period.

**The decision.** When the period ends, the maintainers decide as GOVERNANCE.md says: while every maintainer comes from one organization, the Lead Maintainer decides what consensus does not; once maintainers come from two or more, a merge also needs approving reviews from maintainers of two organizations. The decision and its reasons are posted on the pull request and in the announcement. No decision needs every maintainer to agree, and a vote is GOVERNANCE.md's last resort, not part of this process.

## Records

A merged CEP file is never edited again, not to fix a typo and not to mark it superseded. A later CEP that changes the decision supersedes it: it names the earlier CEP in its preamble, and the index below records both. Rust's RFCs, PEPs and fullsend's decision records are kept the same way, though each allows small amendments; a CEP allows none. The specification's own text keeps changing as later CEPs and editorial fixes land; a CEP records what was decided, on what evidence, and why. Its pull request and its announcement hold the rest of the record: the motion, the objections, their answers and the outcome. A CEP that never merges is recorded by its closed pull request and its row in the index.

## Numbers

A CEP's number is the number of the pull request that adds it, zero-padded to four digits, so no registry hands out numbers. 0000 is the template. CEP-0001 and CEP-0002 were numbered by hand when the process began; GitHub gave numbers 1 and 2 to issues, so no pull request will take them.

## Independent implementations: a milestone for 1.0

Every assembler listed today, in Python, TypeScript, Go and Rust, was written by the specification's author. Two passing reports at Candidate therefore show that the change can be implemented and that its cases are consistent, not that someone else reads the text the same way. W3C asks for independent implementations before a Recommendation, and RFC 7942 has an Internet-Draft record who implemented it. For CWA, independent implementations, written and maintained by people other than the specification's authors from its text and cases, are a milestone for 1.0: before a 1.0 release, at least two independent assemblers pass every published case. They are not a gate on each CEP, which would hold every change until such assemblers exist. Each CEP's Reference implementations section says who wrote each implementation it cites, so the record shows how independent its evidence was.

## Index

| CEP | Title | Type | Status |
| --- | --- | --- | --- |
| [0001](0001-cep-process.md) | The CEP process and project governance | Process | Draft |
