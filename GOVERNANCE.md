# Governance

Context Window Architecture has one maintainer today and is meant to become a community effort. This document says who decides, how a decision is made and where it is recorded, and which rules keep any one organization from steering the specification once more than one takes part. [proposals/README.md](proposals/README.md) says how a change to what the specification means is proposed and decided, and [CONTRIBUTING.md](CONTRIBUTING.md) says what every pull request needs.

[CEP-0001](proposals/0001-cep-process.md) adopted this document. It changes only through a Process CEP, except for the list of maintainers, which changes as Becoming a maintainer says, and for wording that changes no rule.

## Scope

This document governs the specification in this repository: SPEC.md, the schemas, the contract data, the conformance cases and their README, the examples, the guides and the proposals. The organization's other repositories, the assemblers, the assembler template, the website and the demo, take the specification at a commit they pin (README.md). They follow what is decided here; they are not governed by it.

## Roles

Every role is held by a person. No organization holds a seat, a vote or a role: a role stays with its holder when they change employer, and an employer cannot name a replacement.

**Contributors** are everyone who asks a question, reports a problem, reviews a change, opens a pull request or writes a proposal. No membership is needed. Each commit is signed off under the Developer Certificate of Origin (CONTRIBUTING.md); there is no contributor licence agreement.

**Maintainers** have write access to this repository. A maintainer:

- reviews pull requests, and squash-merges them as Decisions says;
- answers new Ideas and proposals within the deadlines in proposals/README.md, and sponsors proposals from authors who are not maintainers;
- moves and decides motions on proposals, as Decisions says;
- declares an affiliation and keeps it current.

**The Lead Maintainer** is a maintainer who also:

- decides, while every maintainer comes from one organization, what the maintainers do not settle by consensus, and posts the reasons;
- approves new maintainers while there is only one;
- calls votes, once a vote is possible (Votes);
- speaks for the project, for example to a foundation (Later steps).

When the Lead Maintainer steps down, or has not answered in Governance Discussions for 90 days, the maintainers choose a successor by consensus, or by a vote when consensus fails.

**Emeritus maintainers** are former maintainers, listed for credit. They keep no access, and one who returns does so as Becoming a maintainer says.

### Maintainers

