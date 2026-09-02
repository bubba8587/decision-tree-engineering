#!/usr/bin/env python3
"""dte: Decision Tree Engineering reference tool.  dte:B6

One file, standard library only, Python 3.8+. Copy it into any project.

    python dte.py validate [--as RING]   check the tree; exit 1 on errors
    python dte.py tree [--files]         print the tree ring by ring
    python dte.py blast <ID>             blast radius of a node
    python dte.py trace <path>           why does this artifact exist?
    python dte.py conflicts              declared contradictions and who wins
    python dte.py coverage               artifacts with no citation
    python dte.py next <ring>            next free id in a ring
    python dte.py inbox                  decisions waiting to be placed
    python dte.py place <slug> <ring> --by NAME [--parents A1,B2]
    python dte.py authority [ring]       who holds each ring (whom to ask)

Options: --root DIR (default: cwd)  --decisions DIR (default: ROOT/decisions)
Config:  ROOT/dte.cfg, key = value lines (summaries, protect_human, authority)
"""
import argparse
import datetime
import fnmatch
import os
import re
import subprocess
import sys
from collections import defaultdict

ID_RE = re.compile(r"^([A-Z])(\d+)$")
CITE_RE = re.compile(r"\bdte:([A-Z]\d+(?:\s*,\s*[A-Z]\d+)*)")
STATUSES = {"proposed", "active", "superseded", "reverted"}
MADE_BY = {"human", "ai", "joint"}
LIST_FIELDS = {"parents", "supersedes", "conflicts_with", "aliases"}
KNOWN_FIELDS = LIST_FIELDS | {
    "id", "title", "status", "superseded_by", "made_by", "by", "date",
    "ratified_by", "confidence", "authorized_by",
}
INBOX_FIELDS = {"title", "proposed_ring", "ask", "made_by", "by", "date", "parents", "confidence"}
IN_EFFECT = {"proposed", "active"}
TITLE_MAX = 100          # dte:B16
INBOX_DIR = "inbox"      # dte:B14

DEFAULTS = {"summaries": True, "protect_human": True, "authority": ()}
CONFIG = dict(DEFAULTS)


# ---------------------------------------------------------------- config  dte:B12

def load_config(root):
    cfg = dict(DEFAULTS)
    cfg["authority"] = []
    path = os.path.join(root, "dte.cfg")
    if not os.path.exists(path):
        return cfg
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.split("#", 1)[0].strip()
            if not line or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip()
            if key in ("summaries", "protect_human"):
                cfg[key] = val.lower() in ("on", "true", "yes", "1")
            elif key == "authority":
                for item in val.split(","):
                    if ":" in item:
                        ring, _, holder = item.partition(":")
                        cfg["authority"].append((ring.strip().upper(), holder.strip()))
    return cfg


def holder_of(ring, cfg):
    """Who holds a ring per the advisory map.  dte:B13"""
    best = None
    for key, holder in cfg["authority"]:
        if key == ring:
            return holder
        if key.endswith("+") and ord(key[0]) <= ord(ring):
            if best is None or ord(key[0]) > ord(best[0]):
                best = (key[0], holder)
    return best[1] if best else "the human (ring %s is unmapped)" % ring


# ---------------------------------------------------------------- parsing

def parse_frontmatter(text):
    """Restricted YAML subset: scalars, [inline, lists], block lists.  dte:C1"""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing frontmatter (file must start with ---)")
    data, key, i = {}, None, 1
    while i < len(lines):
        line = lines[i]
        if line.strip() == "---":
            return data, "\n".join(lines[i + 1:])
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        if stripped.startswith("- "):
            if key is None or not isinstance(data.get(key), list):
                raise ValueError("list item without a list key at line %d" % (i + 1))
            data[key].append(_scalar(stripped[2:]))
            i += 1
            continue
        if ":" not in line:
            raise ValueError("cannot parse line %d: %r" % (i + 1, line))
        key, _, raw = line.partition(":")
        key = key.strip()
        raw = _strip_comment(raw.strip())
        if raw == "":
            data[key] = []
            data.setdefault("_empty", set()).add(key)
        elif raw.startswith("[") and raw.endswith("]"):
            inner = raw[1:-1].strip()
            data[key] = [_scalar(x) for x in inner.split(",")] if inner else []
        else:
            data[key] = _scalar(raw)
        i += 1
    raise ValueError("frontmatter never closed")


