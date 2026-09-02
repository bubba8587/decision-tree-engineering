---
title: Agent-private memory is outside the tree and may hold only pointers to nodes, never project decisions of its own
proposed_ring: B
ask: human
made_by: ai
by: Claude Fable 5.1
date: 2026-09-02
parents: [A2, A6]
confidence: low
---

## Decision

An agent's private memory (Claude Code memory files, or any equivalent) is
not part of the project and is not scanned by the tool. It may record
pointers to nodes and personal working notes. Any rule about how work in
this project is done must exist as a node or as an inbox item; memory may
reference it but may not be its only home.

## Why

The owner asked what decision lets the agent update its memory. Nothing
does: memory is outside the tree. The concrete harm surfaced immediately:
the owner's instruction to ask questions in chat rather than through the
question dialog exists only in the agent's memory, invisible to the tree, to
other agents, and to `dte`. That is a project working rule held in a place
A2 cannot reach.

`confidence: low` because the alternative, declaring memory a project
artifact and scanning it, is also defensible and the owner may prefer it.
Also open: whether the "ask in chat" rule itself should become a node, and
at what ring.

## Consequences

- The existing memory entry for "ask in chat" should be mirrored into the
  tree if this is placed.
- CLAUDE.md gains a line: memory is not a substitute for a node.
