<!-- [[B3]], [[B37]], [[B12]], [[B21]], [[B30]], [[B1]], [[B15]], [[B6]], [[B44]], [[B45]], [[B46]] -->
<!-- covers: tools/dte.py -->
# Scanning

How the reference tool finds citations, sorts the files that hold them into layers, and turns them into coverage gauges and scope findings. It serves B3 citationToken (artifacts cite leaves), B37 derivedLinks (lists below a leaf are derived, never stored), B44 specCovers, B45 coverageStore and B21 scopeAdvisory.

## The walk

The scanner walks the project root and reads every file except anything under `.git`, the decisions directory, `.dtecoverage`, a file with a NUL byte in its first 8 KB, and a path matching a glob in `.dteignore`. The running tool file is skipped unless `scan_self = on`, because the tool's own citations belong to DTE's tree; only DTE's repository sets it.

An ignore glob matches a path, any one segment of a path, or a directory prefix, so `node_modules` and `vendor/dte/` both work.

## Citation forms

Two forms are read everywhere: the token `dte:` followed by one or more comma-separated ids, and the wikilink `[[ID]]` or `[[ID|text]]`. In a frontmatter link field a quoted wikilink, `"[[A1]]"`, reads as the bare id. The `links` key picks the form the tool writes: `token` writes `dte:ID`, `wikilink` writes `[[ID]]`.

A citation to an unknown id is an error. A citation to a retired id is an error that carries the ledger's hint, including the `git log` command that shows the old text. A citation to a leaf that is not in effect (keep mode) is a warning.

Examples in prose use the two-letter placeholder ring `ZZ` (`dte:ZZ1`), which is not an id shape and never counts.

## Layers

`layer_of(path)` checks the `tests`, `specs`, `agents` and `docs` globs from `dte.cfg` in that order and falls back to code. `show` groups a leaf's citing artifacts under "enforced by", "specified by", "instructs", "described by" and "implemented by". A doc does not count as reach.

## A spec's scope

A spec-layer file declares its scope with `covers: <globs>` in a comment line within its first 30 lines (an HTML, `//`, `/*` or `# ` comment; a markdown heading is not a comment). Every scanned file the globs match, the spec itself excepted, is built to the spec. When the spec cites a leaf, each covered file counts as citing that leaf through the spec: `show` lists it with "via <spec>", and `blast` prints a "Built to" block per spec.

## The exclusion store

`.dtecoverage` at the root lists files that need no decision. A `why:` line opens a group and the globs under it, in `.dteignore` syntax, belong to that group. A glob before any `why:` line, or an empty `why:`, makes `coverage` exit 2. An excluded file is still scanned, and a citing one counts as cited instead of excluded. A glob that matches no scanned file is stale.

## The three gauges

`dte coverage` prints one gauge per hop:

- **artifacts**: scanned files outside the exclusion store that cite a leaf, or are built to a spec that cites one.
- **specs**: spec-layer files that cite at least one leaf themselves.
- **MUSTs**: in-effect leaves whose body states `MUST` (outside History, Contest and Alternatives considered, and not in backticks) that some test-layer file cites; the line also counts the ones labeled `*Unenforced:*`.

It then lists the excluded counts per reason (`--excluded` lists the files), stale globs from the store or from `covers:`, uncited artifacts, uncited specs, and MUSTs neither tested nor labeled. The last block is the next worklist: files covered only through a spec's `covers:` that still carry five or more comment lines, where a WHY may still live in the code.

`coverage --check` exits 1 when an artifact or spec is uncited, a glob is stale, or (with `must_test = on`) a MUST is neither tested nor labeled.

## Scope findings

`dte scope` is advisory and never fails. Reach is a leaf's transitive descendants plus the non-doc artifacts citing it or a descendant.

- **no reach**: a non-core in-effect leaf with no descendants and no non-doc citation.
- **broad**: a non-core leaf whose descendants or implementing files are at least `broad_fraction` of the whole, with at least `broad_min` of them.
- **skipped ring**: a parent more than one ring shallower, unless the parent or the leaf is human-held, since the owner made or accepted that skip.
- **core-only code**: a non-doc artifact line citing ring A.

`scope --comments` lists code-layer files with five or more comment lines and no citation, skipping excluded files.

## Changed files

The `--as` check, the body-change check and the changed-leaves block ask `git status --porcelain --untracked-files=all`. Without git every leaf counts as changed and a warning says the check is coarse. A leaf as it stood at HEAD comes from `git show HEAD:<path>`.
