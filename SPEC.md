<!-- dte:A1,A2,A3,A4,A5,A6,B1,B2,B3,B4,B5,B7,B10,B11,B12,B13,B14,B15,B16 -->
# DTE Specification (v0)

This document is normative. Words in **bold** are defined terms. Each section
cites the decision it derives from; the decision file holds the rationale.

## 1. Premise

Every element of a project exists because a decision was made (dte:A2). Some
decisions are made by humans, some by AI, some jointly (dte:A3). DTE records the
decisions as a tree of **rings** and links every **artifact** to the decisions it
serves, so that the **blast radius** of changing any decision is knowable (dte:A1).

DTE is not a dependency graph. It records *why*, not *what calls what*
(dte:A4, dte:B9).

## 2. Vocabulary

- **Decision**: a choice that caused something to exist or be shaped a certain
  way. Recorded as a **node**.
- **Node**: one markdown file describing one decision (dte:B1).
- **Ring** (or **layer**): the depth of a node from the core. Ring 0 is `A`,
  ring 1 is `B`, and so on (dte:B2).
- **Core**: the `A` ring. The abstract goals of the project. Core nodes have no
  parents (dte:B10).
- **Parent**: a node this node exists *because of*. Parents are always in a
  strictly shallower ring (dte:B10).
- **Artifact**: any file in the project that is not a node: code, config,
  docs, tests, data.
- **Citation**: the token `dte:ID` placed in an artifact, meaning "this exists
  because of ID" (dte:B3).
- **Blast radius** of a node: every node that descends from it, every artifact
  that cites it or any descendant, and every node it currently supersedes
  (dte:C2).
- **Precedence**: when two active nodes contradict, the one in the shallower
  ring wins (dte:B4).
- **Provenance**: who made the decision: `human`, `ai`, or `joint` (dte:B7).
- **Human-held**: a node made by a human, or ratified by one (dte:B11).
- **Authority**: the ring an agent operates at. It decides at that ring or
  deeper and asks upward for anything shallower (dte:A6).
- **Inbox**: where a decision waits, without an ID, until someone with
  authority places it in a ring (dte:B14).
- **Summary**: the node's `title`, which always accompanies its ID when a
  model refers to it (dte:A5, dte:B16).

## 3. Identity and rings (dte:B2)

- An ID is one uppercase letter followed by a positive integer: `A1`, `B14`,
  `C3`. The letter is the ring. `A` is the core.
- Numbers within a ring are allocated upward and **never reused**, even after a
  node is moved or reverted. `dte next <ring>` gives the next free number.
- The ID appears in the frontmatter `id:` field and is the file name:
  `decisions/<ring>/<ID>.md`.
- A node **moved** to another ring receives a new ID in the destination ring.
  The old ID is kept in `aliases:` and continues to resolve. Tools warn on
  alias use so citations can be updated at leisure (see section 7).

## 4. Node format (dte:B1, dte:B7)

A node is a markdown file with YAML frontmatter. Only the subset of YAML shown
here is supported (dte:C1): scalars, inline lists `[a, b]`, and block lists.

```yaml
---
id: B3
title: Artifacts cite decisions with a dte: token
status: active            # proposed | active | superseded | reverted
parents: [A1, A2]         # required unless ring A; each must be shallower
supersedes: []            # nodes this one replaces (they become superseded)
superseded_by:            # set when status is superseded
conflicts_with: []        # active nodes this one contradicts (resolved by ring)
aliases: []               # former ids after a move
made_by: ai               # human | ai | joint
by: Claude Fable 5.1      # person or model, free text
date: 2026-09-02
ratified_by:              # human who confirmed an ai/joint decision (optional)
authorized_by:            # human who authorised retiring/moving a human-held node
confidence: high          # low | medium | high (optional)
---
```

`title` is the summary string (dte:A5). Write it as the decision in one
sentence, under 100 characters, so it can stand beside the ID in chat.

Body sections, in this order. Only **Decision** and **Why** are required.

