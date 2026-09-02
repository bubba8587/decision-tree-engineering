---
title: An agent may edit CLAUDE.md only to reflect a node that already exists; changing the protocol itself is human-held
proposed_ring: B
ask: human
made_by: ai
by: Claude Fable 5.1
date: 2026-09-02
parents: [A6, A3]
confidence: medium
---

## Decision

CLAUDE.md (and any file that instructs agents) is an artifact of the
protocol nodes it cites. An agent may edit it to mirror a node that is
already in the tree, citing that node. An agent may not introduce a rule
into it that has no node, and may not remove or weaken a rule whose node is
human-held. The protocol file is treated as human-held for those purposes.

## Why

The owner asked which decision permits an agent to update CLAUDE.md. Today
the answer is only "B8 says the protocol lives there, and the agent holds
ring B", which permits an agent to rewrite its own operating instructions
without any human seeing a decision. Self-modification of agent
instructions is the sharpest case of acting above one's authority (A6) and
should be visible as such (A3).

Proposed at ring B because it is a rule about an artifact. It could equally
be a clause of A6; the owner should say.

## Consequences

- Every rule in CLAUDE.md cites a node; the validator could check that the
  file cites at least one node per section.
- A protocol change starts with a node, not with an edit to CLAUDE.md.
