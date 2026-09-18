# Obsidian vault schema, copied from the Solenoid adoption (2026-09-18)

Reference material for the DTE upgrade driven by FEEDBACK.md. Not a decision node; excluded from the scanner via `.dteignore`. Delete once the upgrade lands.

Solenoid opens `decisions/` as the vault root. Layout observed:

```
decisions/
  .obsidian/            app.json, appearance.json, core-plugins.json, graph.json,
                        workspace.json (per-user state, not copied), themes/Obsidianite (3rd-party theme, not copied)
  A/ B/ C/ D/ E/        node files, one per ID, wikilink form
  DTE.base              Obsidian Bases file: Outbox / Unratified / Contested / Inbox / All nodes
  README.md             one-screen guide for the human using the vault (below)
  RETIRED               ledger (no extension; feedback #8 suggests RETIRED.md as a table)
  inbox/                agent -> human
  outbox/               human -> agent (feedback #9)
```

Node frontmatter shape in the vault (name + aliases + quoted title + wikilink link fields):

```yaml
---
id: C81
name: wikilinkCitations
title: "citations and link fields are [[ID]] wikilinks, browsable from Obsidian"
status: active
parents: ["[[B8]]", "[[B1]]"]
supersedes: []
superseded_by:
conflicts_with: []
made_by: ai
by: Claude Fable 5.1
date: 2026-09-17
ratified_by:
aliases: [wikilinkCitations]
---
```

Ledger header there: `# Retired decision ids. Never reissued. Text lives in git history.  [[C11]]`

Solenoid dte.cfg additions:

```
# links: how the tool writes citations and the link fields (parents, supersedes,
# superseded_by, conflicts_with). token writes dte:ID; wikilink writes [[ID]] so the
# tree is browsable from Obsidian (graph view, backlinks). Both forms are always read.
links = wikilink
docs = *.md, docs/*
```

Solenoid .dteignore lines relevant to DTE:

```
# Agent worktrees hold full repo copies; scanning them double-counts everything.
.claude
# The vendored DTE tool + its canonical rule copies: their dte: tokens belong to
# DTE's own tree, not this one. Kept in-repo so agents can load the rule text.
tools/dte.py
dte-rules
```

## decisions/.obsidian/app.json

```json
{}
```

## decisions/.obsidian/appearance.json

```json
{
  "interfaceFontFamily": "Atkinson Hyperlegible Next",
  "monospaceFontFamily": "Atkinson Hyperlegible Mono",
  "textFontFamily": "Atkinson Hyperlegible Next",
  "cssTheme": "Obsidianite"
}
```

## decisions/.obsidian/core-plugins.json

```json
{
  "file-explorer": true,
  "global-search": true,
  "switcher": true,
  "graph": true,
  "backlink": true,
  "canvas": true,
  "outgoing-link": true,
  "tag-pane": true,
  "footnotes": false,
  "properties": true,
  "page-preview": true,
  "daily-notes": true,
  "templates": true,
  "note-composer": true,
  "command-palette": true,
  "slash-command": false,
  "editor-status": true,
  "bookmarks": true,
  "zk-prefixer": false,
  "random-note": false,
  "outline": true,
  "word-count": true,
  "slides": false,
  "audio-recorder": false,
  "workspaces": false,
  "file-recovery": true,
  "publish": false,
  "sync": true,
  "bases": true,
  "webviewer": false
}
```

## decisions/.obsidian/graph.json

(colorGroups by ring folder; DTE has rings A-C only, trim accordingly)

```json
{
  "collapse-filter": true,
  "search": "",
  "showTags": false,
  "showAttachments": false,
  "hideUnresolved": false,
  "showOrphans": true,
  "collapse-color-groups": true,
  "colorGroups": [
    {
      "query": "path:A/",
      "color": {
        "a": 1,
        "rgb": 5397472
      }
    },
    {
      "query": "path:B/",
      "color": {
        "a": 1,
        "rgb": 11657298
      }
    },
    {
      "query": "path:C/",
      "color": {
        "a": 1,
        "rgb": 13705112
      }
    },
    {
      "query": "path:D/",
      "color": {
        "a": 1,
        "rgb": 5358100
      }
    },
    {
      "query": "path:E/",
      "color": {
        "a": 1,
        "rgb": 14432798
      }
    }
  ],
  "collapse-display": true,
  "showArrow": false,
  "textFadeMultiplier": 0,
  "nodeSizeMultiplier": 1,
  "lineSizeMultiplier": 1,
  "collapse-forces": true,
  "centerStrength": 0.100890985324948,
  "repelStrength": 10.9355700986266,
  "linkStrength": 1,
  "linkDistance": 30,
  "scale": 0.04778763528607827,
  "close": true
}
```

