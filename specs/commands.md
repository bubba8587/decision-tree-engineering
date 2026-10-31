<!-- [[B29]], [[B12]], [[B22]], [[B11]], [[B16]], [[B60]], [[B33]], [[B9]], [[B39]], [[B6]], [[A8]], [[B37]], [[B42]], [[B27]], [[B14]], [[B17]], [[B15]], [[B43]], [[B56]], [[B59]] -->
<!-- covers: tools/dte.py -->
# Commands

What each authoring, checking and agent command of the reference tool does. It serves B29 toolWritesFrontmatter (frontmatter is written only by commands), B43 leanFrontmatter, B59 provenanceFields, B60 oneContest, B42 builderAutonomy and B56 portableProtocol. Retiring, moving, folding and renumbering are in `specs/retiring.md`; finding citations and the gauges are in `specs/scanning.md`.

## Paths

A path argument is taken as typed when it is absolute or exists from the current directory, and relative to `--root` otherwise.

## new, place, import

Every command that writes a leaf writes the 0.2 shape: `id`, `uuid`, `title` (double-quoted), `status` only when not active, `parents`, `branch` when given, `made_by` only when not `ai`, `by`, `date`, an empty `ratified_by:` (so the property shows in Obsidian, ready to be typed into), `authorized_by` and `contested_by` when set, and `aliases: [name]`.

`dte new <ring> --name N --title T --by NAME [--parents ...] [--made-by ai|human|joint] [--status active|proposed] [--branch B] [--authorized-by HUMAN]` requires a camelCase name not already taken. The body comes from `--body-file` (its sections verbatim, frontmatter stripped, Decision and Why required) or from `--decision`, `--why` and `--consequences`; a missing section is `TODO` and validate warns until it is written. Before allocating, `new` asks `git ls-remote --heads origin` (eight-second timeout) and warns when the remote has branches this clone has not fetched; `DTE_NO_REMOTE=1` skips the call.

`dte place <slug> <ring> --by NAME [--parents ...]` writes an inbox item as a leaf with a History line and removes the inbox file; a gap is refused. The placer does not ratify.

`dte import <dir> --by NAME [--source LABEL]` reads every `.md` in the folder: frontmatter `ring`, `title`, optional `name` (or `aliases`) and `parents` (ids, names, or other files in the batch by file name or name), and any leaf property the source already carries; the body verbatim. Ids are allocated parent-first. Each leaf gets the History line `imported from <source> (<file>)`, which is the import mark, and a carried `ratified_by` gets a second line saying so. An unknown property, a cycle or a parent that resolves to nothing refuses the whole batch.

## set, ratify, authorize, reparent, conflict

`dte set <ID> title|name VALUE --by NAME [--authorized-by HUMAN]` is the one generic field write. It collapses whitespace, warns on a title of 100 characters or more, checks a name's shape and uniqueness and writes it as the one alias, refuses a human-held leaf without a human's name, and appends the old value to History. Any other field is refused with the command that owns it.

`dte ratify <ID>... --by HUMAN` sets `ratified_by`, drops `status` when it flips proposed to active, drops `## Contest` and `## History`, and writes one History line naming what it dropped. A human-made leaf is refused; ratification is for AI and joint leaves.

`dte authorize <ID>... --by HUMAN [--note TEXT]` writes `authorized_by` on existing leaves with a History line.

`dte reparent <ID> --parents A1,B2 --by NAME [--authorized-by HUMAN]` replaces a leaf's parents, checking each is in effect and shallower, refusing a human-held leaf without a human's name, and logging the old parents.

`dte conflict <A> <B>` writes `conflicts_with` on both and prints the winner by ring; a same-ring pair fails validation until one is superseded or moved.

## contest

