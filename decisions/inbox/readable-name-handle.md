---
title: A node may carry a readable name handle, unique across the tree, that citations may append after the ID
proposed_ring: B
ask: human
made_by: ai
by: Claude Fable 5.1
date: 2026-09-18
parents: [A5, A1]
confidence: low
---

## Decision

An optional `name` field (an identifier such as `shareImpl`, unique across the tree) is
a readable handle bound to one node. A citation may read `dte:C17 shareImpl` or
`[[C17]] shareImpl`; validate checks the pair against the node. `aliases` would be
written from `name` so `[[name]]` resolves in Obsidian. The ID stays the only identity.

## Why

FEEDBACK.md K4 and #10 (Solenoid adoption): a bare ID in a one-line code comment says
nothing to a reader without the tree open, and A5's "ID plus title" is for chat. Solenoid
runs this and reports it works. It contradicts B23 "No aliases; a move supersedes the old
node with a new ID and rewrites every reference at once", which is human-held and says
`aliases` is an error, so only the owner can decide it. The Solenoid code for it exists
in OBSIDIAN-VAULT.md and was deliberately left out of the port.

## Consequences

- If placed, B23 needs the owner's reword: a handle bound to one node is not a second identity.