| Name | GitHub | Role | Affiliation |
| --- | --- | --- | --- |
| Melvin Hillsman | [@mrhillsman](https://github.com/mrhillsman) | Lead Maintainer | _to be declared_ |

Emeritus: none yet.

### Affiliation

A maintainer's *organization* is the employer or other entity that pays them for their work on CWA, counted together with its parent and its subsidiaries, as W3C counts related Members as one. A contractor counts with the client that pays for the CWA work. A maintainer whom no one pays for CWA work is *independent* and counts as an organization of one, as CloudEvents counts a nonaffiliated individual. Each maintainer declares their affiliation in the table above and updates it within 30 days of a change. Anyone who believes a declared affiliation is wrong says so in Governance Discussions.

## Becoming a maintainer

1. **Contributions.** At least three months of sustained work on the specification, in any mix: reviews of others' pull requests, merged changes, conformance cases, a proposal carried to a decision, or an implementation listed in implementations/. The work keeps the repository's conventions: derived text written by `check.py`, cases written by their generators, a CHANGES.md bullet for each change to the specification.
2. **Nomination.** A maintainer nominates the contributor in a Discussion in the Governance category and says what they have done. Anyone may ask a maintainer to nominate them, themselves included. The nominee accepts in the Discussion and declares their affiliation.
3. **Decision.** The nomination stays open for 7 days. While there is one maintainer, the Lead Maintainer decides; after that, the maintainers decide as Decisions says. Once the employer cap is in effect, it must still hold after the addition.
4. **Record.** The decision is posted in the Discussion with its reasons, and a pull request adds the new maintainer to the table.

A maintainer may step back at any time, by a pull request that moves them to the emeritus list. A maintainer with no review, merge or comment in this repository for 12 months is asked in Governance Discussions whether they want to stay; with no answer within 30 days, another maintainer moves them to the emeritus list. A maintainer may be removed for conduct that harms the project, by the other maintainers as Decisions says; the outcome and its reasons are posted, and private details stay private.

## Decisions

**Pull requests.** A pull request merges once CI passes and a maintainer approves it. Once there are two or more maintainers, the approval comes from a maintainer other than the author. While there is one, that maintainer merges their own pull requests once CI passes. A change to what the specification means is a CEP, and it merges only as [proposals/README.md](proposals/README.md) says: after a motion and a final comment period.

**Consensus.** Maintainers decide by rough consensus, as RFC 7282 describes it: a question is settled when every objection has been answered in writing and the maintainers judge that none still standing shows the proposal is wrong. Objections are answered, not outvoted, and no decision needs every maintainer to agree. While every maintainer comes from one organization, the Lead Maintainer decides what consensus does not settle, and posts why.

**Votes.** A vote is a last resort, once maintainers come from two or more organizations, for a question consensus has not settled and that cannot wait. The Lead Maintainer, or any two maintainers from different organizations, can call one in a Governance Discussion. Only maintainers vote, one vote per organization (below). A vote stays open for 7 days, counts only when at least half of the organizations with maintainers cast one, and passes with more votes for than against. A tie changes nothing.

### Rules against capture

These rules are written now and take effect at the thresholds below. Each applies while its threshold holds, and the Lead Maintainer announces in Governance Discussions when one starts or stops.

| Rule | In effect while | After |
| --- | --- | --- |
| A change to what the specification means, and every Process CEP, needs approving reviews from maintainers of at least two organizations | maintainers come from two or more organizations | OpenTelemetry |
| No organization holds more than two in five maintainer seats | there are five or more maintainers | PEP 13 |
| One vote per organization | maintainers come from two or more organizations | W3C, CloudEvents |

- **Two organizations approve.** The author's own organization counts when the author is a maintainer. GitHub cannot check affiliations, so the maintainer who merges checks them against the table.
- **The employer cap.** Two in five is 40 percent of the seats, rounded down: two of five, six or seven maintainers, three of eight or nine. An organization at the cap adds no maintainer. When a change of affiliation puts one over it, its maintainers agree among themselves, within 60 days, which of them become emeritus until it holds.
- **One vote per organization.** The maintainers of one organization cast a single vote between them. An organization whose maintainers do not agree abstains.

### Records and venues

Every decision is made and recorded in public. A CEP's motion, objections, answers and outcome are on its pull request and in its announcement. Maintainer changes and votes are in Governance Discussions, and a change to this document is a Process CEP, recorded like any other. A decision reached in a call or a chat counts only once it is posted there with its reasons. Reports about a person's conduct are handled privately; the outcome is posted.

GitHub Discussions is the venue for everything that is not an issue or a pull request:

| Category | Used for |
| --- | --- |
| Q&A | Questions |
| Ideas | The Idea stage of a CEP, Process CEPs included |
| Announcements | Final comment periods and the decisions that end them, posted by maintainers |
| Governance | Nominations, votes and affiliation questions |

Issues report problems, and pull requests change files. No mailing list, chat or meeting is required, and none is a place where decisions are made.

`.github/CODEOWNERS` names maintainers, never bots, apps or automation accounts, and changes when the maintainer list does.

## Later steps

Each of these waits until the project needs it, and comes through a Process CEP:

- **Release freezes**: a cut-off for CEPs before a 1.0 or other stable release.
- **Working groups** for parts of the specification, once one area has more proposals than the maintainers can review.
- **More roles**, such as triagers or approvers below maintainers, once review load needs them.
- **A steering committee or a term for the Lead Maintainer**, once there are enough maintainers to fill one.
- **A foundation home** to hold the name, the domain and any funds, with funding and business decisions kept separate from technical authority, as the OpenAPI Initiative keeps them.
- **A code of conduct** with a private channel for reports.
- **Independent implementations**, a milestone for 1.0 that proposals/README.md describes.

Unanimity is not among them. No decision here waits for every maintainer to approve: Rust's teams stopped requiring every member's sign-off in 2018, because proposals sat waiting on one or two reviewers. An objection still has to be answered (Consensus), so dropping unanimity takes no one's argument away.
