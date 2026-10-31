<!-- [[B24]], [[B32]], [[B11]], [[B60]], [[B29]], [[B47]], [[B48]], [[B54]], [[B58]], [[B61]] -->
<!-- covers: tools/dte.py -->
# Retiring

How a leaf leaves the tree, changes ring, or changes number, and how the tool keeps every reference honest when it does. It serves B24 retiredLedger (nothing vanishes), B32 nameHandle (the id is the identity), B58 uuidIdentity, B47 leafIsACall, B48 childIsFork and B61 bodyEditsLogged.

## The ledger

`decisions/RETIRED` holds one tab-separated line per retired leaf: `id, date, action, successor or -, by, authorized_by or -, title`. Lines starting with `#` are comments. The actions are `superseded`, `reverted`, `moved`, `folded` and `to-spec`; for `to-spec` the successor column holds the spec's path. An id retired twice is an error.

`next` never reissues a ledger number. A citation, parent or conflict naming a ledger id is an error carrying the ledger's hint. What a leaf superseded is derived from the ledger: every line whose successor is that leaf and whose action is `superseded`, `moved` or `folded`.

## Deletion checks

With git, a leaf file git reports deleted is an error unless the ledger has its line; under `retire = keep` it is an error regardless, since keep mode retires by status. A renamed leaf file is an error. Two exceptions, each a case where the leaf did not leave: a file whose HEAD uuid now lives under another id was renumbered, and a file whose HEAD version belongs to another branch's subtree (its own `branch:` or an ancestor's) is leaving a branch it never belonged to.

For an uncommitted deletion, the human-held and ring checks read the leaf at HEAD.

## Rewriting references

Whenever a leaf's id goes away in favour of another, every citation of the old id becomes the new one: in artifacts, and in leaf bodies outside History, which records what was true then. Where the old leaf's name followed its id, the new leaf's name replaces it. A line that ends up citing the new id twice keeps the first; the separator before a repeat (`,`, `;`, `and`, `or`) goes with it, and so do brackets it leaves empty. Each child's `parents` changes the old id to the new one.

## retire

`dte retire <ID> --by NAME [--superseded-by NEW] [--authorized-by HUMAN]` refuses a human-held leaf without a human's name. With a successor it rewrites references to NEW and prints them for review, since they were built under the old leaf. Without one it prints the references that now fail validation: that list is the revert's blast radius. Then it writes the ledger line and deletes the file, or under `retire = keep` sets `status` and `superseded_by` (and the successor's `supersedes`). Delete mode without git keeps the file, with a warning.

A contest travels to the successor only when that contest produced it: `contest --record` writing the winner passes it on, setting the successor's `contested_by` and a History line. A successor that merely absorbed a retired leaf inherits no contest.

## move

`dte move <ID> <ring> --by NAME [--parents A1,B2] [--authorized-by HUMAN]` refuses a leaf that is not in effect, is already at that ring, has a child that would not be deeper, or is human-held without a human's name. Parents are `--parents`, or else the old parents still strictly shallower; every dropped parent is printed. The new leaf takes the old body, a fresh id and a fresh uuid, no `ratified_by`, and a History line. The old leaf retires as `moved`, and references follow.

## fold

`dte fold <ID> [--into PARENT] --by NAME [--authorized-by HUMAN]` takes a child that only details its parent back into it. The child must have one parent, or name the one with `--into`. Its Decision and Consequences become bullets under the parent's Consequences (a paragraph becomes one bullet), the parent gets a History line, references and children move to the parent, and the child retires as `folded`. A human-held child or parent needs a human's name.

## to-spec

`dte to-spec <ID> <spec> --by NAME [--authorized-by HUMAN]` turns a mechanics leaf into spec text. The spec must sit inside the `specs` globs and is created if missing, titled from its file name and citing the leaf's parents. The leaf's title becomes a section heading with its Decision and Consequences under it, and the spec's header gains any parent it did not already cite. Citations of the leaf move to its first parent and are printed for review, since each file may really be built to the spec instead. Children join the leaf's parents. The leaf retires as `to-spec`. A ring A leaf is refused: a goal is never mechanics.

## renumber and merge-ids

`dte renumber <ID> --by NAME [--to NEW]` gives a leaf a new number in the same ring, the next free one by default. The uuid stays, because it is the same leaf. References follow, the leaf gets a History line, and no ledger line is written, because the old number goes on naming whichever leaf holds it elsewhere.

`dte merge-ids <ref> --by NAME [--dry-run]` runs on the branch about to merge into or rebase onto `ref`. Every leaf here whose id `ref` gives to a different leaf (another uuid, none, or a retirement this branch did not make) is renumbered to a number free here, at `ref`, in both ledgers and on every branch git knows.

## The editorial log

`decisions/EDITORIAL` holds one tab-separated line per wording-only sweep: `date, by, note, leaves`, where leaves are space-separated `ID@hash` pairs and the hash is the first 12 hex digits of SHA-256 over the leaf's body with whitespace collapsed. `dte editorial --by NAME --note TEXT` writes a line covering every leaf whose body changed in the working tree with no new History line. The body-change check accepts a leaf whose current body hash a line records, so the next edit to it warns again.

A body change counts as logged when its History holds a line HEAD's History lacks; a History that was reset to one new line therefore counts.

## upgrade

`dte upgrade` rewrites 0.1 frontmatter in place and touches no body: the name becomes the one alias, `name` and `confidence` go, `status: active`, `made_by: ai` and an empty `conflicts_with` go, under `retire = delete` `supersedes` and `superseded_by` go, and a leaf without a uuid gets one after its id line. A backfilled uuid takes its time from the leaf's date plus its number in milliseconds and its random bits from SHA-256 of `id|title`, so running it twice changes nothing.
