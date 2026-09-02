"""Tests for tools/dte.py.  dte:B6,C2,B4,B5,B11,B14,B15

Run: python -m unittest discover -s tests
"""
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import dte  # noqa: E402

NODE = """---
id: {id}
title: {title}
status: {status}
parents: [{parents}]
supersedes: [{supersedes}]
superseded_by: {superseded_by}
conflicts_with: [{conflicts}]
aliases: [{aliases}]
made_by: {made_by}
by: tester
date: 2026-09-02
ratified_by: {ratified_by}
authorized_by: {authorized_by}
---

## Decision
x

## Why
y
"""

INBOX = """---
title: {title}
proposed_ring: {ring}
ask: {ask}
made_by: ai
by: tester-agent
date: 2026-09-02
parents: [{parents}]
---

## Decision
z

## Why
w
"""


def write_node(root, **kw):
    kw.setdefault("title", kw["id"] + " title")
    for f in ("status",):
        kw.setdefault(f, "active")
    for f in ("parents", "supersedes", "superseded_by", "conflicts", "aliases",
              "ratified_by", "authorized_by"):
        kw.setdefault(f, "")
    kw.setdefault("made_by", "human")
    ring = kw["id"][0]
    d = os.path.join(root, "decisions", ring)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, kw["id"] + ".md"), "w", encoding="utf-8") as fh:
        fh.write(NODE.format(**kw))


def write_inbox(root, slug, title, ring="", ask="", parents=""):
    d = os.path.join(root, "decisions", "inbox")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, slug + ".md"), "w", encoding="utf-8") as fh:
        fh.write(INBOX.format(title=title, ring=ring, ask=ask, parents=parents))


def write_file(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)