def _strip_comment(raw):
    if raw.startswith(("'", '"')):
        return raw
    return re.sub(r"\s+#.*$", "", raw)


def _scalar(raw):
    raw = _strip_comment(raw.strip())
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "'\"":
        return raw[1:-1]
    return raw


def _normalise(data):
    empties = data.pop("_empty", set())
    for k in empties:
        if k not in LIST_FIELDS and data.get(k) == []:
            data[k] = None
    return data


class Node:
    def __init__(self, path, data, body):
        self.path = path
        self.body = body
        self.raw = _normalise(data)
        data = self.raw
        self.id = str(data.get("id") or "")
        self.title = str(data.get("title") or "")
        self.status = str(data.get("status") or "")
        self.made_by = str(data.get("made_by") or "")
        self.by = str(data.get("by") or "")
        self.superseded_by = data.get("superseded_by") or None
        self.ratified_by = data.get("ratified_by") or None
        self.authorized_by = data.get("authorized_by") or None
        self.confidence = data.get("confidence") or None
        for f in LIST_FIELDS:
            v = data.get(f)
            if v is None:
                v = []
            if not isinstance(v, list):
                v = [v]
            setattr(self, f, [str(x) for x in v if str(x)])

    @property
    def ring(self):
        m = ID_RE.match(self.id)
        return m.group(1) if m else None

    @property
    def number(self):
        m = ID_RE.match(self.id)
        return int(m.group(2)) if m else 0

    @property
    def in_effect(self):
        return self.status in IN_EFFECT

    @property
    def human_held(self):
        """dte:B11"""
        return self.made_by == "human" or bool(self.ratified_by)

    def label(self):
        if not CONFIG["summaries"]:
            return self.id
        tag = ""
        if self.status != "active":
            tag += " [%s]" % self.status
        if self.made_by != "human":
            tag += " (%s%s)" % (self.made_by, "" if self.ratified_by else ", unratified")
        return "%s %s%s" % (self.id, self.title, tag)


class InboxItem:
    """A decision with no ID yet.  dte:B14"""

    def __init__(self, path, data, body):
        self.path = path
        self.body = body
        self.raw = _normalise(data)
        self.slug = os.path.splitext(os.path.basename(path))[0]
        self.title = str(self.raw.get("title") or "")
        self.proposed_ring = str(self.raw.get("proposed_ring") or "").upper()
        self.ask = str(self.raw.get("ask") or "")
        self.made_by = str(self.raw.get("made_by") or "")
        self.by = str(self.raw.get("by") or "")
        p = self.raw.get("parents") or []
        self.parents = [str(x) for x in (p if isinstance(p, list) else [p]) if str(x)]


def ring_depth(ring):
    return ord(ring) - ord("A")


def id_key(i):
    m = ID_RE.match(i)
    return (m.group(1), int(m.group(2))) if m else ("~", 0)


# ---------------------------------------------------------------- tree

