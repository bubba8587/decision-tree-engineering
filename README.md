<!-- dte:A1,A2,A3,A4 -->
# Decision Tree Engineering (DTE)

**Every thing in a project exists because a decision was made.** DTE makes that
lineage explicit, ring by ring, so that when a decision changes you know exactly
what it touches.

Think of a tree: the core is a handful of abstract goals (ring `A`). Each
ring outward is a layer of decisions made *because of* the ring inside it.
Code, config, docs and tests are the leaves and bark. Each one cites the
decision(s) it exists to serve.

DTE works **alongside** structural methods such as graph engineering. A
dependency graph tells you *what* touches *what*. The decision tree tells you
*why* any of it is there, and who decided.

## The one rule that matters (A1)

> If a decision is changed or reverted, it is possible to know exactly what
> layers that decision applies to and its blast radius. A decision can be moved
> up and down the hierarchy; a superseding or contradictory decision higher in
> the hierarchy always takes preference over one lower down.

Everything else in this repo descends from that. See `decisions/A/A1.md`.

## How it looks

```
decisions/
  A/A1.md      ring 0: core goals          (made by a human)
  B/B3.md      ring 1: "cite decisions with a dte: token"   parents: [A1, A2]
  C/C3.md      ring 2: "how the scanner finds citations"    parents: [B3]
tools/dte.py   # dte:B6,C3   <- code cites the decisions it serves
```

A decision node is a markdown file with frontmatter:

```yaml
---
id: B3
title: Artifacts cite decisions with a dte: token
status: active            # proposed | active | superseded | reverted
parents: [A1, A2]         # must be in shallower rings
made_by: ai               # human | ai | joint
by: Claude Fable 5.1
date: 2026-09-02
---
```

Any artifact cites a decision with the token `dte:ID` in a comment or in prose.

## Ask the tree

```
python tools/dte.py validate          # is the tree consistent?
python tools/dte.py tree              # print the whole tree, ring by ring
python tools/dte.py blast B3          # what would changing B3 touch?
python tools/dte.py trace tools/dte.py   # why does this file exist?
python tools/dte.py conflicts         # who wins each contradiction?
python tools/dte.py coverage          # which artifacts have no lineage yet?
python tools/dte.py next C            # next free id in ring C
```

The tool is one file with no dependencies (Python 3.8+). Copy it into any
project.

## Read next

- `SPEC.md` for the normative rules.
- `decisions/` for this repo's own tree. DTE is built with DTE.
- `ADOPTING.md` for bringing DTE into an existing project.
- `CLAUDE.md` for how AI agents are expected to behave in a DTE repo.

## Status

Day one. The A-ring is set (A1 by the project owner; A2 to A4 proposed and
awaiting ratification). Rings B and C describe the format and tooling. First
external target: Solenoid NGC.