## decisions/DTE.base

```yaml
filters:
  and:
    - file.ext == "md"
properties:
  file.name:
    displayName: ID
  name:
    displayName: Name
  title:
    displayName: Title
  made_by:
    displayName: Made by
  ratified_by:
    displayName: Ratified by
  contested_by:
    displayName: Contested by
  file.folder:
    displayName: Ring
views:
  - type: table
    name: Outbox
    filters:
      or:
        - file.inFolder("outbox")
        - file.hasTag("ratify", "retire", "contest", "ask")
    order:
      - file.name
      - name
      - title
      - file.tags
      - file.mtime
  - type: table
    name: Unratified
    filters:
      and:
        - file.hasProperty("id")
        - note.ratified_by.isEmpty()
        - note.status != "superseded"
        - note.status != "reverted"
    groupBy:
      property: file.folder
      direction: ASC
    order:
      - file.name
      - name
      - title
      - made_by
      - by
      - contested_by
      - confidence
  - type: table
    name: Contested
    filters:
      and:
        - file.hasProperty("id")
        - "!note.contested_by.isEmpty()"
        - note.ratified_by.isEmpty()
    order:
      - file.name
      - name
      - title
      - contested_by
      - date
  - type: table
    name: Inbox
    filters:
      and:
        - file.inFolder("inbox")
    order:
      - file.name
      - name
      - title
      - proposed_ring
      - ask
      - by
  - type: table
    name: All nodes
    filters:
      and:
        - file.hasProperty("id")
    groupBy:
      property: file.folder
      direction: ASC
    order:
      - file.name
      - name
      - title
      - status
      - ratified_by
      - parents
      - date
```

## decisions/README.md (vault-side guide for the human)

```markdown
# Using the tree from here

**Tell an agent something.** Tag a node, or drop a note in `outbox/`. The next session picks it up.

| Tag | Means |
|---|---|
| `#ratify` | I accept this decision |
| `#retire` | Revert it |
| `#contest` | I disagree; build the alternatives |
| `#ask` | Answer the question next to this tag |

Tags go in the `tags` property or inline in the body. Typing your name into `ratified_by` also counts.

**Write a decision.** New note in `outbox/`, any shape. Say what and why. Above ring C it becomes an inbox item first.

**Find things.** `[[C41]]` by ID, `[[branchModel]]` by name. `DTE.base` has the Outbox, Unratified, Contested, Inbox and All views.

**Never.** Rename or delete a node file, or change `id`, `parents`, `status`. Those go through the tool.

