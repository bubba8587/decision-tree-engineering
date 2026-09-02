<!-- dte:B8,A3 -->
# Working in this repo (and any DTE repo)

This project uses Decision Tree Engineering. Read `SPEC.md` once. Then follow
this protocol in every session. It exists because of decision B8, which
exists because of A3: AI-made decisions must be recorded at the moment they
are made or they are lost.

## Before you change anything

1. `python tools/dte.py tree` to see the current tree.
2. If you are about to edit an existing decision node, run
   `python tools/dte.py blast <ID>` first and read the whole report. Everything
   listed is your responsibility to reconcile.

## While you work

- Every artifact you create or substantially change must carry a citation:
  `dte:ID` in a comment (code) or an HTML comment / prose (docs). Cite the most
  specific node that explains it.
- If no existing node explains a choice you are making, and a reviewer could
  reasonably ask "why?", that is a new decision. Create it:
  - `python tools/dte.py next <ring>` for the ID. Never pick numbers by hand.
  - Write `decisions/<ring>/<ID>.md` using the frontmatter in SPEC section 4.
  - `made_by: ai`, `by: <your model name>`, `status: active`, real `parents`.
  - Say what you decided, why the parents demanded it, and what it implies.
  - Set `confidence: medium` or `low` when you are guessing the owner's
    preference, and say so in the Why.
- Never delete a decision file. Supersede or revert (SPEC section 7).
- Never resolve a contradiction by editing the loser. Precedence is position.
  If the ring order gives the wrong answer, that is a move, and moves are the
  owner's call.

## Before you say you are done

- `python tools/dte.py validate` must print `OK`. Warnings are allowed;
  read them anyway.
- Mention any new nodes you created in your final message so the owner can
  ratify them. Unratified AI decisions are listed at the end of every
  validate run; do not try to clear that list yourself.

## Rings in this repo

- `A` core goals. A1 is the owner's; A2 to A4 are proposed and await
  ratification. Do not add to ring A without being asked.
- `B` format and rules of DTE itself.
- `C` how the reference tool implements ring B.

## Conventions

- Python 3.8+, standard library only, one file for the tool (B6).
- Keep prose short. The Why section carries the argument; the Decision
  section is one or two citable sentences.
