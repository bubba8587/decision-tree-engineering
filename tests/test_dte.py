"""Tests for tools/dte.py.  dte:B6,C2,B4,B24,B11,B14,B15,C11

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
    for f in ("parents", "supersedes", "superseded_by", "conflicts",
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
        write_file(self.root, "src/b.py", "# %s\n" % ("dte" + ":B2"))  # split: not a citation here
        write_file(self.root, "src/none.py", "print(2)\n")

    def tearDown(self):
        self.tmp.cleanup()

    def _git(self, *a):
        return subprocess.run(["git", "-C", self.root] + list(a), capture_output=True, text=True)

    def _init_repo(self):
        if self._git("init", "-q").returncode != 0:
            self.skipTest("git not available")
        self._git("config", "user.email", "t@example.com")
        self._git("config", "user.name", "t")
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "base")

    def _read(self, rel):
        with open(os.path.join(self.root, rel), encoding="utf-8") as fh:
            return fh.read()


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
        # dte:B24  reverting B1 must surface C1
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

    def test_aliases_field_is_rejected(self):
        # dte:B23
        p = os.path.join(self.root, "decisions", "B", "B1.md")
        with open(p, encoding="utf-8") as fh:
            text = fh.read()
        write_file(self.root, "decisions/B/B1.md", text.replace("made_by:", "aliases: [B9]\nmade_by:"))
        code, out = run(self.root, "validate")
        self.assertEqual(code, 1)
        self.assertIn("unknown frontmatter field 'aliases'", out)

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

    def test_demotion_touches_the_shallower_file(self):
        # dte:B23  the alias back door is closed: demoting B1 means editing a B file
        self._init_repo()
        code, out = run(self.root, "move", "B1", "C", "--by", "agent", "--parents", "B2")
        self.assertEqual(code, 2)  # C1 is a child at ring C, refused
        write_node(self.root, id="B3", parents="A1", made_by="ai")
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "b3")
        code, out = run(self.root, "move", "B3", "C", "--by", "agent", "--parents", "B2")
        self.assertEqual(code, 0, out)
        code, out = run(self.root, "validate", "--as", "C")
        self.assertEqual(code, 1)
        self.assertIn("B3: retired by an agent at ring C but lived at ring B", out)

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

    def test_renamed_node_file_is_error(self):
        # dte:C11  git mv is not a move
        self._init_repo()
        self._git("mv", "decisions/B/B2.md", "decisions/B/B9.md")
        code, out = run(self.root, "validate")
        self.assertEqual(code, 1)
        self.assertIn("decisions/B/B2.md: node file renamed", out)

    def test_placing_inbox_item_is_not_a_deletion(self):
        write_inbox(self.root, "thing", "A thing", ring="B", parents="A1")
        self._init_repo()
        code, out = run(self.root, "place", "thing", "B", "--by", "owner")
        self.assertEqual(code, 0, out)
        code, out = run(self.root, "validate")
        self.assertEqual(code, 0, out)

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


class TestMove(Base):
    """dte:B23, dte:C9, dte:B24"""

    def test_move_deletes_old_and_rewrites_everything(self):
        write_node(self.root, id="D1", parents="C1", made_by="ai")
        self._init_repo()
        code, out = run(self.root, "move", "C1", "B", "--by", "owner", "--parents", "A1",
                        "--authorized-by", "owner")  # C1 is human-made in the fixture
        self.assertEqual(code, 0, out)
        self.assertIn("moved C1 -> B3", out)
        self.assertIn("DROPPED parents: B1", out)
        self.assertIn("file deleted, ledger line written", out)
        self.assertFalse(os.path.exists(os.path.join(self.root, "decisions", "C", "C1.md")))
        ledger = self._read("decisions/RETIRED")
        self.assertIn("C1\t", ledger)
        self.assertIn("\tmoved\tB3\towner\towner\t", ledger)
        new = self._read("decisions/B/B3.md")
        self.assertIn("id: B3", new)
        self.assertIn("parents: [A1]", new)
        self.assertIn("supersedes: [C1]", new)
        self.assertIn("moved from C1 to ring B as B3 by owner", new)
        self.assertIn("dte:B3", self._read("src/a.py"))
        self.assertNotIn("dte:C1", self._read("src/a.py"))
        self.assertIn("parents: [B3]", self._read("decisions/D/D1.md"))
        code, out = run(self.root, "validate")
        self.assertEqual(code, 0, out)
        self.assertEqual(run(self.root, "next", "C")[1].strip(), "C2")  # C1 burned

    def test_move_in_keep_mode_keeps_file_with_status(self):
        write_file(self.root, "dte.cfg", "retire = keep\n")
        self._init_repo()
        code, out = run(self.root, "move", "C1", "B", "--by", "owner", "--parents", "A1",
                        "--authorized-by", "owner")
        self.assertEqual(code, 0, out)
        old = self._read("decisions/C/C1.md")
        self.assertIn("status: superseded", old)
        self.assertIn("superseded_by: B3", old)
        self.assertIn("C1\t", self._read("decisions/RETIRED"))
        code, out = run(self.root, "validate")
        self.assertEqual(code, 0, out)

    def test_delete_mode_without_git_falls_back_to_keep(self):
        code, out = run(self.root, "move", "C1", "B", "--by", "owner", "--parents", "A1",
                        "--authorized-by", "owner")
        self.assertEqual(code, 0, out)
        self.assertIn("needs git", out)
        self.assertTrue(os.path.exists(os.path.join(self.root, "decisions", "C", "C1.md")))

    def test_move_keeps_parents_that_are_still_shallower(self):
        write_node(self.root, id="C2", parents="A1, B1", made_by="ai")
        self._init_repo()
        code, out = run(self.root, "move", "C2", "B", "--by", "owner")
        self.assertEqual(code, 0, out)
        self.assertIn("parents: A1", out)
        self.assertIn("DROPPED parents: B1", out)

    def test_move_of_human_held_needs_authorization(self):
        code, out = run(self.root, "move", "B2", "C", "--by", "agent", "--parents", "B1")
        self.assertEqual(code, 2)
        self.assertIn("human-held", out)
        self._init_repo()
        code, out = run(self.root, "move", "B2", "C", "--by", "agent", "--parents", "B1",
                        "--authorized-by", "owner")
        self.assertEqual(code, 0, out)
        self.assertIn("B2\t", self._read("decisions/RETIRED"))
        self.assertIn("\towner\t", self._read("decisions/RETIRED"))
        code, out = run(self.root, "validate", "--as", "C")
        self.assertEqual(code, 0, out)

    def test_move_refuses_when_child_would_not_be_deeper(self):
        code, out = run(self.root, "move", "B1", "C", "--by", "agent", "--parents", "B2")
        self.assertEqual(code, 2)
        self.assertIn("child C1", out)


class TestRetire(Base):
    """dte:B24, dte:C11"""

    def test_supersede_rewrites_and_deletes(self):
        write_node(self.root, id="B3", parents="A1", made_by="ai")
        self._init_repo()
        code, out = run(self.root, "retire", "B1", "--by", "agent", "--superseded-by", "B3")
        self.assertEqual(code, 0, out)
        self.assertIn("REVIEW", out)
        self.assertIn("C1 C1 title", out)
        self.assertFalse(os.path.exists(os.path.join(self.root, "decisions", "B", "B1.md")))
        self.assertIn("supersedes: [B1]", self._read("decisions/B/B3.md"))
        self.assertIn("parents: [B3]", self._read("decisions/C/C1.md"))
        self.assertIn("B1\t", self._read("decisions/RETIRED"))
        self.assertIn("\tsuperseded\tB3\t", self._read("decisions/RETIRED"))
        code, out = run(self.root, "validate")
        self.assertEqual(code, 0, out)
        self.assertEqual(run(self.root, "next", "B")[1].strip(), "B4")

    def test_revert_leaves_references_failing_with_hint(self):
        self._init_repo()
        code, out = run(self.root, "retire", "B1", "--by", "agent")
        self.assertEqual(code, 0, out)
        self.assertIn("blast radius of the revert", out)
        code, out = run(self.root, "validate")
        self.assertEqual(code, 1)
        self.assertIn("C1: ORPHAN, parent B1 was retired on", out)
        self.assertIn("reverted", out)
        self.assertIn("git log --all -- decisions/B/B1.md", out)

    def test_citing_a_retired_id_is_an_error_with_hint(self):
        self._init_repo()
        run(self.root, "retire", "B1", "--by", "agent")
        write_file(self.root, "src/z.py", "# %s\n" % ("dte" + ":B1"))
        code, out = run(self.root, "validate")
        self.assertIn("src/z.py:1: cites B1, which was retired", out)

    def test_retire_human_held_needs_authorization(self):
        self._init_repo()
        code, out = run(self.root, "retire", "B2", "--by", "agent")
        self.assertEqual(code, 2)
        self.assertIn("human-held", out)
        code, out = run(self.root, "retire", "B2", "--by", "agent", "--authorized-by", "owner")
        self.assertEqual(code, 0, out)
        self.assertIn("\towner\t", self._read("decisions/RETIRED"))

    def test_manual_deletion_without_ledger_is_error(self):
        write_node(self.root, id="C2", parents="B1", made_by="ai")
        self._init_repo()
        os.remove(os.path.join(self.root, "decisions", "C", "C2.md"))
        code, out = run(self.root, "validate")
        self.assertEqual(code, 1)
        self.assertIn("deleted with no ledger line; use dte retire", out)

    def test_deletion_in_keep_mode_is_error_even_with_ledger(self):
        write_node(self.root, id="C2", parents="B1", made_by="ai")
        self._init_repo()
        run(self.root, "retire", "C2", "--by", "agent")   # delete mode: file gone, ledger written
        write_file(self.root, "dte.cfg", "retire = keep\n")
        code, out = run(self.root, "validate")
        self.assertEqual(code, 1)
        self.assertIn("retire = keep", out)

    def test_agent_deleting_shallower_node_is_error(self):
        write_node(self.root, id="B3", parents="A1", made_by="ai")
        self._init_repo()
        run(self.root, "retire", "B3", "--by", "agent")
        code, out = run(self.root, "validate", "--as", "C")
        self.assertEqual(code, 1)
        self.assertIn("B3: retired by an agent at ring C but lived at ring B", out)

    def test_agent_deleting_human_node_checked_against_head(self):
        self._init_repo()
        # bypass the command: write the ledger by hand and delete the human-made B2
        write_file(self.root, "decisions/RETIRED", "B2\t2026-09-02\treverted\t-\tagent\t-\tB2 title\n")
        os.remove(os.path.join(self.root, "decisions", "B", "B2.md"))
        os.remove(os.path.join(self.root, "src", "b.py"))
        code, out = run(self.root, "validate", "--as", "B")
        self.assertEqual(code, 1)
        self.assertIn("B2: human-held node deleted without authorized_by in the ledger", out)

    def test_blast_lists_retired_predecessor(self):
        write_node(self.root, id="B3", parents="A1", made_by="ai")
        self._init_repo()
        run(self.root, "retire", "B1", "--by", "agent", "--superseded-by", "B3")
        code, out = run(self.root, "blast", "B3")
        self.assertIn("candidates to return", out)
        self.assertIn('B1 "B1 title"', out)
        self.assertIn("git log --all", out)


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

    def test_next_never_reuses_retired_numbers(self):
        # dte:B24  the ledger burns numbers even with the file gone
        write_file(self.root, "decisions/RETIRED", "B7\t2026-09-02\treverted\t-\tx\t-\tgone\n")
        self.assertEqual(run(self.root, "next", "B")[1].strip(), "B8")
        self.assertEqual(run(self.root, "next", "D")[1].strip(), "D1")

    def test_summaries_off_prints_bare_ids(self):
        # dte:B16
        write_file(self.root, "dte.cfg", "summaries = off\n")
        code, out = run(self.root, "tree")
        self.assertIn("A1\n", out)
        self.assertNotIn("A1 title", out)


if __name__ == "__main__":
    unittest.main()