**Agent side.** `python tools/dte.py outbox` lists what you left, `--done <ID or note>` clears it, `validate` prints the count. Details: `docs/dte.md`.
```

## Diff: DTE tools/dte.py -> Solenoid tools/dte.py (wikilinks, quoted titles, name/aliases/tags, null, outbox, authority fix)

Unified diff, `diff DTE/tools/dte.py solenoid/tools/dte.py`. Solenoid-specific citations ([[C81]] etc.) are theirs, not ours.

```diff
50a51,52
> # Two citation forms, read everywhere: the dte: token and the [[ID]] wikilink
> # (optionally [[ID|alias]]) that Obsidian follows. `links` in dte.cfg picks the written one.
51a54,93
> LINK_RE = re.compile(r"\[\[([A-Z]\d+)(?:\|[^\]]*)?\]\]")
> 
> 
> def cited_ids(line):
>     """Every id cited on a line, in order, from both forms."""
>     found = []
>     for m in CITE_RE.finditer(line):
>         found.extend(re.split(r"\s*,\s*", m.group(1)))
>     found.extend(m.group(1) for m in LINK_RE.finditer(line))
>     return found
> 
> 
> def wikilinks():
>     return CONFIG.get("links") == "wikilink"
> 
> 
> def fm_id(i):
>     """One id as written in a frontmatter link field."""
>     return '"[[%s]]"' % i if wikilinks() else i
> 
> 
> def fm_ids(ids):
>     return "[%s]" % ", ".join(fm_id(i) for i in ids)
> 
> 
> def cite_text(ids):
>     """The citation as written into an artifact."""
>     if wikilinks():
>         return ", ".join("[[%s]]" % i for i in ids)
>     return "dte:" + ",".join(ids)
> 
> 
> def sub_citations(text, old_id, new_id):
>     """old_id -> new_id in every citation of either form."""
>     def swap(m):
>         ids = [new_id if x == old_id else x for x in re.split(r"\s*,\s*", m.group(1))]
>         return "dte:" + ",".join(ids)
>     text = CITE_RE.sub(swap, text)
>     return LINK_RE.sub(lambda m: m.group(0).replace("[[" + old_id, "[[" + new_id, 1)
>                        if m.group(1) == old_id else m.group(0), text)
56,57c98,100
< KNOWN_FIELDS = LIST_FIELDS | {
<     "id", "title", "status", "superseded_by", "made_by", "by", "date",
---
> OBSIDIAN_FIELDS = {"aliases", "tags", "cssclasses"}   # Obsidian's own keys; read, never judged
> KNOWN_FIELDS = LIST_FIELDS | OBSIDIAN_FIELDS | {
>     "id", "name", "title", "status", "superseded_by", "made_by", "by", "date",
60c103,121
< INBOX_FIELDS = {"title", "proposed_ring", "ask", "made_by", "by", "date", "parents", "confidence"}
---
> INBOX_FIELDS = {"name", "title", "proposed_ring", "ask", "made_by", "by", "date", "parents", "confidence"} | OBSIDIAN_FIELDS
> NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*(?:-\d+)?$")   # a node's readable handle, the `name` field
> # The outbox: what a human changes in the vault and an agent must process. A note dropped in
> # decisions/outbox, an action tag on a node (a tags property or an inline #ratify, #retire, #contest, #ask),
> # or a ratified_by typed into the properties pane. Never a bare diff: an anonymous edit cannot
> # be told from an agent's own unfinished work, and validate already lists changed nodes (B17).
> OUTBOX_DIR = "outbox"
> ACTION_TAG_RE = re.compile(r"(?<![\w/#])#(ratify|retire|contest|ask)\b")
> ACTIONS = {
>     "ratify": "the author ratifies it: dte ratify <ID> --by <author>, then move the id into the owner-kept list the tests pin",
>     "retire": "the author reverts it: dte blast <ID>, then dte retire <ID> --by <author> --authorized-by <author>, fix the orphans",
>     "contest": "the author disputes it: dte contest <ID> --again, build the alternatives, record the verdict, report",
>     "ask": "the author left a question or comment in the body: answer it in chat; if it changes the node, make the change and add a History line",
> }
> 
> 
> def summary_of(name, title):
>     """How a node is printed: `name: title` when it has a handle, else the title."""
>     return "%s: %s" % (name, title) if name else title
68c129,130
<             "retire": "delete"}   # dte:B24
---
>             "retire": "delete",   # dte:B24
>             "links": "token"}     # token writes dte:ID; wikilink writes [[ID]] (Obsidian-browsable)
96a159,160
>             elif key == "links":
>                 cfg["links"] = "wikilink" if val.lower() in ("wikilink", "wiki", "obsidian") else "token"
165,166c229,239
<         return raw[1:-1]
<     return raw
---
>         q, raw = raw[0], raw[1:-1]
>         raw = raw.replace("''", "'") if q == "'" else raw.replace('\\"', '"').replace("\\\\", "\\")
>     elif raw in ("null", "~", "Null", "NULL"):   # Obsidian writes an emptied property as null
>         return ""
>     m = LINK_RE.fullmatch(raw)   # "[[B7]]" in a link field reads as B7
>     return m.group(1) if m else raw
> 
> 
> def fm_str(s):
>     """A free-text field, double-quoted so a colon or hash inside it stays valid YAML."""
>     return '"%s"' % s.replace("\\", "\\\\").replace('"', '\\"')
183a257
>         self.name = str(data.get("name") or "")
184a259
>         self.summary = summary_of(self.name, self.title)
192a268,271
>         tags = data.get("tags") or []
>         tags = [str(t).lstrip("#") for t in (tags if isinstance(tags, list) else [tags]) if str(t)]
>         self.actions = sorted({t for t in tags if t in ACTIONS}
>                               | {m.group(1) for m in ACTION_TAG_RE.finditer(body)})
231c310
<         return "%s %s%s" % (self.id, self.title, tag)
---
>         return "%s %s%s" % (self.id, self.summary, tag)
241a321
>         self.name = str(self.raw.get("name") or "")
266a347
>         self.outbox_dir = os.path.join(self.decisions_dir, OUTBOX_DIR)
268a350
>         self.outbox = []           # (slug, title, path) notes the human dropped for an agent
284a367
>             dirs[:] = [d for d in dirs if not d.startswith(".")]   # .obsidian and friends
290a374,379
>             if os.path.abspath(dirpath) == os.path.abspath(self.outbox_dir):
>                 for fn in sorted(files):
>                     if fn.endswith(".md"):
>                         self._load_outbox(os.path.join(dirpath, fn))
>                 dirs[:] = []
>                 continue
301a391,426
>     def _load_outbox(self, path):
>         """A human's note: frontmatter optional, title from it, the first heading, or the file name."""
>         text = read_text(path).replace("\r\n", "\n")
>         slug = os.path.splitext(os.path.basename(path))[0]
>         title = None
>         if text.startswith("---"):
>             try:
>                 data, body = parse_frontmatter(text)
>                 title = str(data.get("title") or "") or None
>             except ValueError:
>                 body = text
>         else:
>             body = text
>         if not title:
>             m = re.search(r"^#+\s+(.+)$", body, re.M)
>             title = m.group(1).strip() if m else slug
>         self.outbox.append((slug, title, path))
> 
>     def outbox_items(self):
>         """[(kind, ref, label, todo)] everything a human designated in the vault for an agent to process."""
>         items = []
>         for slug, title, path in self.outbox:
>             items.append(("note", slug, '"%s"  (%s)' % (title, self.rel(path)),
>                           "read it and act: a decision becomes dte new or an inbox item, a correction becomes an edit, "
>                           "a question gets an answer in chat; then dte outbox --done %s" % slug))
>         for node in self.ordered_nodes():
>             for act in node.actions:
>                 items.append(("tag", node.id, "%s  #%s" % (node.label(), act),
>                               ACTIONS[act]
>                               + "; then dte outbox --done %s" % node.id))
>             if node.ratified_by and not re.search(r"ratified by", node.body):
>                 items.append(("ratified", node.id, "%s  ratified_by: %s typed in, no History line" % (node.label(), node.ratified_by),
>                               "run dte ratify %s --by \"%s\" so History records it, then move the id into the owner-kept list the tests pin"
>                               % (node.id, node.ratified_by)))
>         return items
> 
402a528
>         names = {}   # handle -> id, for uniqueness
420a547,551
>             if node.name and not NAME_RE.match(node.name):
>                 E.append("%s: name %r is not an identifier" % (i, node.name))
>             if node.name and names.get(node.name, i) != i:
>                 E.append("%s: name %r is already %s's" % (i, node.name, names[node.name]))
>             names.setdefault(node.name, i)
523a655,657
>                 old = self.node_at_head(rel)
>                 if old is not None and not old.human_held:
>                     continue   # this change IS the ratification; the report lists it for the human
689,691c823,824
<                     for m in CITE_RE.finditer(line):
<                         for cid in re.split(r"\s*,\s*", m.group(1)):
<                             self.citations.append((rel, ln, cid, self.resolve(cid)))
---
>                     for cid in cited_ids(line):
>                         self.citations.append((rel, ln, cid, self.resolve(cid)))
800a934,936
>     n_out = len(tree.outbox_items())
>     if n_out:
>         print("\nOUTBOX (%d): the human designated things in the vault for an agent; run dte outbox" % n_out)
1024a1161,1223
> def cmd_outbox(tree, args):
>     """The human's edits in the vault, as a work list; --done clears one item once processed."""
>     if args.done:
>         return outbox_done(tree, args.done)
>     items = tree.outbox_items()
>     if not items:
>         print("Outbox empty. The human has designated nothing for an agent.")
>         return 0
>     print("OUTBOX (%d): process each, then clear it. The author's word is the authorization." % len(items))
>     for kind, ref, label, todo in items:
>         print("  [%s] %s" % (kind, label))
>         print("      %s" % todo)
>     return 0
> 
> 
> def outbox_done(tree, ref):
>     for slug, title, path in tree.outbox:
>         if slug == ref:
>             os.remove(path)
>             print('removed outbox note "%s" (%s)' % (title, tree.rel(path)))
>             return 0
>     node = tree.nodes.get(ref)
>     if node is None:
>         print("no outbox note or node called %s" % ref)
>         return 2
>     text = read_text(node.path)
>     nl = "\r\n" if "\r\n" in text else "\n"
>     text = text.replace("\r\n", "\n")
>     text = drop_list_items(text, "tags", lambda t: t.lstrip("#") in ACTIONS)
>     # a paragraph that opens with the tag is a message to the agent and goes whole;
>     # a tag inside a sentence marks the author's own text, so only the tag goes
>     text = re.sub(r"(?m)^[ \t]*#(?:ratify|retire|contest|ask)\b[^\n]*\n?(?:(?![ \t]*(?:[-#|>*]|\d+\.|$))[^\n]+\n?)*", "", text)
>     text = ACTION_TAG_RE.sub("", text)
>     text = re.sub(r"[ \t]+$", "", text, flags=re.M).rstrip("\n") + "\n"
>     write_text(node.path, text.replace("\n", nl))
>     print("cleared the action tags on %s" % node.label())
>     return 0
> 
> 
> def drop_list_items(text, key, pred):
>     """Remove items matching pred from a frontmatter list, inline or block form; drop the key when empty."""
>     lines = text.split("\n")
>     end = lines.index("---", 1)
>     for k in range(1, end):
>         name, _, raw = lines[k].partition(":")
>         if name.strip() != key:
>             continue
>         raw = raw.strip()
>         if raw.startswith("["):
>             items = [x for x in (_scalar(i) for i in raw[1:-1].split(",")) if x]
>             span = (k, k + 1)
>         else:
>             j = k + 1
>             while j < end and lines[j].strip().startswith("- "):
>                 j += 1
>             items = [_scalar(lines[x].strip()[2:]) for x in range(k + 1, j)]
>             span = (k, j)
>         keep = [x for x in items if not pred(x)]
>         new = ["%s: [%s]" % (key, ", ".join(keep))] if keep else []
>         return "\n".join(lines[:span[0]] + new + lines[span[1]:])
>     return text
> 
> 
1064c1263
<         "title: %s" % item.title,
---
>         "title: %s" % fm_str(item.title),
1066c1265
<         "parents: [%s]" % ", ".join(parents),
---
>         "parents: %s" % fm_ids(parents),
1076a1276,1278
>     if item.name:
>         fm.insert(2, "name: %s" % item.name)
>         fm.append("aliases: [%s]" % item.name)
1089c1291
<     print("cite it as dte:%s and re-run validate" % new_id)
---
>     print("cite it as %s and re-run validate" % cite_text([new_id]))
1124c1326
<     tree.append_ledger(node.id, action, successor, by, authorized_by, node.title)
---
>     tree.append_ledger(node.id, action, successor, by, authorized_by, node.summary)
1136c1338
<     text = set_field(text, "superseded_by", successor or "")
---
>     text = set_field(text, "superseded_by", fm_id(successor) if successor else "")
1147,1152d1348
<     tok = re.compile(r"\bdte:([A-Z]\d+(?:\s*,\s*[A-Z]\d+)*)")
< 
<     def swap(m):
<         ids = [new_id if x == old_id else x for x in re.split(r"\s*,\s*", m.group(1))]
<         return "dte:" + ",".join(ids)
< 
1155c1351
<         write_text(path, tok.sub(swap, read_text(path)))
---
>         write_text(path, sub_citations(read_text(path), old_id, new_id))
1163c1359
<         ctext = set_field(ctext, "parents", "[%s]" % ", ".join(ps))
---
>         ctext = set_field(ctext, "parents", fm_ids(ps))
1200c1396
<             t = set_field(t, "supersedes", "[%s]" % ", ".join(new.supersedes + [old_id]))
---
>             t = set_field(t, "supersedes", fm_ids(new.supersedes + [old_id]))
1209c1405
<     print('retired %s "%s"' % (old_id, node.title))
---
>     print('retired %s "%s"' % (old_id, node.summary))
1283,1284c1479,1480
<     text = set_field(text, "parents", "[%s]" % ", ".join(parents))
<     text = set_field(text, "supersedes", "[%s]" % old_id)
---
>     text = set_field(text, "parents", fm_ids(parents))
>     text = set_field(text, "supersedes", fm_ids([old_id]))
1304c1500
<     print('moved %s -> %s "%s" at %s' % (old_id, new_id, node.title, tree.rel(dest)))
---
>     print('moved %s -> %s "%s" at %s' % (old_id, new_id, node.summary, tree.rel(dest)))
1376c1572
<             lines.append("%s: [%s]" % (k, ", ".join(v)))
---
>             lines.append("%s: %s" % (k, fm_ids(v)))
1421c1617
<         ("id", new_id), ("title", args.title), ("status", args.status), ("parents", parents),
---
>         ("id", new_id), ("title", fm_str(args.title)), ("status", args.status), ("parents", parents),
1429a1626,1628
>     if args.name:
>         fields.insert(1, ("name", args.name))
>         fields.append(("aliases", "[%s]" % args.name))   # so [[name]] resolves in Obsidian
1439c1638
<     print("  " + "; ".join(todo + ["cite it as dte:%s from what it governs" % new_id]))
---
>     print("  " + "; ".join(todo + ["cite it as %s from what it governs" % cite_text([new_id])]))
1507c1706
<         hay = (node.id + " " + node.title + " " + node.body).lower()
---
>         hay = (node.id + " " + node.summary + " " + node.body).lower()
1511c1710
<             if q not in (node.id + " " + node.title).lower():
---
>             if q not in (node.id + " " + node.summary).lower():
1551a1751,1752
>     # The contest informed this ratification and is finished; History stays, one line per event.
>     text = re.sub(r"\n## Alternatives considered\n.*?(?=\n## |\Z)", "", text, flags=re.S)
1558c1759
<     print('ratified %s "%s" by %s%s' % (i, node.title, by,
---
>     print('ratified %s "%s" by %s%s' % (i, node.summary, by,
1623,1625c1824,1825
<         m = CITE_RE.search(lines[k])
<         if m:
<             have = re.split(r"\s*,\s*", m.group(1))
---
>         have = cited_ids(lines[k])
>         if have:
1630c1830,1835
<             lines[k] = lines[k][:m.start(1)] + ",".join(have + new) + lines[k][m.end(1):]
---
>             m = CITE_RE.search(lines[k])
>             if m:
>                 lines[k] = lines[k][:m.start(1)] + ",".join(have + new) + lines[k][m.end(1):]
>             else:
>                 last = list(LINK_RE.finditer(lines[k]))[-1]
>                 lines[k] = lines[k][:last.end()] + ", " + ", ".join("[[%s]]" % x for x in new) + lines[k][last.end():]
1634c1839
<     comment = comment_line(ext, "dte:" + ",".join(ids))
---
>     comment = comment_line(ext, cite_text(ids))
1746c1951
<     text = set_field(text, "parents", "[%s]" % ", ".join(parents))
---
>     text = set_field(text, "parents", fm_ids(parents))
1750c1955
<     print('re-parented %s "%s": [%s] -> [%s]' % (args.id, node.title, old, ", ".join(parents)))
---
>     print('re-parented %s "%s": [%s] -> [%s]' % (args.id, node.summary, old, ", ".join(parents)))
1754c1959
< SETTABLE = ("title", "confidence")       # dte:B29 the fields with no invariant
---
> SETTABLE = ("title", "name", "confidence")       # dte:B29 the fields with no invariant
1786c1991
<     old = node.title if field == "title" else (node.confidence or "")
---
>     old = {"title": node.title, "name": node.name}.get(field, node.confidence or "")
1789a1995,1997
>     if field == "name" and not NAME_RE.match(new):
>         print("a name is an identifier like shareImpl or round-2")
>         return 2
1801c2009,2011
<     text = set_field(text, field, new)
---
>     text = set_field(text, field, fm_str(new) if field == "title" else new)
>     if field == "name":
>         text = set_field(text, "aliases", "[%s]" % new)
1923c2133
<     print('recorded contest on %s "%s": %s wins' % (node.id, node.title, args.chosen))
---
>     print('recorded contest on %s "%s": %s wins' % (node.id, node.summary, args.chosen))
1953c2163
<             text = set_field(text, "conflicts_with", "[%s]" % ", ".join(n.conflicts_with + [y]))
---
>             text = set_field(text, "conflicts_with", fm_ids(n.conflicts_with + [y]))
2055a2266,2267
>     ob = sub.add_parser("outbox")
>     ob.add_argument("--done", default=None, metavar="ID|slug", help="clear one processed item")
2078a2291
>     n.add_argument("--name", default=None, help="readable handle, an identifier; becomes the alias")
2135c2348
<         "next": cmd_next, "scope": cmd_scope, "inbox": cmd_inbox, "place": cmd_place,
---
>         "next": cmd_next, "scope": cmd_scope, "inbox": cmd_inbox, "outbox": cmd_outbox, "place": cmd_place,
```