```
## Decision
One or two sentences. The thing that was decided, stated so it can be cited.

## Why
The reasoning. What the parents demanded, what was traded off.

## Consequences
What this makes true for the rings below and for artifacts.

## Alternatives considered
Optional.

## History
Optional. One line per event: created, ratified, moved, superseded.
```

### Status semantics (dte:C5)

| status       | in effect?         | meaning                                             |
|--------------|--------------------|-----------------------------------------------------|
| `proposed`   | yes, provisionally | made but not yet confirmed. Children get a warning. |
| `active`     | yes                | the normal state.                                   |
| `superseded` | no                 | replaced by `superseded_by`. File is kept.          |
| `reverted`   | no                 | withdrawn with no replacement. File is kept.        |

## 5. Citations (dte:B3)

- Token: `dte:` immediately followed by one or more IDs separated by commas.
  Examples: `dte:B3`, `dte:B6,C1`. Case-sensitive. No spaces before the ID.
- Place it in a comment for code, or in prose or an HTML comment for docs.
  A file-level citation at the top says why the file exists. Line-level
  citations say why a specific block exists.
- Citing a node implicitly cites its whole ancestry. Cite the *most specific*
  node that explains the artifact. Citing an `A` node directly is allowed and
  means "this exists straight from the core goal".
- Citing an unknown ID is an error. Citing an alias is a warning.
- Nodes do not use citation tokens for lineage; they use `parents:`.

## 6. Rules

- **R1 (dte:B10)** Every non-core node has at least one parent. Core nodes have
  none. Every parent is in a strictly shallower ring.
- **R2 (dte:B4)** Two active nodes that contradict each other are resolved by
  ring: shallower wins. Two contradicting nodes in the *same* ring are an
  error; resolve by superseding one or moving one.
- **R3 (dte:B5)** Node files are never deleted. Superseding or reverting
  changes `status`; the ring is preserved as history.
- **R4 (dte:B5)** An active node whose parent is superseded or reverted is an
  **orphan**. Orphans are errors: re-parent, supersede, or revert them.
  This is how A1 is enforced: reverting a node forces its blast radius to be
  dealt with, not forgotten.
- **R5 (dte:B7)** Every node records `made_by` and `by`. AI-made nodes may be
  `active` without ratification so agents are not blocked, but tools surface
  every unratified AI node until a human sets `ratified_by`.
- **R6 (dte:A2)** The goal is total coverage: every artifact cites at least one
  node. Coverage below 100% is not an error (adoption is incremental, dte:C4)
  but it is always reported.
- **R7 (dte:B11)** A human-held node that is superseded, reverted, or moved
  must carry `authorized_by` naming a human. Off with `protect_human = off`.
- **R8 (dte:A6, dte:B15)** An agent never places or alters a node shallower
  than its ring. It writes the decision to the inbox and asks. With
  `--as <ring>`, validate enforces this on the agent's changed files.
- **R9 (dte:A5)** A model refers to a decision as `ID title`, never bare ID,
  unless `summaries = off`.

## 7. Operations

**Add a decision.** `dte next <ring>` for the ID. Write the node. Set parents.
Cite it from the artifacts it produces. Run `dte validate`.

**Supersede.** Create the new node with `supersedes: [OLD]`. Set the old node
to `status: superseded` and `superseded_by: NEW`. Run `dte blast OLD` before
you start and again after: every descendant of OLD is now an orphan until you
re-parent it to NEW (or to something else) or retire it.

**Revert.** Set `status: reverted`. Same orphan discipline as supersede, with
no replacement to re-parent to.

**Move (promote or demote).** Moving changes precedence (dte:A1, dte:B2).
1. `dte next <destination ring>` gives the new ID.
2. Rename the file, update `id:`, add the old ID to `aliases:`, append a
   History line.
3. Parents must still be strictly shallower. If you promoted past a parent,
   re-parent to that parent's parents or higher.
4. Children must still be strictly deeper. If you demoted below a child, move
   or re-parent the child.
5. Existing citations keep resolving through the alias. Update them when
   convenient.
6. Run `dte conflicts`: promotion means this node now wins contradictions it
   previously lost, and vice versa.

