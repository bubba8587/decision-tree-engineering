# DTE feedback — from using DTE as a reference elsewhere

External-user feedback on DTE, captured while formalizing specs in another repo
(Solenoid, which has its own mature prose rule system in `docs/rules.md` +
`docs/decisions.md`). Each entry: what was observed, why it matters, a suggestion.
Unverified against DTE's latest tool behavior — some may already be handled; those
are phrased as "confirm". Newest first. Not a DTE decision node (kept out of the
scanner via `.dteignore`); triage into `decisions/inbox/` or the tree as you see fit.

---

## 2026-09-15b — converting Solenoid's rule corpus (~150 rules and decisions) into the tree

Each item was checked against SPEC, PROTOCOL (CLAUDE.md), ADOPTING and README, and against
`tools/dte.py`, before filing. Where Solenoid overrode DTE, the override is recorded in its
B8 node.

**K1. [gap] No way to import an existing rule corpus.** Solenoid had 81 named rules and ~60
logged decisions in prose. `dte new` takes the body as `--decision/--why/--consequences`
arguments only (no `--body-file`, no batch import), so 150 multi-paragraph bodies with
backticks, quotes and tables went through a Python subprocess wrapper to survive shell
quoting on Windows. *Suggestion:* `dte new ... --body-file NODE.md` (sections parsed from the
file) and/or `dte import spec.json` that creates many nodes in parent-first order, allocating
IDs and resolving parents by title or key within the batch.

