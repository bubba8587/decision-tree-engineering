<!-- dte:B8,A3,A5,A6,B14,B15,B17 -->
# Working in this repo (and any DTE repo)

This project uses Decision Tree Engineering. Read `SPEC.md` once. Then follow
this protocol in every session. It exists because of B8 "AI agents record
each non-trivial decision as a node at the time they make it", which exists
because of A3 "every decision records who made it, human or AI".

## Your ring

You operate at a ring. If the human or the agent that spawned you told you
which, use that. In this repo, if nobody said, assume ring **B**: the owner
holds A, and subagents you spawn get C or deeper. Tell every subagent its
ring in its instructions. `python tools/dte.py authority` shows who holds
each ring and therefore whom to ask.

The map binds you, not the owner. The owner may decide at any ring.

## Before you change anything

1. `python tools/dte.py tree` to see the current tree and the inbox.
2. If you are about to edit an existing node, run
   `python tools/dte.py blast <ID>` first and read the whole report.
   Everything listed is your responsibility to reconcile.
3. If the node is human-held (made by a human, or ratified by one), you may
   not supersede, revert, move, or reword it. Ask. A human must write
   `authorized_by` on it before validate will pass (B11).

## While you work

- Every artifact you create or substantially change carries a citation:
  `dte:ID` in a comment (code) or an HTML comment / prose (docs). Cite the
  most specific node that explains it.
- If no existing node explains a choice you are making, and a reviewer could
  reasonably ask "why?", that is a new decision. Decide where it belongs:
  - **At your ring or deeper**: create it. `python tools/dte.py next <ring>`
    for the ID; never pick numbers by hand. Frontmatter per SPEC section 4,
    `made_by: ai`, `by: <your model name>`, `status: active`, real
    `parents`. Say what you decided, why the parents demanded it, and what
    it implies. `confidence: medium` or `low` when guessing the owner's
    preference, and say so.
  - **Shallower than your ring, or you are not sure**: do not create it.
    Write `decisions/inbox/<slug>.md` (SPEC section 7, Escalate) and ask
    the holder of that ring in chat, giving the title. It gets an ID only
    when someone with authority runs `dte place`.
- Never delete a decision file. Supersede or revert (SPEC section 7).
- Never resolve a contradiction by editing the loser. Precedence is
  position. If the ring order gives the wrong answer, that is a move, and
  moves above your ring are not yours to make.

## When you talk about decisions (A5)

Never name a decision by bare ID in chat. Always give the ID with its title,
for example: A5 "a decision is always referred to by ID plus a short dense
summary, never by bare ID". The reader almost certainly does not have the
decision file open. `python tools/dte.py tree` prints the ID-plus-title form
for every node; copy from there. When you write a node, make its `title`
dense enough to stand in for the decision in a sentence, under 100
characters.

## When you report work (B17)

Every time you tell the owner that something now exists or was built, name
the decision that governs it in the same message, as ID plus title. If you
created that node during the work, say so right there, not in a closing
list. "The inbox is built" is incomplete; "the inbox is built, governed by
B14 'unplaced decisions wait in decisions/inbox without an ID until someone
with authority places them', which I created" is complete. The owner may
want to overrule the decision, and cannot if they only hear about the
artifact.

## Before you say you are done

- `python tools/dte.py validate --as <your ring>` must print `OK`. Warnings
  are allowed; read them anyway. It fails if you touched a node above your
  ring or a human-held node.
- Validate ends with "Nodes changed in this working tree". Copy those lines
  into your report so the owner can ratify them. List anything you put in
  the inbox, with the question it is waiting on. Unratified AI decisions
  are also printed; do not try to clear that list yourself.

## Rings in this repo

- `A` core goals. A1, A5, A6 are the owner's; A2 to A4 are proposed and
  await ratification. Do not add to ring A. Inbox it and ask.
- `B` format and rules of DTE itself.
- `C` how the reference tool implements ring B.

## Conventions

- Python 3.8+, standard library only, one file for the tool (B6).
- Keep prose short. The Why section carries the argument; the Decision
  section is one or two citable sentences.
