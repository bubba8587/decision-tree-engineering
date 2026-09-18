---
name: threeLayers
title: DTE holds why, specs hold what, code holds how; each layer cites the one above and stores nothing from below
proposed_ring: A
ask: human
made_by: ai
by: Claude Fable 5.1
date: 2026-09-18
parents: []
confidence: medium
---

## Decision

DTE exists to help authors organize their projects into three separate layers: decisions, specs, and implementation.

The decision tree holds WHY, specs hold WHAT, and then the implementation (HOW) follows the spec.

The decision tree holds why: goals, rules, choices and their provenance. Specs hold what: what to build, generated from the tree and citing the nodes they serve; a choice a spec forces (a dependency, a format) is recorded as a deeper node first. Code and tests hold how, and cite the nodes the spec told them to. A layer cites upward and never stores anything from below: a node never lists its tests, specs or files; those lists are derived from citations at read time.

## Why

Stated by the owner on 2026-09-18 while walking the Solenoid feedback. Solenoid put "Enforced by: test" lines into nodes and the owner judged that a breach of scope: authored pointers downward go stale, and they pull test data into a document a human must keep readable. A test that cites the node is the same fact, kept where it can be checked. The same boundary answers the spec-tooling question in FEEDBACK.md #6: Spec Kit, Kiro and OpenSpec live in the middle layer, and DTE is the rationale layer under them, never a fourth spec format.

## Consequences

- dte.cfg gains `specs` and `tests` globs beside `docs`; `show` prints "specified by", "implemented by" and "enforced by" as derived lists; `coverage` reports in-effect nodes with no citing test. No `enforced_by` field (FEEDBACK.md K5, #1 declined).
- `dte spec <ID>` emits a spec skeleton from a node and its subtree for a tree agent to fill.
- Reverting a node's blast radius includes its specs and everything built to them.