class Tree:
    def __init__(self, root, decisions_dir):
        self.root = os.path.abspath(root)
        self.decisions_dir = os.path.abspath(decisions_dir)
        self.inbox_dir = os.path.join(self.decisions_dir, INBOX_DIR)
        self.nodes = {}
        self.aliases = {}
        self.inbox = []
        self.errors = []
        self.warnings = []
        self.children = defaultdict(list)
        self.citations = []
        self.scanned_files = []
        self._leaf_ids = set()
        self._validated = False
        self._load()

    # -- loading
    def _load(self):
        if not os.path.isdir(self.decisions_dir):
            self.errors.append("decisions dir not found: %s" % self.decisions_dir)
            return
        for dirpath, dirs, files in os.walk(self.decisions_dir):
            if os.path.abspath(dirpath) == os.path.abspath(self.inbox_dir):
                for fn in sorted(files):
                    if fn.endswith(".md"):
                        self._load_inbox(os.path.join(dirpath, fn))
                dirs[:] = []
                continue
            for fn in sorted(files):
                if not fn.endswith(".md") or fn.upper() == "README.MD":
                    continue
                self._load_node(os.path.join(dirpath, fn))
        for node in self.nodes.values():
            for a in node.aliases:
                if a in self.nodes:
                    self.errors.append("%s: alias %s collides with a live id" % (node.id, a))
                elif a in self.aliases:
                    self.errors.append("%s: alias %s also claimed by %s" % (node.id, a, self.aliases[a]))
                else:
                    self.aliases[a] = node.id
        for node in self.nodes.values():
            for p in node.parents:
                r = self.resolve(p)
                if r:
                    self.children[r].append(node.id)

    def _read(self, path):
        with open(path, encoding="utf-8") as fh:
            return parse_frontmatter(fh.read())

    def _load_node(self, path):
        rel = self.rel(path)
        try:
            data, body = self._read(path)
        except (ValueError, UnicodeDecodeError) as e:
            self.errors.append("%s: %s" % (rel, e))
            return
        node = Node(path, data, body)
        if not ID_RE.match(node.id):
            self.errors.append("%s: bad or missing id %r" % (rel, node.id))
            return
        if node.id in self.nodes:
            self.errors.append("%s: duplicate id %s (also %s)"
                               % (rel, node.id, self.rel(self.nodes[node.id].path)))
            return
        self.nodes[node.id] = node

    def _load_inbox(self, path):
        rel = self.rel(path)
        try:
            data, body = self._read(path)
        except (ValueError, UnicodeDecodeError) as e:
            self.errors.append("%s: %s" % (rel, e))
            return
        item = InboxItem(path, data, body)
        for f in item.raw:
            if f not in INBOX_FIELDS:
                self.errors.append("%s: unknown inbox field %r (inbox items have no id or status)" % (rel, f))
        if not item.title:
            self.errors.append("%s: inbox item needs a title" % rel)
        if item.made_by not in MADE_BY:
            self.errors.append("%s: made_by must be one of %s" % (rel, sorted(MADE_BY)))
        self.inbox.append(item)

    def rel(self, path):
        return os.path.relpath(path, self.root).replace(os.sep, "/")

    def resolve(self, i):
        if i in self.nodes:
            return i
        return self.aliases.get(i)

    def ordered(self, ids=None):
        return sorted(ids if ids is not None else self.nodes, key=id_key)

    def ordered_nodes(self):
        return [self.nodes[i] for i in self.ordered()]

    # -- validation (rules R1..R7 in SPEC)
    def validate(self, as_ring=None):
        if self._validated:
            return not self.errors
        self._validated = True
        E, W = self.errors, self.warnings
        for node in self.ordered_nodes():
            i = node.id
            expected = os.path.join(self.decisions_dir, node.ring, i + ".md")
            if os.path.abspath(node.path) != os.path.abspath(expected):
                E.append("%s: file should be at %s" % (i, self.rel(expected)))
            for f in node.raw:
                if f not in KNOWN_FIELDS:
                    E.append("%s: unknown frontmatter field %r" % (i, f))
            if node.status not in STATUSES:
                E.append("%s: status must be one of %s" % (i, sorted(STATUSES)))
            if node.made_by not in MADE_BY:
                E.append("%s: made_by must be one of %s" % (i, sorted(MADE_BY)))
            if not node.by:
                E.append("%s: 'by' is required" % i)
            if not node.title:
                E.append("%s: title is required" % i)
            elif len(node.title) > TITLE_MAX:   # dte:B16
                W.append("%s: title is %d chars; keep the summary under %d" % (i, len(node.title), TITLE_MAX))
            if "## Decision" not in node.body or "## Why" not in node.body:
                E.append("%s: body needs '## Decision' and '## Why' sections" % i)
            # R1 parents  dte:B10
            if node.ring == "A" and node.parents:
                E.append("%s: core (A) nodes cannot have parents" % i)
            if node.ring != "A" and not node.parents:
                E.append("%s: non-core node has no parents" % i)
            for p in node.parents:
                pid = self.resolve(p)
                if pid is None:
                    E.append("%s: parent %s does not exist" % (i, p))
                    continue
                if pid != p:
                    W.append("%s: parent %s is an alias of %s; update it" % (i, p, pid))
                parent = self.nodes[pid]
                if ring_depth(parent.ring) >= ring_depth(node.ring):
                    E.append("%s: parent %s is not in a shallower ring" % (i, pid))
                # R4 orphans  dte:B5
                if node.in_effect and not parent.in_effect:
                    E.append("%s: ORPHAN, parent %s is %s (re-parent, supersede, or revert %s)"
                             % (i, pid, parent.status, i))
                if node.in_effect and parent.status == "proposed":   # dte:C5
                    W.append("%s: parent %s is still proposed (needs ratification)" % (i, pid))
            # supersession  dte:B5
            if node.status == "superseded":
                sb = self.resolve(str(node.superseded_by or ""))
                if not sb:
                    E.append("%s: superseded but superseded_by is missing or unknown" % i)
                elif i not in self.nodes[sb].supersedes:
                    W.append("%s: superseded_by %s, but %s does not list it in supersedes" % (i, sb, sb))
            elif node.superseded_by:
                E.append("%s: superseded_by set but status is %s" % (i, node.status))
            for s in node.supersedes:
                sid = self.resolve(s)
                if sid is None:
                    E.append("%s: supersedes unknown %s" % (i, s))
                elif self.nodes[sid].status != "superseded":
                    E.append("%s: supersedes %s but %s has status %s"
                             % (i, sid, sid, self.nodes[sid].status))
            # R2 conflicts  dte:B4
            for c in node.conflicts_with:
                cid = self.resolve(c)
                if cid is None:
                    E.append("%s: conflicts_with unknown %s" % (i, c))
                elif self.nodes[cid].in_effect and node.in_effect \
                        and self.nodes[cid].ring == node.ring:
                    E.append("%s: same-ring contradiction with %s; supersede or move one" % (i, cid))
            # R7 human-held protection  dte:B11
            if CONFIG["protect_human"] and node.human_held and not node.authorized_by:
                if node.status in ("superseded", "reverted"):
                    E.append("%s: human-held node is %s without authorized_by naming a human"
                             % (i, node.status))
                if node.aliases:
                    E.append("%s: human-held node was moved (aliases %s) without authorized_by"
                             % (i, ", ".join(node.aliases)))
            if node.in_effect and not self.children.get(i):
                self._leaf_ids.add(i)
        # citations  dte:C3
        self.scan()
        for rel, ln, cid, resolved in self.citations:
            if resolved is None:
                E.append("%s:%d: citation to unknown id %s" % (rel, ln, cid))
            elif resolved != cid:
                W.append("%s:%d: citation %s is an alias of %s" % (rel, ln, cid, resolved))
            elif not self.nodes[resolved].in_effect:
                W.append("%s:%d: cites %s which is %s" % (rel, ln, cid, self.nodes[resolved].status))
        cited = {r for _, _, _, r in self.citations if r}
        for i in sorted(self._leaf_ids, key=id_key):
            if i not in cited:
                W.append("%s: in effect but has no children and no citing artifacts" % i)
        if as_ring:
            self._check_authority(as_ring)
        return not E

    def _check_authority(self, as_ring):
        """dte:B15"""
        E, W = self.errors, self.warnings
        as_ring = as_ring.upper()
        changed, exact = self.changed_files()
        if not exact:
            W.append("git unavailable or not a repository; treating every node as changed (--as check is coarse)")
        by_path = {self.rel(n.path): n for n in self.nodes.values()}
        for rel in sorted(changed):
            node = by_path.get(rel)
            if node is None:
                continue
            if ring_depth(node.ring) < ring_depth(as_ring) and not node.authorized_by:
                E.append("%s: changed by an agent at ring %s but lives at ring %s; escalate to %s"
                         % (node.id, as_ring, node.ring, holder_of(node.ring, CONFIG)))
            if CONFIG["protect_human"] and node.human_held and not node.authorized_by:
                E.append("%s: human-held node changed without authorized_by (agent at ring %s)"
                         % (node.id, as_ring))

    def changed_files(self):
        """(set of changed relpaths, exact?)  dte:C6"""
        try:
            out = subprocess.run(
                ["git", "-C", self.root, "status", "--porcelain", "--untracked-files=all"],
                capture_output=True, text=True, check=True).stdout
        except (OSError, subprocess.CalledProcessError):
            return {self.rel(n.path) for n in self.nodes.values()}, False
        changed = set()
        for line in out.splitlines():
            if len(line) < 4:
                continue
            path = line[3:]
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
            changed.add(path.strip('"').replace("\\", "/"))
        return changed, True

    def unratified(self):
        return [n for n in self.ordered_nodes()
                if n.made_by in ("ai", "joint") and not n.ratified_by and n.in_effect]

    # -- scanning  dte:C3
    def _ignores(self):
        pats = []
        p = os.path.join(self.root, ".dteignore")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        pats.append(line)
        return pats

    def _ignored(self, rel, pats):
        parts = rel.split("/")
        for pat in pats:
            pat = pat.rstrip("/")
            if fnmatch.fnmatch(rel, pat) or any(fnmatch.fnmatch(p, pat) for p in parts):
                return True
            if fnmatch.fnmatch(rel, pat + "/*") or rel.startswith(pat + "/"):
                return True
        return False

    def scan(self):
        if self.scanned_files:
            return
        pats = self._ignores()
        dec_rel = self.rel(self.decisions_dir)
        for dirpath, dirs, files in os.walk(self.root):
            dirs[:] = sorted(d for d in dirs if d != ".git"
                             and not self._ignored(self.rel(os.path.join(dirpath, d)), pats))
            for fn in sorted(files):
                path = os.path.join(dirpath, fn)
                rel = self.rel(path)
                if rel == dec_rel or rel.startswith(dec_rel + "/") or self._ignored(rel, pats):
                    continue
                try:
                    with open(path, "rb") as fh:
                        head = fh.read(8192)
                    if b"\x00" in head:
                        continue
                    with open(path, encoding="utf-8", errors="replace") as fh:
                        lines = fh.read().splitlines()
                except OSError:
                    continue
                self.scanned_files.append(rel)
                for ln, line in enumerate(lines, 1):
                    for m in CITE_RE.finditer(line):
                        for cid in re.split(r"\s*,\s*", m.group(1)):
                            self.citations.append((rel, ln, cid, self.resolve(cid)))

    # -- queries
    def descendants(self, i):
        """Transitive children, as {id: depth}.  dte:C2"""
        out, stack = {}, [(c, 1) for c in self.children.get(i, [])]
        while stack:
            c, d = stack.pop()
            if c in out:
                continue
            out[c] = d
            stack.extend((g, d + 1) for g in self.children.get(c, []))
        return out

    def ancestors(self, i):
        node = self.nodes[i]
        if not node.parents:
            return [[i]]
        chains = []
        for p in node.parents:
            pid = self.resolve(p)
            if pid is None:
                chains.append([i, p + "?"])
                continue
            for chain in self.ancestors(pid):
                chains.append([i] + chain)
        return chains