def run(root, *argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = dte.main(["--root", root] + list(argv))
    return code, buf.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        write_node(self.root, id="A1")
        write_node(self.root, id="B1", parents="A1", made_by="ai")
        write_node(self.root, id="B2", parents="A1")
        write_node(self.root, id="C1", parents="B1")
        write_file(self.root, "src/a.py", "# dte:C1\nprint(1)\n")
        write_file(self.root, "src/b.py", "# dte:B2\n")
        write_file(self.root, "src/none.py", "print(2)\n")

    def tearDown(self):
        self.tmp.cleanup()


class TestValidate(Base):
    def test_clean_tree_passes(self):
        code, out = run(self.root, "validate")
        self.assertEqual(code, 0, out)
        self.assertIn("OK", out)
        self.assertIn("B1", out.split("Unratified")[1])

    def test_unknown_citation_is_error(self):
        token = "dte" + ":Z9"  # split so this repo's own scanner ignores it
        write_file(self.root, "src/c.py", "# %s\n" % token)
        code, out = run(self.root, "validate")
        self.assertEqual(code, 1)
        self.assertIn("unknown id Z9", out)

    def test_parent_must_be_shallower(self):
        write_node(self.root, id="B3", parents="B1")
        code, out = run(self.root, "validate")
        self.assertEqual(code, 1)
        self.assertIn("not in a shallower ring", out)

    def test_orphan_after_revert(self):
        # dte:B5  reverting B1 must surface C1
        write_node(self.root, id="B1", parents="A1", status="reverted", made_by="ai")
        code, out = run(self.root, "validate")
        self.assertEqual(code, 1)
        self.assertIn("C1: ORPHAN", out)

    def test_same_ring_conflict_is_error(self):
        # dte:B4
        write_node(self.root, id="B2", parents="A1", conflicts="B1")
        code, out = run(self.root, "validate")
        self.assertEqual(code, 1)
        self.assertIn("same-ring contradiction", out)

    def test_alias_resolves_with_warning(self):
        # dte:B2  move B2 -> C2, keep alias (AI-made so no human-held check)
        os.remove(os.path.join(self.root, "decisions", "B", "B2.md"))
        write_node(self.root, id="C2", parents="A1", aliases="B2", made_by="ai")
        code, out = run(self.root, "validate")
        self.assertEqual(code, 0, out)
        self.assertIn("B2 is an alias of C2", out)

    def test_long_title_warns(self):
        # dte:B16
        write_node(self.root, id="B3", parents="A1", title="x" * 120)
        code, out = run(self.root, "validate")
        self.assertEqual(code, 0)
        self.assertIn("B3: title is 120 chars", out)


class TestHumanHeld(Base):
    """dte:B11"""

    def test_reverting_human_node_needs_authorization(self):
        write_node(self.root, id="B2", parents="A1", status="reverted")
        code, out = run(self.root, "validate")
        self.assertEqual(code, 1)
        self.assertIn("B2: human-held node is reverted without authorized_by", out)

    def test_authorized_revert_passes(self):
        write_node(self.root, id="B2", parents="A1", status="reverted", authorized_by="owner")
        code, out = run(self.root, "validate")
        self.assertEqual(code, 0, out)

    def test_ratified_ai_node_is_human_held(self):
        write_node(self.root, id="B1", parents="A1", made_by="ai", ratified_by="owner",
                   status="superseded", superseded_by="B3")
        write_node(self.root, id="B3", parents="A1", supersedes="B1", made_by="ai")
        write_node(self.root, id="C1", parents="B3")
        code, out = run(self.root, "validate")
        self.assertEqual(code, 1)
        self.assertIn("B1: human-held node is superseded without authorized_by", out)

    def test_protection_can_be_configured_off(self):
        write_file(self.root, "dte.cfg", "protect_human = off\n")
        write_node(self.root, id="B2", parents="A1", status="reverted")
        code, out = run(self.root, "validate")
        self.assertEqual(code, 0, out)

    def test_blast_flags_human_held(self):
        code, out = run(self.root, "blast", "A1")
        self.assertIn("human-held", out)


class TestInbox(Base):
    """dte:B14"""

    def test_inbox_is_listed_with_ask(self):
        write_file(self.root, "dte.cfg", "authority = A:human, B:orchestrator, C+:subagent\n")
        write_inbox(self.root, "new-goal", "Some new goal", ring="A")
        code, out = run(self.root, "validate")
        self.assertEqual(code, 0, out)
        self.assertIn("PENDING PLACEMENT (1)", out)
        self.assertIn("ASK human", out)
        self.assertIn("1 pending", out)

    def test_place_assigns_id_and_removes_inbox(self):
        write_inbox(self.root, "new-rule", "A new rule", ring="B", parents="A1")
        code, out = run(self.root, "place", "new-rule", "B", "--by", "owner")
        self.assertEqual(code, 0, out)
        self.assertIn('placed B3 "A new rule"', out)
        self.assertFalse(os.path.exists(os.path.join(self.root, "decisions", "inbox", "new-rule.md")))
        with open(os.path.join(self.root, "decisions", "B", "B3.md"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("id: B3", text)
        self.assertIn("placed at ring B as B3 by owner", text)
        code, out = run(self.root, "validate")
        self.assertEqual(code, 0, out)

    def test_place_refuses_without_parents(self):
        write_inbox(self.root, "new-rule", "A new rule")
        code, out = run(self.root, "place", "new-rule", "B", "--by", "owner")
        self.assertEqual(code, 2)
        self.assertIn("needs parents", out)


class TestAuthority(Base):
    """dte:B13, dte:B15, dte:C6"""

    def _git(self, *a):
        return subprocess.run(["git", "-C", self.root] + list(a), capture_output=True, text=True)

    def _init_repo(self):
        if self._git("init", "-q").returncode != 0:
            self.skipTest("git not available")
        self._git("config", "user.email", "t@example.com")
        self._git("config", "user.name", "t")
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "base")

    def test_authority_map(self):
        write_file(self.root, "dte.cfg", "authority = A:human, B:orchestrator, C+:subagent\n")
        code, out = run(self.root, "authority", "D")
        self.assertIn("C: subagent", out)
        self.assertIn("D: subagent", out)
        self.assertIn("A: human", out)

    def test_agent_changing_shallower_ring_is_error(self):
        write_file(self.root, "dte.cfg", "authority = A:human, B:orchestrator, C+:subagent\n")
        self._init_repo()
        write_node(self.root, id="B3", parents="A1", made_by="ai")   # new B node by a C agent
        code, out = run(self.root, "validate", "--as", "C")
        self.assertEqual(code, 1)
        self.assertIn("B3: changed by an agent at ring C but lives at ring B; escalate to orchestrator", out)

    def test_authorized_change_above_ring_passes(self):
        self._init_repo()
        write_node(self.root, id="A2", authorized_by="owner")   # scribed for the human
        code, out = run(self.root, "validate", "--as", "B")
        self.assertEqual(code, 0, out)

    def test_validate_lists_changed_nodes(self):
        # dte:C7
        self._init_repo()
        write_node(self.root, id="C2", parents="B1", made_by="ai", title="a fresh node")
        code, out = run(self.root, "validate")
        self.assertIn("Nodes changed in this working tree", out)
        self.assertIn("C2 a fresh node", out)

    def test_agent_within_ring_passes(self):
        self._init_repo()
        write_node(self.root, id="C2", parents="B1", made_by="ai")
        code, out = run(self.root, "validate", "--as", "C")
        self.assertEqual(code, 0, out)

    def test_agent_touching_human_node_is_error(self):
        self._init_repo()
        write_node(self.root, id="B2", parents="A1", title="edited by ai")
        code, out = run(self.root, "validate", "--as", "B")
        self.assertEqual(code, 1)
        self.assertIn("B2: human-held node changed without authorized_by", out)


class TestScope(Base):
    """dte:B21, dte:C8"""

    def test_no_reach(self):
        write_node(self.root, id="B3", parents="A1", made_by="ai")
        write_file(self.root, "README.md", "dte:B3 described only\n")
        code, out = run(self.root, "scope")
        self.assertIn("NO REACH (1)", out)
        self.assertIn("B3 B3 title", out)

    def test_broad(self):
        write_file(self.root, "dte.cfg", "broad_min = 2\nbroad_fraction = 0.5\n")
        write_file(self.root, "src/c.py", "# dte:B1\n")
        write_file(self.root, "src/d.py", "# dte:B1\n")
        code, out = run(self.root, "scope")
        self.assertIn("BROAD (1)", out)
        self.assertIn("B1 B1 title", out)
        self.assertIn("promote it, or split it", out)

    def test_skipped_ring(self):
        write_node(self.root, id="C2", parents="A1")
        code, out = run(self.root, "scope")
        self.assertIn("SKIPPED RING (1)", out)
        self.assertIn("a ring B decision is missing, or C2 belongs at ring B", out)

    def test_core_only_code(self):
        write_file(self.root, "src/e.py", "# %s\n" % ("dte" + ":A1"))
        code, out = run(self.root, "scope")
        self.assertIn("CORE-ONLY CODE (1)", out)
        self.assertIn("src/e.py:1", out)

    def test_docs_do_not_count_as_reach(self):
        write_node(self.root, id="B3", parents="A1", made_by="ai")
        write_file(self.root, "notes/x.txt", "dte:B3\n")
        write_file(self.root, "dte.cfg", "docs = notes/*\n")
        code, out = run(self.root, "scope")
        self.assertIn("NO REACH (1)", out)

    def test_validate_mentions_findings(self):
        write_node(self.root, id="C2", parents="A1")
        code, out = run(self.root, "validate")
        self.assertIn("scope findings (advisory)", out)


class TestQueries(Base):
    def test_blast_lists_descendants_and_artifacts(self):
        # dte:C2
        code, out = run(self.root, "blast", "B1")
        self.assertEqual(code, 0)
        self.assertIn("C1", out)
        self.assertIn("src/a.py", out)
        self.assertNotIn("src/b.py", out)
        self.assertIn("Layers touched: B, C", out)

    def test_blast_shows_superseded(self):
        write_node(self.root, id="B2", parents="A1", status="superseded", superseded_by="B3",
                   authorized_by="owner")
        write_node(self.root, id="B3", parents="A1", supersedes="B2")
        code, out = run(self.root, "blast", "B3")
        self.assertIn("candidates to return", out)
        self.assertIn("B2", out)

    def test_conflict_resolved_by_ring(self):
        write_node(self.root, id="C1", parents="B1", conflicts="B2")
        code, out = run(self.root, "conflicts")
        self.assertIn("->  B2 wins (ring B over C)", out)

    def test_trace_walks_to_core(self):
        code, out = run(self.root, "trace", os.path.join(self.root, "src", "a.py"))
        self.assertEqual(code, 0)
        self.assertIn("C1  <-  B1  <-  A1", out)

    def test_coverage(self):
        code, out = run(self.root, "coverage")
        self.assertIn("2/3", out)
        self.assertIn("src/none.py", out)

    def test_next_skips_aliases(self):
        os.remove(os.path.join(self.root, "decisions", "B", "B2.md"))
        write_node(self.root, id="C2", parents="A1", aliases="B2", made_by="ai")
        self.assertEqual(run(self.root, "next", "B")[1].strip(), "B3")
        self.assertEqual(run(self.root, "next", "D")[1].strip(), "D1")

    def test_summaries_off_prints_bare_ids(self):
        # dte:B16
        write_file(self.root, "dte.cfg", "summaries = off\n")
        code, out = run(self.root, "tree")
        self.assertIn("A1\n", out)
        self.assertNotIn("A1 title", out)


if __name__ == "__main__":
    unittest.main()