**Ratify.** A human sets `ratified_by:` on an AI or joint node, and flips
`proposed` to `active` if applicable. A ratified node is human-held from
then on (dte:B11).

**Escalate (dte:B14).** When a decision belongs above your ring, or you do
not know where it belongs, write `decisions/inbox/<slug>.md`:

```yaml
---
title: One-sentence statement of the decision
proposed_ring: B          # your best guess, or omit
ask: orchestrator         # who should place it; defaults to the ring's holder
made_by: ai
by: <model>
date: 2026-09-02
parents: [A1]             # candidate parents, optional
---
## Decision
## Why
```

Then say so in chat, with the title. Validate and tree print PENDING
PLACEMENT with the question to ask until it is placed.

**Place (dte:B14).** Someone with authority runs
`dte place <slug> <ring> --by <name> [--parents A1,B2]`. The tool allocates
the ID, writes the node into the ring with a History line, and removes the
inbox file. The placer is not thereby ratifying the content; `ratified_by`
stays empty until a human sets it.

**Authorise an override (dte:B11).** To retire or move a human-held node, a
human sets `authorized_by:` on it. An AI may prepare the change but the
field must name a person.

## 8. Blast radius (dte:C2)

For node X:

1. **Descendants**: every node with X (or an alias of X) in `parents`,
   transitively. Grouped by ring.
2. **Artifacts**: every file and line citing X or any descendant.
3. **Formerly superseded**: every node X supersedes. If X is reverted, those
   are candidates to come back.

`dte blast X` prints all three. Read it before changing X.

## 9. Relationship to graph engineering (dte:B9, dte:A4)

A structural graph (dependencies, call graph, data flow, module ownership)
answers "what is connected to what". DTE answers "why does this exist and who
decided". They are orthogonal axes over the same artifacts and they
cross-reference:

- An artifact appears in both. Its graph edges say what it touches; its
  citations say what it serves.
- A DTE node may name graph elements in its Consequences section. A graph
  element may carry a citation.
- DTE does not model structural edges, and a graph does not model precedence
  or provenance. Neither tool should grow to absorb the other.

## 10. Authority and agents (dte:A6, dte:B13, dte:B15)

Every agent has a ring. A spawning agent states it in the subagent's
instructions ("you operate at ring C"). The agent:

- makes decisions at its ring or deeper, and cites them;
- writes anything shallower, or of unclear ring, to the inbox and asks;
- runs `dte validate --as <ring>` before finishing, which fails if any node
  it changed is shallower than its ring or is human-held without
  `authorized_by`.

The advisory map in `dte.cfg` (`authority = A:human, B:orchestrator,
C+:subagent`) says who holds each ring, so "ask upward" has an addressee.
`dte authority` prints it. The map binds agents. It never binds humans, who
may decide at any ring; a human-made node is valid anywhere.

## 11. Configuration (dte:B12)

`dte.cfg` at the project root, `key = value` per line, `#` comments.

| key             | default | meaning                                      |
|-----------------|---------|----------------------------------------------|
| `summaries`     | `on`    | print `ID title`; `off` prints bare IDs (A5) |
| `protect_human` | `on`    | enforce R7 (B11)                             |
| `authority`     | none    | advisory ring-to-holder map (B13)            |

## 12. Tooling contract (dte:B6)

A conforming tool is a single file with no dependencies beyond the language
runtime, and implements at least: `validate` (with `--as`), `tree`, `blast`,
`trace`, `conflicts`, `coverage`, `next`, `inbox`, `place`, `authority`.
Every output that names a node prints `ID title` unless summaries are off.
The reference implementation is `tools/dte.py`. Exit code is non-zero when
`validate` finds errors.

## 13. Open questions (not yet decided)

- Whether a node may have a parent in a *deeper* ring for "supporting" links.
  Current answer: no; use Consequences prose.
- Rings beyond `Z`. Current answer: if you need 27 rings, the core is wrong.
- Whether citations should carry a reason string. Deferred.
- License for this repo. Owner's decision.