# ---------------------------------------------------------------- commands

def report(tree, show_unratified=True):
    for e in tree.errors:
        print("ERROR   " + e)
    for w in tree.warnings:
        print("WARNING " + w)
    if tree.inbox:
        print_inbox(tree)
    if show_unratified:
        un = tree.unratified()
        if un:
            print("\nUnratified AI/joint decisions (%d):  dte:B7" % len(un))
            for n in un:
                print("  %s  [%s: %s]" % (n.label(), n.made_by, n.by))


def print_inbox(tree):
    """dte:B14"""
    print("\nPENDING PLACEMENT (%d), no ID until placed:" % len(tree.inbox))
    for it in tree.inbox:
        who = it.ask or (holder_of(it.proposed_ring, CONFIG) if it.proposed_ring else "the human")
        ring = ("proposed ring %s" % it.proposed_ring) if it.proposed_ring else "ring unknown"
        print('  %s  "%s"  (%s, %s by %s)' % (it.slug, it.title, ring, it.made_by, it.by))
        print("    ASK %s: where does this belong?  then: dte place %s <ring> --by <name>" % (who, it.slug))


def cmd_validate(tree, args):
    ok = tree.validate(as_ring=args.as_ring)
    report(tree)
    n_cited = len({r for r, _, _, _ in tree.citations})
    print("\n%d nodes, %d pending, %d citations in %d/%d artifacts, %d errors, %d warnings"
          % (len(tree.nodes), len(tree.inbox), len(tree.citations), n_cited,
             len(tree.scanned_files), len(tree.errors), len(tree.warnings)))
    print("OK" if ok else "FAILED")
    return 0 if ok else 1


