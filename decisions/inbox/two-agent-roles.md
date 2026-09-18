---
name: twoAgentRoles
title: Tree agents decide and hold a ring; builder agents build to spec, hold no ring, and are denied the tree
proposed_ring: A
ask: human
made_by: ai
by: Claude Fable 5.1
date: 2026-09-18
parents: []
confidence: medium
---

## Decision

There are two kinds of agent. A tree agent holds a ring, reads the tree, records decisions, writes specs from nodes, and owes the one contest (B28) before building on an unratified node. A builder agent holds no ring and is denied the tree: it reads the spec, builds to it precisely, cites the nodes the spec names, and makes no decision. When the spec does not cover something, the builder stops and reports the gap to the spec's tree agent; it never improvises.

## Why

Stated by the owner on 2026-09-18: spec separation exists to unlock agent autonomy. A builder that reads the spec has no reason to question or contest anything in it, because every decision it embodies was settled before the spec was written. Denying the tree is what makes the builder special: it cannot be tempted by an unratified node it happened to read. A7 wants agents that never re-question what a node justifies; the strongest form is an agent that never sees the node. An import (FEEDBACK.md K2) produces nodes, not specs, so nothing is acted under and no contest is owed.

## Consequences

- `dte brief` gains a builder form: the spec, the citation rule, and how to report a gap; no binding nodes, no DTE_RING.
- B28 oneContest is reworded to bind tree agents only, before the first new work (a spec or a child node) under an unratified node.
- A spec gap is a new inbox kind, addressed to the spec's tree agent, distinct from a decision awaiting placement.
- CLAUDE.md is the tree-agent protocol; a builder gets its own instruction block.
