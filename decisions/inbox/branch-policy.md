---
title: Agents commit to develop; main only receives merges that validate clean; unratified count is reported at merge, never gates it
proposed_ring: B
ask: human
made_by: ai
by: Claude Fable 5.1
date: 2026-09-02
parents: [A7, A6]
confidence: medium
---

## Decision

Agents work on `develop`. `main` receives only merges from `develop` for
which `dte validate` passes with zero errors. The number of unratified
AI nodes is printed in the merge report and does not block the merge;
ratification happens on `develop` at the owner's pace, or on `main`
after, since ratification is a frontmatter change the tool makes.

## Why

The owner asked for `main` and `develop` on 2026-09-02. Which branch
agents commit to, where ratification happens, and what `main` requires
are decisions nobody has made, and A6 says an agent does not make them
above its ring. This is a proposal at ring B. A7 argues against gating
`main` on ratification: agents would stall on the owner's attention.

## Consequences

- `dte hook` on `main` would refuse a broken merge locally.
- C15 keeps IDs from colliding across the two branches.