def cmd_tree(tree, args):
    tree.validate()
    if tree.errors:
        report(tree, show_unratified=False)
        print()
    cited_by = defaultdict(set)
    for rel, _, _, r in tree.citations:
        if r:
            cited_by[r].add(rel)
    seen = set()

    def walk(i, depth):
        node = tree.nodes[i]
        marker = " (again)" if i in seen else ""
        print("  " * depth + node.label() + marker)
        if i in seen:
            return
        seen.add(i)
        if args.files and cited_by.get(i):
            for f in sorted(cited_by[i]):
                print("  " * (depth + 1) + "- " + f)
        for c in tree.ordered(tree.children.get(i, [])):
            walk(c, depth + 1)

    for i in tree.ordered():
        if tree.nodes[i].ring == "A":
            walk(i, 0)
    stray = [i for i in tree.ordered() if tree.nodes[i].ring != "A" and i not in seen]
    if stray:
        print("\nNot reachable from the core:")
        for i in stray:
            print("  " + tree.nodes[i].label())
    if tree.inbox:
        print_inbox(tree)
    return 0


def cmd_blast(tree, args):
    """dte:C2"""
    tree.validate()
    target = tree.resolve(args.id)
    if target is None:
        print("unknown id: %s" % args.id)
        return 2
    node = tree.nodes[target]
    print("BLAST RADIUS of %s\n" % node.label())
    if node.human_held:
        print("  This node is human-held. Changing it needs authorized_by from a human.  dte:B11\n")
    desc = tree.descendants(target)
    by_ring = defaultdict(list)
    for d in desc:
        by_ring[tree.nodes[d].ring].append(d)
    print("Descendant decisions (%d):" % len(desc))
    if not desc:
        print("  none")
    for ring in sorted(by_ring):
        print("  ring %s:" % ring)
        for d in tree.ordered(by_ring[ring]):
            n = tree.nodes[d]
            print("    %s  via %s" % (n.label(), ", ".join(
                p for p in n.parents if tree.resolve(p) in desc or tree.resolve(p) == target)))
    affected = {target} | set(desc)
    hits = defaultdict(list)
    for rel, ln, cid, r in tree.citations:
        if r in affected:
            hits[rel].append((ln, cid))
    print("\nCiting artifacts (%d files):" % len(hits))
    if not hits:
        print("  none")
    for rel in sorted(hits):
        print("  %s  %s" % (rel, ", ".join("%s@%d" % (c, ln) for ln, c in sorted(hits[rel]))))
    if node.supersedes:
        print("\nCurrently superseded by %s (candidates to return if %s is reverted):" % (target, target))
        for s in node.supersedes:
            sid = tree.resolve(s)
            print("  " + (tree.nodes[sid].label() if sid else s + " (unknown)"))
    rings = sorted(set(by_ring) | {node.ring})
    print("\nLayers touched: %s.  %d decisions, %d artifacts."
          % (", ".join(rings), len(affected), len(hits)))
    return 0