**K2. [protocol gap] B28's contest has no answer for an import.** B28 says an unratified
node gets one contest before an agent first acts under it. Lifting 150 existing rules makes
every lifted C node the parent of lifted D nodes in the same run, so a literal reading
demands ~60 contests whose alternatives were never on the table: the rules already existed
and were only being re-homed. Solenoid overrode it (import is not acting under; a lifted
node's contest happens when later work first builds on it). *Suggestion:* an `imported`
provenance or a `--imported` flag on `new` that marks the node as re-homed existing
content, with B28 applying from the first NEW work under it.

**K3. [bug] `retire --superseded-by` copies the loser's contest into the winner but does not
mark the winner contested.** B4's contest chose the variant; `retire B4 --superseded-by B8`
appended "Carried from B4, which this node supersedes. ### Contest ... variant wins" to B8's
Alternatives, yet `validate` listed B8 as `(ai, unratified)` with no `contested`, so the
protocol asked for a second contest of the node that WAS the contest's answer. *Suggestion:*
when the successor is the recorded winner of the retired node's contest, set its
`contested_by` from that contest (or have `contest --record` for a non-keep verdict create
the winner and retire the loser in one step).

**K4. [gap, overridden] No human-readable handle; B23's no-alias rule costs readability in
code.** Solenoid's code, tests and docs had cited rules by camelCase name (`per shareImpl`)
for months; a bare `dte:C17` in a comment says nothing to a reader without the tree open,
and A5's "ID plus title" is for chat, not for a one-line comment. Solenoid kept the name as a
title prefix (`shareImpl: One implementation, two surfaces`) and lets a citation carry it
(`dte:C17 shareImpl`), with its own test failing when a pair disagrees with the node's
title. *Suggestion:* an optional `name:` frontmatter field (unique, validated), `find`/`show`
by name, and `validate` checking `dte:ID name` pairs. It is a handle bound to one node, not
a second identity, so B23's concern (aliases drifting) is met by the check.

**K5. [gap, concrete repeat of #1] Enforcement is still prose.** Solenoid now writes
`*Enforced by:* file.test.ts → "test name"` into Consequences and runs its own suite that
fails when a MUST node lacks the line, a cited suite is missing, or a quoted test name is not
in the suite (found a real stale citation on first run). *Suggestion:* a structured
`enforced_by:` list and a `validate` check that each named file exists; `coverage` could report
active MUST-style nodes with no enforcement.

**K6. [gap] A prose example of a citation is itself a citation.** `CITE_RE` matches
`dte:C12` inside a backtick code span, so writing an example like "a citation may read
`dte:C12 shareImpl`" in the adopter's own docs failed `validate` with "citation to unknown id".
DTE's own docs avoid it by citing real IDs, and dte-rules/ is ignored wholesale. *Suggestion:*
skip tokens inside inline code spans, or document an escape (`dte:&lt;ID&gt;`) in SPEC § 5.

**K7. [ergonomics] `validate` at 150 nodes prints ~300 lines per run.** Every run lists every
unratified node (151 here) plus a "no children and no citing artifacts" warning per leaf, so
the one line that matters (`0 errors ... OK`) scrolls away, and an agent's context fills with
the same list each check. There is no `--quiet`/`--summary`. *Suggestion:* a `--summary`
flag (counts, errors, and the nodes changed in this working tree), with the full unratified
list behind `dte unratified`.

**K8. [bug, from reading `cmd_cite`] `cite` appends to ANY citation in a file's first three
lines, including a line-level one.** It scans `lines[at:at+3]` with `CITE_RE` and merges the
new IDs into the first match. A file whose second line is a comment like
`// headless (dte:D19 implReteFree, enforced by ...)` gets `dte:D19,C17 implReteFree`: the
file-level citation lands inside a sentence about one block, and the readable name now sits
after the wrong list. Solenoid sidestepped it with its own citer that only merges into a line
holding nothing but the citation. *Suggestion:* merge only into a line whose whole content is
the comment marker plus `dte:IDs`; otherwise insert a new line.

**K9. [scope gap] A process decision can never have reach.** SPEC § 12: "no reach" is a
non-core node with no descendants and no implementing artifact, and describing documents
(the `docs` globs, default `*.md, docs/*`) do not count. Solenoid's process nodes (branch
model, comment minimalism, "exceptions live under the rule", "spec-first for new
mechanisms") govern how agents work; what implements them is agent instructions (CLAUDE.md),
a CI workflow, or reviewers' behaviour. CLAUDE.md is `*.md`, so it cannot count; citing
from a CI YAML file just to satisfy `scope` touches a pipeline for a comment. They sit in
the no-reach list permanently next to real dead nodes, which dilutes the signal. *Suggestion:*
count agent-instruction files (the files B18 already names: CLAUDE.md and its kin) as
implementing artifacts for the nodes they cite, or let a node declare `kind: process` so
`scope` reports it separately.

---

## 2026-09-15 — Solenoid ring-A review with the owner

**J5. [tooling, owner-invited] A `dte rules` command that loads DTE's own rule text,
so an agent never works from a partial copy.** Observed: Solenoid vendored SPEC,
CLAUDE.md (as PROTOCOL) and README but not ADOPTING, which holds the ring-A guidance
("sit with the owner… goals, not features"). The agent then made a ring-A mistake that
text covers, and filed feedback blaming DTE for the gap. CLAUDE.md says only "Read SPEC.md
once"; `brief` hands a subagent the ring rules and binding nodes but none of SPEC or
ADOPTING. Hand-vendoring is the weak link: which files, and whether they are current, is
up to the adopter. The fault was the agent's, but the tool can make it hard to repeat.
*Suggestion:*
- `dte rules [--for adopt|work|subagent]` prints, in reading order, the canonical text
  an agent needs for that job: work = CLAUDE protocol + SPEC; adopt = + ADOPTING;
  subagent = brief + the SPEC sections the brief cites. Text embedded in `dte.py` itself
  (still one stdlib file, B6), so a copied tool always carries its matching rules and
  version.
- `dte rules --check <dir>` compares vendored copies against the embedded text and names
  missing or stale files (Solenoid's `dte-rules/` would have failed on ADOPTING).
- `brief` ends with "run `dte rules --for subagent` first", and `init` writes the
  agent-instructions pointer to `dte rules` instead of telling adopters to copy prose (I5).
- Feedback discipline: CLAUDE.md could say "before reporting a DTE gap, `dte find` the
  topic in the rule text" (`find` already searches nodes; extend it to the embedded docs).

**J4. [contradiction, checked against SPEC + ADOPTING] Reconstructed decisions are told
to be `made_by: human`, which makes an agent's guess human-held.** ADOPTING "Growing the
tree" says a decision nobody remembers gets `made_by: human`, `by: unknown
(reconstructed)`, `confidence: low`. SPEC §2 defines human-held as "a node made by a
human", and R7/B11 then bar any agent from superseding, reverting or moving it without a
human's `authorized_by`. So the inference an agent writes during adoption becomes locked
against the agent that must keep refining it, and its provenance claims a human decided
what nobody remembers. It also clashes with adopters who already rule that a past owner
statement is evidence, not a ruling (Solenoid's `authorRuled`). *Suggestion:* reconstructed
nodes are `made_by: ai` (or a distinct `reconstructed` provenance), unratified, low
confidence; the owner's ratification makes them human-held, as for any AI node.

**J2. [gap] No way to say one sibling refines or carves out another.** Solenoid B5
(Excel parity) and B6 (deliberate divergences from Excel: units, typed values) live in
the same ring. B6 is exactly the exception list for B5, but SPEC R2 makes a same-ring
contradiction an error and precedence is only by ring. Worked around by wording B5 as
"divergences are documented" so they don't contradict. *Suggestion:* a `refines:` /
`carves_out:` link, or SPEC guidance that a designed exception is written into the
general node's Decision rather than left as a contradiction.

**J3. [minor] Hand body edits leave no History line.** `set` records title changes, but
rewording a node's Decision/Why (allowed, since only frontmatter is tool-owned) records
nothing, so a ratifier can't see the node changed after drafting. *Suggestion:* validate
notes "body changed in this working tree" next to the changed-nodes list, or a `dte
reword` that appends History.

---

## 2026-09-14 — integration attempt in Solenoid (live adoption)

Adopting DTE into Solenoid (a large React/TS + Tauri app) as a real test case.

**I1. [bug, adoption-blocking] The vendored `tools/dte.py` carries `dte:` tokens to
DTE's OWN tree, so `validate` FAILS immediately after `init`.** ADOPTING.md step 1
("copy `tools/dte.py` into the project") plus step 3 ("`validate` should pass with zero
citations") are contradictory as written: the copied tool file is dogfooded with ~87
`dte:B6,C1,...` comment tokens that don't exist in the adopting repo → 87 "citation to
unknown id" errors, exit 1. *Fix:* `dte init` should add the tool's own filename to the
generated `.dteignore` (DTE already does exactly this for `WALKTHROUGH.md`, with the
rationale "its dte: tokens belong to that tree, not this one"), or the scanner should
always skip the file it is executing from. Worked around by adding `tools/dte.py` to
`.dteignore`.

**I2. [tension] The agent protocol forbids what adoption requires (ring A).** `CLAUDE.md`
says "Do not add to ring A. Inbox it and ask", but `ADOPTING.md` step 2 tells the adopter
to `dte new A ...` for the core goals. An agent doing a "go all out" adoption must create
ring A to bootstrap the tree. *Suggestion:* a documented bootstrap exception (e.g. `dte
init --owner` opens A-creation, or ADOPTING states A-creation is owner-authorized and the
agent may draft A as `made_by: ai` unratified for the owner to ratify). Here the owner
said "go all out", so A1–A4 were drafted `made_by: ai, unratified` for ratification.
*Sharper, observed:* `validate --as B` then HARD-FAILS with `ERROR A1: changed by an
agent at ring B but lives at ring A; escalate to human` (x4) — even though the owner
explicitly authorized the adoption. Two concrete asks: (a) there is no command to record
the owner's go-ahead on an EXISTING node — `set` only writes `title`/`confidence`, so an
agent cannot mark an already-created node `authorized_by` after the human says yes; add
`dte authorize <ID> --by <human>` (or let `set` write `authorized_by`). (b) The error is
working-tree-diff based ("changed in this working tree"), so it appears to CLEAR once the
nodes are committed (the A drafts then just sit in the unratified list for the owner) — if
that's the intended adoption flow (agent drafts A → commits → owner ratifies), ADOPTING
should say so, because `validate --as <ring>` failing mid-adoption reads as "you did it
wrong" when the protocol required it.

**I4. [gap, and possibly a headline value prop] DTE never says to REPLACE explanatory
comments with citations — it treats citations as purely additive.** Every mention of
comments in README/SPEC/ADOPTING/CLAUDE is about *where the `dte:ID` token sits* ("in a
comment or in prose"); nothing guides moving a comment's WHY into the node's `## Why` and
replacing the comment with the citation. But that is arguably the biggest payoff: a
WHY-comment is a decision's rationale living in the wrong place — it drifts, duplicates,
and can silently contradict the decision. Migrating it into the node (one home, A5-style)
and leaving a stable `dte:ID` behind is exactly what DTE is *for*.
*Distinction to state:* HOW/what comments (explaining mechanics, gotchas, non-obvious
control flow) stay; WHY comments (rationale, "we do X because…") migrate to a node and
collapse to a citation. *Suggestions:* (a) say this explicitly in ADOPTING ("Growing the
tree") and CLAUDE.md; (b) a tool affordance like `dte cite --replace <file> <ID>` (or a
`--from-comment`) that removes the rationale comment as it inserts the citation, so the
migration is one command; (c) a `scope`/report that flags files heavy in prose comments
but light in citations as migration candidates. Raised by the Solenoid owner, whose repo
already runs a "comments are last-resort, default is deletion" rule (`commentMinimalism`)
— DTE citations are the missing third home (not code, not a comment) that makes that rule
reach the WHY, so the two are a natural fit.

**I5. [guidance invites duplication] ADOPTING says "put the protocol from CLAUDE.md into
the project's agent instructions" — which led the agent to RE-AUTHOR DTE's protocol as
prose in the adopting repo, and to create a Solenoid node (C4) for a DTE-usage rule.** The
owner's intent is the opposite: a *copy of DTE's own rule files* (SPEC.md, CLAUDE.md, and
the B/C decision text) lives vendored in the adopting repo so agents load the real text
into context, and the adopter does NOT duplicate DTE-specific decisions in its own tree.
The adopter's tree holds only its OWN domain decisions (e.g. "Solenoid adopts DTE" and
the app's subsystems); DTE's format/protocol/usage rules stay DTE's, referenced not
copied-as-nodes. *Suggestions:* (a) reword ADOPTING to "vendor DTE's SPEC.md + CLAUDE.md
(and B/C rules) into the project and point your agent instructions at them", not "put the
protocol into your instructions"; (b) state explicitly that DTE-specific decisions are
never re-created as nodes in the adopting repo — only the adopter's own decisions are;
(c) maybe an `dte vendor-rules <dir>` command that copies the canonical rule files in and
`.dteignore`s them (their `dte:` tokens are DTE's tree, cf. I1). Corrected in Solenoid by
retiring C4 and reducing docs/dte.md to Solenoid-specifics + pointers to vendored copies.

**I3. [minor] Day-one leaves every A node WARNING "in effect but has no children and no
citing artifacts".** Correct long-term, but on a fresh adoption ALL goals trip it at once
(coverage is 0 by design per A4/B22). Consider suppressing this warning for nodes younger
than the first citation, or a `--adopting` mode, so the day-one `validate` isn't all
warnings.

---

## 2026-09-14 — first pass, comparing DTE to Solenoid's `rules.md`

**1. [gap] DTE tracks WHY a decision exists, not WHETHER it still holds.**
Solenoid pairs every rule with `Enforced by: <test that fails when the rule is
violated>`, or an explicit `UNENFORCED` marked as *debt, not decoration*. DTE's
`validate` checks the tree's structural integrity (parents strictly shallower,
citations resolve, one ratified root) — but nothing checks that the codebase still
*obeys* an `active` decision. A node can be `active` and silently violated by drift.
*Suggestion:* an optional `enforced_by:` frontmatter field (a test id / command) plus
a `coverage`-style report of active nodes with no enforcement. This is the single
biggest gap vs. a behavioral rule system: DTE knows the intent, not the compliance.

**2. [refinement] `## Why` conflates the forcing incident with the rationale.**
Solenoid separates `Origin:` (the concrete incident that produced the rule — "rules
with an incident are load-bearing; rules invented without one tend to be someone's
taste") from the reasoning. DTE's `## Why` holds both.
*Suggestion:* a convention (or optional field) marking whether a decision was forced
by a concrete incident vs. preventive judgment. This directly strengthens the contest
mechanism — a node with no forcing incident is a stronger contest/deletion candidate.
(Compare Solenoid's provenance grades: INFERRED = has a named incident, DEFAULT =
preventive judgment with none, and "DEFAULT is the thinnest ice.")

**3. [confirm] Does `validate` flag a `dte:ID` token that points at a retired or
superseded node?**
`blast` walks decision→artifacts and the survey says validate checks "citations
resolve" — but does it reject a citation that resolves to a `retired`/`superseded`
node (a stale link), not just a missing id? If not, that's a drift hole: code keeps
citing a decision that no longer stands. (Solenoid's analogue: `uniqueNameMap` makes
the name function total AND injective — every reference resolves to exactly one live
target.)

**Meta observation (not a problem):** DTE and Solenoid's `rules.md` are the same idea
at different maturities — rings A/B/C ≈ decisions→rules→invariants; `ratified_by` ≈
Solenoid's single `[ARR]` author-ruled mark; `dte:ID` ≈ "cite the rule name". The
pieces DTE has that Solenoid lacks (structured provenance frontmatter, blast/trace
queries, the contest) are the strongest argument for Solenoid eventually adopting DTE
rather than growing more prose. The piece Solenoid has that DTE lacks is #1 above.

## 2026-09-16 (Solenoid, Claude Fable 5.1)

**4. [bug] `show` crashes on Windows when a node body holds a non-cp1252 character.**
`python tools/dte.py show D42` dies with `UnicodeEncodeError: 'charmap' codec can't encode
character '→'` at `cmd_show`'s `print`. Any `→` / `↔` in a `## Consequences` line
kills the command under PowerShell's default stdout encoding. `validate` survives because
it prints only titles. Workaround: `PYTHONIOENCODING=utf-8`. Fix: `sys.stdout.reconfigure
(encoding="utf-8", errors="replace")` at startup, or `print(..., errors="replace")`.

## 2026-09-17 (Solenoid, Claude Fable 5.1)

**5. [patch, applied in Solenoid's vendored copy] Wikilink citations and link fields, for Obsidian.**
The owner asked for the Solenoid tree to be manageable from Obsidian. Obsidian follows `[[ID]]`
by filename across a vault and reads wikilinks inside frontmatter properties, so the tree's
lineage becomes graph-view edges and backlinks for free, but only if the node files and
citations use that syntax. `dte:ID` is opaque to it. Solenoid's `tools/dte.py` (byte-identical
to this repo's before the patch) now:
- reads both forms everywhere: `CITE_RE` (the token) plus `LINK_RE` (`[[ID]]`, `[[ID|alias]]`),
  joined by `cited_ids(line)`; `_scalar` unwraps `"[[B7]]"` in a link field to `B7`;
- writes per a new `dte.cfg` key `links = token | wikilink` (default `token`, so this repo's
  tree is untouched): `fm_id`/`fm_ids` for `parents`, `supersedes`, `superseded_by`,
  `conflicts_with`; `cite_text` for `cite`, `new` and `place` output; `sub_citations` for
  `retire`/`move` rewrites in either form; `cite` appends to an existing wikilink line.
- Your `tests/test_dte.py` passes unchanged against the patched file (74 tests). Diff it:
  `solenoid/tools/dte.py` vs `DTE/tools/dte.py`. Solenoid records it as C81 "wikilinkCitations".
Two things you may want to decide here rather than let a downstream config settle:
- `[[ID]]` is not CommonMark; GitHub renders it as literal text. A third value, `links =
  markdown`, writing `[C41](../C/C41.md)`, would render everywhere (GitHub, MADR viewers) and
  Obsidian follows it too, at the cost of noisier citations in code comments. Cheap to add.
- SPEC §5 says "Nodes do not use citation tokens for lineage". Wikilinks in a node's prose
  (Solenoid links `[[B7]]` in a Why) are not lineage, but a scanner that ever walks the
  decisions dir would count them; the rule text should say so.

**6. [positioning] Where DTE sits against the spec standards already out there.**
The owner's framing: DTE is not *the* spec, it is one part of spec-driven development. What
exists, and the fit:
- **ADR / MADR** (Nygard 2011; MADR 4.x) is the nearest standard and DTE is a superset of it.
  MADR's fields map one to one: Context ↔ Why, Decision Outcome ↔ Decision, Considered
  Options ↔ Alternatives considered, `status: superseded by` ↔ `superseded_by`. MADR 4 added a
  **Confirmation** section ("how compliance with this decision is confirmed"), which is exactly
  gap #1 above (Solenoid's *Enforced by:* line). What DTE adds that ADR lacks: rings and
  precedence, `parents` as a real graph, made_by/ratified_by provenance, blast radius, the
  contest, the ledger. What ADR has that DTE lacks: an ecosystem (adr-tools, log4brains,
  adr-viewer) that renders a folder of records. *Suggestion:* keep DTE's headings but declare
  the MADR mapping in SPEC, and let `export` emit MADR-shaped files so those viewers work on a
  DTE tree unchanged. Cheapest possible interop.
- **RFC 2119 / BCP 14** (MUST, SHOULD, MAY) is the standard vocabulary for the *rule* kind of
  node. Solenoid's rule nodes already write **MUST** in Decision and a test keys the
  enforcement label off it. Worth adopting as a convention in SPEC §4: a Decision using a
  BCP 14 keyword is a rule and carries Confirmation/Enforced-by; one that does not is a choice.
- **Spec-driven development toolchains** (GitHub Spec Kit: constitution + spec/plan/tasks per
  feature; AWS Kiro: requirements in EARS syntax + design + tasks; OpenSpec: specs plus change
  proposals with delta specs, archived on merge) specify *what to build* for one feature and
  are consumed at build time. DTE records *why*, per decision, and outlives the feature. They
  are complementary, and the seams are clean: Spec Kit's `constitution.md` is ring A/B in
  prose (a `dte brief` could generate it); a Kiro/Spec Kit requirement should cite the node it
  serves; an OpenSpec change proposal is an inbox item whose merge produces nodes. *Suggestion:*
  ADOPTING.md gets a short "beside Spec Kit / Kiro / OpenSpec" section saying exactly that,
  so a reader who already runs one of them sees DTE as the rationale layer under it, not a
  fourth spec format.
- **arc42 §9 "Design Decisions"** and **C4** both defer to ADRs for rationale; a DTE tree is a
  valid filling for that section. **ReqIF / traceability matrices** are what `blast` and
  `trace` compute over rationale instead of requirements; no need to adopt the format, but the
  word "traceability" would help people find DTE.
- **Obsidian** specifically: properties with wikilinks (Obsidian 1.4+) make `parents` a typed
  link list; Bases (1.9+) or Dataview can table the tree (`status`, `ring`, `ratified_by`)
  without a plugin. Code-side citations stay invisible to Obsidian (it indexes markdown only),
  which is fine: they are for the tool, and node/doc-side links are for the human.

**7. [bug, fixed in Solenoid's vendored copy] Node titles are written as unquoted YAML, which is
invalid whenever the title holds `: ` (or ` #`).** Solenoid's `name: summary` title convention
put a colon-space in 157 of 169 titles; the tool's subset parser splits on the first colon and
never noticed, but Obsidian (and any real YAML parser) rejects the whole frontmatter and shows
every property as invalid. Fix in the vendored tool: `fm_str()` double-quotes the title (escaping
`\` and `"`) in `new`, `place` and `set`, and `_scalar` unescapes double- and single-quoted
scalars on read. Every existing title was requoted in place. Your
`test_set_writes_whitelisted_fields_and_guards_human_held` asserts the unquoted spelling
(`title: A new title`) and is the one upstream test the patched file fails; the other 73 pass.
Suggest quoting `by`, `ratified_by` and `authorized_by` the same way, since a name can hold a
colon too.

**8. [direction] Meeting Obsidian halfway: what the tool could do beyond wikilinks.**
Written up for the owner in Solenoid; the DTE-facing parts:
- Obsidian re-serialises the whole frontmatter on any property edit: inline lists become block
  lists (already parsed), empty fields can become `null`, keys reorder. `_scalar` should read
  `null` and `~` as empty, or the first property edit in Obsidian breaks validate.
- `aliases`, `tags`, `cssclasses` are Obsidian's own keys and should be known fields. Better:
  write `aliases` from the title's `name:` prefix and `tags` from ring/status at write time, so
  `[[name]]` resolves and the tag pane becomes a ring browser.
- `ratified_by` typed into the Properties pane is the human act DTE wants; B29 "frontmatter is
  never hand-edited" binds agents, so validate accepting a human-typed `ratified_by` costs
  nothing and removes a CLI step from the one person who must do it.
- `dte export --obsidian`: a `.base` file with the unratified / contested / inbox views, a
  JSON Canvas per ring or per `blast`, and one note per node listing its citing files, since
  Obsidian indexes markdown only and code citations never appear as backlinks.
- The ledger `RETIRED` has no extension and is invisible to Obsidian; `RETIRED.md` as a table
  keeps burned numbers browsable and linkable.

**9. [built in Solenoid's vendored copy] The outbox: the human-to-agent channel, and what it
took.** Solenoid records it as C82 "vaultOutbox". `dte outbox` lists (a) notes in
`decisions/outbox/` (frontmatter optional; title from it, the first heading, or the file name),
(b) nodes tagged `ratify`, `retire`, `contest` or `ask` in a `tags` property or inline `#ask` etc. (flat tags; the owner ruled out nested ones), with a fixed
vocabulary ratify / retire / contest / ask and the exact command for each, (c) a `ratified_by`
present with no "ratified by" History line, i.e. typed into Obsidian's Properties pane. Not
bare diffs: the owner's call, since an anonymous edit cannot be told from an agent's own
unfinished work and validate's "Nodes changed" list already covers it. `dte outbox --done <ID|slug>` deletes the note or strips
the action tags (inline and list, block or inline form). `validate` prints `OUTBOX (n)` so an
agent cannot miss it. The inbox is your agent-to-human direction; this is the other one, and
it needs no watcher or plugin because tags and a folder are what Obsidian makes cheap and git
already knows what changed.
Changes to the tool that came with it, each a deliberate divergence you may want upstream:
- `null` / `~` read as empty (Obsidian writes an emptied property as `null`); dot-directories
  under `decisions/` are skipped (`.obsidian`).
- `aliases`, `tags`, `cssclasses` are known fields. `aliases` is written from the title's
  `name:` prefix so `[[name]]` resolves in the vault; `resolve()` still accepts only IDs, so a
  citation the tool counts is always by ID. This fails your `test_aliases_field_is_rejected`
  on purpose: B23's no-alias rule is about identity, and a readable handle bound to the title
  is not a second identity (Solenoid's B8 makes the same argument for `dte:ID name`).
- `_check_authority` no longer errors on a human-held node whose HEAD version was not
  human-held: that change is the ratification itself. Before this, `dte ratify` followed by
  `validate --as B` failed until the commit, which made the documented flow un-runnable.
- A `.base` file (Obsidian Bases) ships beside the tree with Outbox / Unratified / Contested /
  Inbox / All views. Bases cannot read bodies, so "MUST without Enforced-by" stays a test.

**10. [format, built in Solenoid's vendored copy] A `name` property beside `title`.** The
owner split the `name: description` title convention into two properties: `name` holds the
camelCase handle (validated as an identifier, unique across the tree, the source of `aliases`),
`title` is the description alone (so the 100-char check measures the summary, not the handle).
The tool prints `ID name: title`, `new` takes `--name`, `set name` exists, `find` searches
both. In Obsidian the handle is now a sortable column and a Bases property rather than a
prefix inside a string. If upstream ever wants readable handles, this is the shape.

**11. [format, owner's ruling, built in Solenoid's vendored copy] A node is present governance;
History is an activity log; the contest dies at ratification.** The owner's words: "decision trees
can have history but they can't become a dev log. that's just cluttered context." Ruling: a node
body holds what stands, why, and what it makes true. `## History` is one line per event (created,
ratified, moved, reworded) and nothing else. `## Alternatives considered` exists to inform the
ratification and is deleted by `ratify` once a human rules; git keeps the text. `contested_by`
stays, since it is provenance (B28). Solenoid's `ratify_one` now strips the section. Suggest the
same upstream, and a validate warning for a ratified node that still carries the section.