`dte contest <ID>` refuses a human-held leaf, and a contested one unless `--again`. It prints the body, the parents as the read-only rubric (for a core leaf, the owner's stated purpose), the counts of children and citing artifacts that count for nothing, the reminder that a Why naming no forcing incident is the thinner claim, and the four slots keep, opposite, deletion and variant.

`dte contest <ID> --record --chosen <slot> --by NAME (--note TEXT | --file NOTES.md)` appends `### Contest <date> by <who>: <slot> wins` and the notes under `## Contest`, sets `contested_by` and logs a History line. With a non-keep verdict, `--title` and a body (`--body-file` or the section flags, plus `--name`) write the winner at the same ring with the same parents and `contested_by` set, then retire the loser superseded by it; `--chosen deletion --retire` reverts it in the same run.

## cite and hook

`dte cite <file> <ID[,ID]>` refuses an unknown or retired id. It reads the first 15 lines below a shebang or a markdown frontmatter as the header: an id already cited there in any form, named or beside other ids, is skipped, and when every id is skipped it does nothing. The rest join an existing line that holds only a citation, or a new comment line in the file type's syntax: `#` for Python, shell, YAML, TOML and files without an extension; `//` for the C family, JavaScript, Go, Rust, Java and friends; `<!-- -->` for markdown, HTML and XML; `/* */` for CSS; `--` for SQL and Lua. JSON and CSV have no comments and are refused.

`dte hook` writes `.git/hooks/pre-commit` running `validate`, and refuses to touch a hook that exists without mentioning dte.

## validate

`validate` prints every error and warning, the inbox with the question to ask, one line counting unratified leaves (contested and imported among them) followed by each unratified leaf of rings A and B with how many leaves sit below it, the changed-leaves block, the outbox count, the scope-finding count, and a summary line; then `OK` or `FAILED`, exiting 1 on errors. `--full` lists every unratified leaf. `--as <ring>` (default `$DTE_RING`) adds the authority check on changed files. With no ring declared and changed files under the decisions directory, a warning asks for one unless `DTE_OWNER` is set.

The changed-leaves block, headed "Leaves changed in this working tree", lists each added or modified leaf as its label, marking `[body changed]` and whether a History line or the editorial log covers it. It is meant to be copied into the agent's report.

Per leaf, validate checks: the file sits at `decisions/<ring>/<ID>.md`; a uuid is present and unique; every field is known, and a 0.1 field is named with `dte upgrade`; the name is camelCase and unique, with the fix printed when it is not; there is at most one alias; Decision and Why exist; no section is empty; a ratified leaf has no Contest; parents exist, are shallower, are in effect; a same-ring declared conflict is an error; a retired human-held leaf has `authorized_by`; the body cites no deeper ring outside History and Contest; a MUST is tested or labeled; and a branch-local root sits on its own branch.

`unratified` lists every unratified leaf, shallowest ring first, then by how many leaves sit below it.

## export

`dte export [--out FILE]` writes one JSON object with sorted keys: `leaves` (every frontmatter field plus `ring` and `path`), `citations` (`file`, `line`, `id`), `retired` (the ledger rows), `inbox` (slug, title, proposed ring, ask, provenance), `errors` and `warnings`. The file path is the join key for a structural graph tool.

## init

`dte init` creates `dte.cfg` with every key present and commented with its default, `.dteignore` with common vendored and generated paths plus the tool's own file, `.dtecoverage` with a commented example, and the decisions directory (from `decisions` in the config) with its inbox. It never overwrites, and prints the next steps.

## vendor

`dte vendor --from <a DTE checkout> [--dir vendor/dte]` copies `PROTOCOL.md`, `SPEC.md`, `ADOPTING.md`, `README.md` and `WALKTHROUGH.md` into the directory and renders the source's in-effect leaves by ring into `DECISIONS.md`. Each file starts with one comment naming the DTE version, the source commit, the date and the copy's own refresh command (`python <the project's tool path> vendor --from <a DTE checkout> --dir <dir>`); nothing in it names the source checkout's path. A 0.1 `CLAUDE.md` copy is removed. The tool file is refreshed: the running copy when it lives in the project, else `tools/dte.py`. The directory is added to `.dteignore` once, whichever spelling (`dir`, `dir/`, `dir/*`) is already there. When an earlier render exists, every A and B leaf added since is printed with its Decision, and every one retired.

## spec, brief, gap

`dte spec <ID> [--out FILE]` writes a skeleton: the leaf's citation, its Decision as Purpose, its parents' Decisions and its Consequences as Constraints, every in-effect descendant as a covered decision, and empty Requirements, Out of scope and Gaps. It refuses to overwrite, and notes when the file sits outside the `specs` globs.

`dte brief <ring> [--under ID]` prints the subagent block: the ring, the rules (decide at the ring or deeper with `new`, the leaf-or-spec test, the child-is-a-fork test, escalate the rest to the inbox, cite with ID plus name, never change a human-held leaf, stop on a refused tree edit, validate with `DTE_RING`, contest an unratified leaf before building under it), then every in-effect leaf above the ring that binds it, restricted to the lineage and subtree of `--under` when given.

`dte brief --builder <spec>` prints the builder rules and the spec text: build exactly what the spec says, cite the ids it names, decide nothing, never read the decisions directory, file a gap when the spec is silent, validate before finishing, and do not set `DTE_RING`. `dte gap <spec> --title T --by NAME [--note TEXT]` writes `decisions/inbox/gap-<slug>.md` with `kind: gap` and the spec's path; `inbox` lists gaps apart from decisions.