def cmd_trace(tree, args):
    tree.validate()
    rel = tree.rel(os.path.abspath(args.path)) if os.path.exists(args.path) else args.path
    cites = [(ln, cid, r) for f, ln, cid, r in tree.citations if f == rel]
    if not cites:
        print("%s: no citations. Nobody has said why this exists.  (dte:A2)" % rel)
        return 1
    print("WHY %s EXISTS\n" % rel)
    seen = set()
    for ln, cid, r in cites:
        if r is None:
            print("  line %d cites unknown %s" % (ln, cid))
            continue
        if r in seen:
            continue
        seen.add(r)
        print("  line %d cites %s" % (ln, r))
        for chain in tree.ancestors(r):
            print("    " + "  <-  ".join(chain))
    order = []
    for r in seen:
        for chain in tree.ancestors(r):
            for i in chain:
                if i in tree.nodes and i not in order:
                    order.append(i)
    order.sort(key=lambda i: (-ring_depth(tree.nodes[i].ring), id_key(i)))
    print("\nDecisions, most specific first:")
    for i in order:
        print("  " + tree.nodes[i].label())
    return 0


def cmd_conflicts(tree, args):
    """dte:B4"""
    tree.validate()
    pairs = set()
    for n in tree.nodes.values():
        for c in n.conflicts_with:
            cid = tree.resolve(c)
            if cid:
                pairs.add(tuple(sorted((n.id, cid), key=id_key)))
    if not pairs:
        print("No declared contradictions.")
        return 0
    for a, b in sorted(pairs, key=lambda p: (id_key(p[0]), id_key(p[1]))):
        na, nb = tree.nodes[a], tree.nodes[b]
        if not (na.in_effect and nb.in_effect):
            verdict = "moot (%s is %s, %s is %s)" % (a, na.status, b, nb.status)
        elif ring_depth(na.ring) < ring_depth(nb.ring):
            verdict = "%s wins (ring %s over %s)" % (a, na.ring, nb.ring)
        elif ring_depth(na.ring) > ring_depth(nb.ring):
            verdict = "%s wins (ring %s over %s)" % (b, nb.ring, na.ring)
        else:
            verdict = "UNRESOLVED: same ring; supersede or move one"
        print("%s  vs  %s  ->  %s" % (na.label(), nb.label(), verdict))
    return 0


def cmd_coverage(tree, args):
    """dte:C4"""
    tree.scan()
    cited = {r for r, _, _, _ in tree.citations}
    missing = [f for f in tree.scanned_files if f not in cited]
    total = len(tree.scanned_files)
    pct = 100.0 * (total - len(missing)) / total if total else 0.0
    print("Coverage: %d/%d artifacts cite a decision (%.1f%%)\n" % (total - len(missing), total, pct))
    if missing:
        print("No citation:")
        for f in missing:
            print("  " + f)
    return 0


def next_id(tree, ring):
    used = [n.number for n in tree.nodes.values() if n.ring == ring]
    used += [int(ID_RE.match(a).group(2)) for a in tree.aliases if a.startswith(ring)]
    return "%s%d" % (ring, (max(used) + 1) if used else 1)


def cmd_next(tree, args):
    ring = args.ring.upper()
    if not re.match(r"^[A-Z]$", ring):
        print("ring must be a single letter A-Z")
        return 2
    print(next_id(tree, ring))
    return 0


def cmd_inbox(tree, args):
    """dte:B14"""
    if not tree.inbox:
        print("Inbox empty. Nothing waiting to be placed.")
        return 0
    print_inbox(tree)
    return 0


def cmd_place(tree, args):
    """dte:B14"""
    ring = args.ring.upper()
    if not re.match(r"^[A-Z]$", ring):
        print("ring must be a single letter A-Z")
        return 2
    item = next((it for it in tree.inbox if it.slug == args.slug), None)
    if item is None:
        print("no inbox item named %r; run: dte inbox" % args.slug)
        return 2
    parents = [p.strip() for p in (args.parents or "").split(",") if p.strip()] or item.parents
    if ring == "A" and parents:
        print("ring A nodes cannot have parents")
        return 2
    if ring != "A" and not parents:
        print("a ring %s node needs parents; pass --parents A1,B2" % ring)
        return 2
    for p in parents:
        pid = tree.resolve(p)
        if pid is None:
            print("parent %s does not exist" % p)
            return 2
        if ring_depth(tree.nodes[pid].ring) >= ring_depth(ring):
            print("parent %s is not shallower than ring %s" % (pid, ring))
            return 2
    new_id = next_id(tree, ring)
    today = datetime.date.today().isoformat()
    fm = [
        "---",
        "id: %s" % new_id,
        "title: %s" % item.title,
        "status: active",
        "parents: [%s]" % ", ".join(parents),
        "supersedes: []",
        "superseded_by:",
        "conflicts_with: []",
        "aliases: []",
        "made_by: %s" % item.made_by,
        "by: %s" % item.by,
        "date: %s" % (item.raw.get("date") or today),
        "ratified_by:",
    ]
    if item.raw.get("confidence"):
        fm.append("confidence: %s" % item.raw["confidence"])
    fm.append("---")
    body = item.body.rstrip("\n")
    history = "\n\n## History\n\n" if "## History" not in body else "\n"
    body += history + "- %s placed at ring %s as %s by %s (from inbox/%s).\n" % (
        today, ring, new_id, args.by, item.slug)
    dest_dir = os.path.join(tree.decisions_dir, ring)
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, new_id + ".md")
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write("\n".join(fm) + "\n" + body)
    os.remove(item.path)
    print('placed %s "%s" at %s' % (new_id, item.title, tree.rel(dest)))
    print("cite it as dte:%s and re-run validate" % new_id)
    return 0


def cmd_authority(tree, args):
    """dte:B13"""
    if not CONFIG["authority"]:
        print("No authority map in dte.cfg. Default: ask the human for everything above your ring.")
    else:
        print("Authority map (advisory; binds agents, never humans):")
        for key, holder in CONFIG["authority"]:
            print("  %-3s %s" % (key, holder))
    rings = sorted({n.ring for n in tree.nodes.values()} | ({args.ring.upper()} if args.ring else set()))
    print("\nWhom to ask, per ring in use:")
    for r in rings:
        print("  %s: %s" % (r, holder_of(r, CONFIG)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dte", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--decisions", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate")
    v.add_argument("--as", dest="as_ring", default=None, metavar="RING",
                   help="check changed nodes against an agent's ring (B15)")
    t = sub.add_parser("tree")
    t.add_argument("--files", action="store_true", help="show citing artifacts under each node")
    sub.add_parser("blast").add_argument("id")
    sub.add_parser("trace").add_argument("path")
    sub.add_parser("conflicts")
    sub.add_parser("coverage")
    sub.add_parser("next").add_argument("ring")
    sub.add_parser("inbox")
    p = sub.add_parser("place")
    p.add_argument("slug")
    p.add_argument("ring")
    p.add_argument("--by", required=True, help="who is placing it")
    p.add_argument("--parents", default=None, help="comma-separated parent ids")
    a = sub.add_parser("authority")
    a.add_argument("ring", nargs="?", default=None)
    args = ap.parse_args(argv)
    CONFIG.clear()
    CONFIG.update(load_config(args.root))
    decisions = args.decisions or os.path.join(args.root, "decisions")
    tree = Tree(args.root, decisions)
    return {
        "validate": cmd_validate, "tree": cmd_tree, "blast": cmd_blast,
        "trace": cmd_trace, "conflicts": cmd_conflicts, "coverage": cmd_coverage,
        "next": cmd_next, "inbox": cmd_inbox, "place": cmd_place,
        "authority": cmd_authority,
    }[args.cmd](tree, args)


if __name__ == "__main__":
    sys.exit(main())
