"""Tests for tools/dte.py.  dte:B6,C2,B4,B24,B11,B14,B15,B29,B27

Run: python -m unittest discover -s tests
"""
import io
import json
import re
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
uuid: {uuid}
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
{aliases}---

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
    kw.setdefault("uuid", dte.new_uuid(0, kw["id"]))
    kw["aliases"] = ("aliases: [%s]\n" % kw.pop("name")) if kw.get("name") else ""
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
        code, out = run(self.root, "validate", "--full")
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

    def test_aliases_must_equal_name(self):
        # dte:B32 a handle bound to the node, never a second identity
        p = os.path.join(self.root, "decisions", "B", "B1.md")
        with open(p, encoding="utf-8") as fh:
            text = fh.read()
        write_file(self.root, "decisions/B/B1.md", text.replace("made_by:", "aliases: [oneName, twoName]\nmade_by:"))
        code, out = run(self.root, "validate")
        self.assertEqual(code, 1)
        self.assertIn("aliases holds one name, not 2", out)
        write_file(self.root, "decisions/B/B1.md", text.replace("made_by:", "aliases: [B9]\nmade_by:"))
        code, out = run(self.root, "validate")
        self.assertIn("dte set B1 name <camelCase>", out)   # feedback item 1: the error names the fix

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
        self.assertIn("B2: human-held leaf is reverted without authorized_by", out)

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
        self.assertIn("B1: human-held leaf is superseded without authorized_by", out)

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
    """dte:B13, dte:B15, dte:B15"""

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
        # dte:B32  the alias back door is closed: demoting B1 means editing a B file
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
        # dte:B17
        self._init_repo()
        write_node(self.root, id="C2", parents="B1", made_by="ai", title="a fresh node")
        code, out = run(self.root, "validate")
        self.assertIn("Leaves changed in this working tree", out)
        self.assertIn("C2 a fresh node", out)

    def test_renamed_node_file_is_error(self):
        # dte:B24  git mv is not a move
        self._init_repo()
        self._git("mv", "decisions/B/B2.md", "decisions/B/B9.md")
        code, out = run(self.root, "validate")
        self.assertEqual(code, 1)
        self.assertIn("decisions/B/B2.md: leaf file renamed", out)

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
        self.assertIn("B2: human-held leaf changed without authorized_by", out)


class TestScope(Base):
    """dte:B21, dte:B21"""

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
        write_node(self.root, id="A1", made_by="ai")
        write_node(self.root, id="C2", parents="A1", made_by="ai")
        code, out = run(self.root, "scope")
        self.assertIn("SKIPPED RING (1)", out)
        self.assertIn("a ring B decision is missing, or C2 belongs at ring B", out)

    def test_a_skip_the_owner_made_or_accepted_is_not_a_finding(self):
        # feedback item 4: a skip under a human-held parent, or on a human-held leaf, is deliberate
        write_node(self.root, id="C2", parents="A1", made_by="ai")   # A1 is human-made in the fixture
        self.assertNotIn("SKIPPED RING", run(self.root, "scope")[1])
        write_node(self.root, id="A1", made_by="ai")
        write_node(self.root, id="C2", parents="A1", made_by="ai", ratified_by="owner")
        self.assertNotIn("SKIPPED RING", run(self.root, "scope")[1])

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
    """dte:B32, dte:B32, dte:B24"""

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
        self.assertNotIn("supersedes: [C1]", new)   # the ledger line is the record (B43)
        self.assertIn("moved from C1 to ring B as B3 by owner", new)
        self.assertIn("C1", run(self.root, "blast", "B3")[1].split("Currently superseded")[1])
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
    """dte:B24, dte:B24"""

    def test_supersede_rewrites_and_deletes(self):
        write_node(self.root, id="B3", parents="A1", made_by="ai")
        self._init_repo()
        code, out = run(self.root, "retire", "B1", "--by", "agent", "--superseded-by", "B3")
        self.assertEqual(code, 0, out)
        self.assertIn("REVIEW", out)
        self.assertIn("C1 C1 title", out)
        self.assertFalse(os.path.exists(os.path.join(self.root, "decisions", "B", "B1.md")))
        self.assertNotIn("supersedes: [B1]", self._read("decisions/B/B3.md"))
        self.assertIn("B1", run(self.root, "blast", "B3")[1].split("Currently superseded")[1])
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
        self.assertIn("B2: human-held leaf deleted without authorized_by in the ledger", out)

    def test_blast_lists_retired_predecessor(self):
        write_node(self.root, id="B3", parents="A1", made_by="ai")
        self._init_repo()
        run(self.root, "retire", "B1", "--by", "agent", "--superseded-by", "B3")
        code, out = run(self.root, "blast", "B3")
        self.assertIn("candidates to return", out)
        self.assertIn('B1 "B1 title"', out)
        self.assertIn("git log --all", out)


class TestAuthoring(Base):
    """dte:B29, dte:B29, dte:B29"""

    def test_new_writes_a_valid_node(self):
        code, out = run(self.root, "new", "C", "--name", "auto1", "--title", "A fresh rule", "--by", "agent",
                        "--parents", "B1", "--decision", "d", "--why", "w")
        self.assertEqual(code, 0, out)
        self.assertIn('created C2 "A fresh rule"', out)
        text = self._read("decisions/C/C2.md")
        self.assertIn("id: C2", text)
        self.assertIn("parents: [B1]", text)
        self.assertNotIn("made_by", text)    # ai is the default; written only when it is not (B43)
        self.assertIn("uuid: ", text)
        self.assertNotIn("supersedes", text)  # the ledger records succession (B43)
        code, out = run(self.root, "validate")
        self.assertEqual(code, 0, out)
        self.assertNotIn("TODO", out)

    def test_new_without_text_warns_todo(self):
        run(self.root, "new", "C", "--name", "auto2", "--title", "Half done", "--by", "agent", "--parents", "B1")
        code, out = run(self.root, "validate")
        self.assertEqual(code, 0, out)
        self.assertIn("C2: body still has a TODO placeholder", out)

    def test_new_refuses_bad_parent(self):
        code, out = run(self.root, "new", "B", "--name", "auto3", "--title", "x", "--by", "agent", "--parents", "B1")
        self.assertEqual(code, 2)
        self.assertIn("not shallower", out)
        code, out = run(self.root, "new", "A", "--name", "auto4", "--title", "x", "--by", "owner", "--made-by", "human")
        self.assertEqual(code, 0, out)
        self.assertIn("created A2", out)

    def test_show(self):
        code, out = run(self.root, "show", "C1")
        self.assertEqual(code, 0, out)
        self.assertIn("C1  <-  B1  <-  A1", out)
        self.assertIn("src/a.py  lines 1", out)
        code, out = run(self.root, "show", "B1")
        self.assertIn("children (1):", out)
        self.assertIn("C1 C1 title", out)

    def test_show_retired(self):
        self._init_repo()
        run(self.root, "retire", "C1", "--by", "agent", "--authorized-by", "owner")
        code, out = run(self.root, "show", "C1")
        self.assertEqual(code, 0, out)
        self.assertIn("RETIRED", out)
        self.assertIn("authorized by owner", out)

    def test_find(self):
        code, out = run(self.root, "find", "b1 title")
        self.assertIn("B1 B1 title", out)
        code, out = run(self.root, "find", "nothing-like-this")
        self.assertIn("no matches", out)

    def test_ratify_flips_proposed_and_holds(self):
        write_node(self.root, id="B1", parents="A1", made_by="ai", status="proposed")
        code, out = run(self.root, "ratify", "B1", "--by", "owner")
        self.assertEqual(code, 0, out)
        self.assertIn("proposed -> active", out)
        text = self._read("decisions/B/B1.md")
        self.assertIn("ratified_by: owner", text)
        self.assertNotIn("status:", text)   # active is the default (B43)
        code, out = run(self.root, "ratify", "B2", "--by", "owner")
        self.assertEqual(code, 2)   # human-made

    def test_conflict_declares_both_sides(self):
        code, out = run(self.root, "conflict", "C1", "B2")
        self.assertEqual(code, 0, out)
        self.assertIn("B2 wins", out)
        self.assertIn("conflicts_with: [B2]", self._read("decisions/C/C1.md"))
        self.assertIn("conflicts_with: [C1]", self._read("decisions/B/B2.md"))
        code, out = run(self.root, "conflicts")
        self.assertIn("B2 wins (ring B over C)", out)

    def test_retired_lists_ledger(self):
        code, out = run(self.root, "retired")
        self.assertIn("Ledger empty", out)
        self._init_repo()
        run(self.root, "retire", "C1", "--by", "agent", "--authorized-by", "owner")
        code, out = run(self.root, "retired")
        self.assertIn("C1", out)
        self.assertIn("reverted", out)
        self.assertIn("authorized by owner", out)

    def test_export_is_json_with_join_keys(self):
        code, out = run(self.root, "export")
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual({n["id"] for n in data["leaves"]}, {"A1", "B1", "B2", "C1"})
        self.assertIn({"file": "src/a.py", "line": 1, "id": "C1"}, data["citations"])
        self.assertEqual(data["errors"], [])
        out_path = os.path.join(self.root, "tree.json")
        code, out = run(self.root, "export", "--out", out_path)
        self.assertTrue(os.path.exists(out_path))

    def test_init_scaffolds_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as empty:
            code, out = run(empty, "init")
            self.assertEqual(code, 0, out)
            self.assertTrue(os.path.exists(os.path.join(empty, "dte.cfg")))
            self.assertTrue(os.path.exists(os.path.join(empty, ".dteignore")))
            self.assertTrue(os.path.isdir(os.path.join(empty, "decisions", "inbox")))
            with open(os.path.join(empty, "dte.cfg"), "w") as fh:
                fh.write("summaries = off\n")
            code, out = run(empty, "init")
            self.assertIn("left alone", out)
            with open(os.path.join(empty, "dte.cfg")) as fh:
                self.assertEqual(fh.read(), "summaries = off\n")

    def test_dte_ring_env_is_default_for_as(self):
        self._init_repo()
        write_node(self.root, id="B3", parents="A1", made_by="ai")
        old = os.environ.get("DTE_RING")
        os.environ["DTE_RING"] = "C"
        try:
            code, out = run(self.root, "validate")
        finally:
            if old is None:
                del os.environ["DTE_RING"]
            else:
                os.environ["DTE_RING"] = old
        self.assertEqual(code, 1)
        self.assertIn("B3: changed by an agent at ring C", out)


class TestCiteBriefHook(Base):
    """dte:B29, dte:B27"""

    def test_cite_python_and_markdown(self):
        write_file(self.root, "src/new.py", "#!/usr/bin/env python\nprint(1)\n")
        code, out = run(self.root, "cite", os.path.join(self.root, "src", "new.py"), "B1,C1")
        self.assertEqual(code, 0, out)
        self.assertEqual(self._read("src/new.py").splitlines()[1], "# dte:B1,C1")
        write_file(self.root, "notes.md", "---\ntitle: x\n---\n# Notes\n")
        code, out = run(self.root, "cite", os.path.join(self.root, "notes.md"), "B2")
        self.assertEqual(code, 0, out)
        self.assertEqual(self._read("notes.md").splitlines()[3], "<!-- %s -->" % ("dte" + ":B2"))
        code, out = run(self.root, "validate")
        self.assertEqual(code, 0, out)

    def test_cite_appends_to_existing_and_refuses_bad(self):
        code, out = run(self.root, "cite", os.path.join(self.root, "src", "a.py"), "B1")
        self.assertEqual(code, 0, out)
        self.assertIn("added B1", out)
        self.assertEqual(self._read("src/a.py").splitlines()[0], "# dte:C1,B1")
        code, out = run(self.root, "cite", os.path.join(self.root, "src", "a.py"), "C1")
        self.assertIn("already cites", out)
        code, out = run(self.root, "cite", os.path.join(self.root, "src", "a.py"), "Z9")
        self.assertEqual(code, 2)
        write_file(self.root, "data.json", "{}\n")
        code, out = run(self.root, "cite", os.path.join(self.root, "data.json"), "B1")
        self.assertEqual(code, 2)
        self.assertIn("no comments", out)

    def test_brief(self):
        write_file(self.root, "dte.cfg", "authority = A:human, B:orchestrator, C+:subagent\n")
        code, out = run(self.root, "brief", "C")
        self.assertEqual(code, 0, out)
        self.assertIn("you operate at ring C", out)
        self.assertIn("ask orchestrator", out)
        self.assertIn("DTE_RING=C", out)
        self.assertIn("A1 A1 title [human-held]", out)
        self.assertIn("B1 B1 title (ai, unratified)", out)
        self.assertNotIn("C1 C1 title", out)

    def test_brief_under_restricts(self):
        write_node(self.root, id="B3", parents="A1", made_by="ai")
        code, out = run(self.root, "brief", "C", "--under", "B1")
        self.assertIn("B1 B1 title", out)
        self.assertNotIn("B3", out)
        self.assertIn("tree --under B1", out)

    def test_hook(self):
        self._init_repo()
        code, out = run(self.root, "hook")
        self.assertEqual(code, 0, out)
        hook = os.path.join(self.root, ".git", "hooks", "pre-commit")
        self.assertTrue(os.path.exists(hook))
        with open(hook) as fh:
            self.assertIn("validate", fh.read())
        code, out = run(self.root, "hook")
        self.assertIn("already runs dte", out)

    def test_set_writes_whitelisted_fields_and_guards_human_held(self):
        # dte:B29, dte:B29
        code, out = run(self.root, "set", "B1", "title", "A  new   title", "--by", "agent")
        self.assertEqual(code, 0, out)
        text = self._read("decisions/B/B1.md")
        self.assertIn('title: "A new title"', text)   # titles are quoted YAML (dte:C1)
        self.assertIn("title changed from", text)
        code, out = run(self.root, "set", "B1", "confidence", "low", "--by", "agent")
        self.assertEqual(code, 2)   # 0.2 dropped the field (B43)
        self.assertIn("Why", out)
        code, out = run(self.root, "set", "B1", "status", "reverted", "--by", "agent")
        self.assertEqual(code, 2)   # invariant-bearing field: redirected to its command
        self.assertIn("retire", out)
        code, out = run(self.root, "set", "B1", "by", "someone else", "--by", "agent")
        self.assertEqual(code, 2)   # provenance is fixed (A3)
        code, out = run(self.root, "set", "B2", "title", "Reworded", "--by", "agent")
        self.assertEqual(code, 2)   # B2 is human-made: needs --authorized-by (B11)
        self.assertIn("authorized-by", out)
        code, out = run(self.root, "set", "B2", "title", "Reworded", "--by", "agent",
                        "--authorized-by", "owner")
        self.assertEqual(code, 0, out)
        text = self._read("decisions/B/B2.md")
        self.assertIn('title: "Reworded"', text)
        self.assertIn("authorized_by: owner", text)
        code, out = run(self.root, "set", "B9", "title", "x", "--by", "agent")
        self.assertEqual(code, 2)

    def test_contest_runs_once_and_records_the_verdict(self):
        # dte:B60, dte:B60
        code, out = run(self.root, "contest", "B1")
        self.assertEqual(code, 0, out)
        self.assertIn("CONTEST B1", out)
        self.assertIn("Rubric", out)
        self.assertIn("A1", out)
        for slot in ("keep", "opposite", "deletion", "variant"):
            self.assertIn(slot, out)
        code, out = run(self.root, "contest", "B2")
        self.assertEqual(code, 2)   # human-made: settled, never contested
        code, out = run(self.root, "contest", "B1", "--record", "--chosen", "keep", "--by", "agent")
        self.assertEqual(code, 2)   # no note
        code, out = run(self.root, "contest", "B1", "--record", "--chosen", "keep", "--by", "agent",
                        "--note", "opposite: 3 files, fails A1. deletion: A1 alone cannot explain C1.")
        self.assertEqual(code, 0, out)
        text = self._read("decisions/B/B1.md")
        self.assertIn("contested_by: agent", text)
        self.assertIn("## Contest", text)
        self.assertIn("keep wins", text)
        self.assertIn("contested by agent; keep won", text)
        code, out = run(self.root, "contest", "B1")
        self.assertEqual(code, 2)
        self.assertIn("already contested", out)
        code, out = run(self.root, "contest", "B1", "--again")
        self.assertEqual(code, 0, out)
        code, out = run(self.root, "tree")
        self.assertIn("(ai, unratified, contested)", out)
        code, out = run(self.root, "validate")
        self.assertIn("1 contested", out)
        code, out = run(self.root, "ratify", "B1", "--by", "owner")
        self.assertEqual(code, 0, out)
        code, out = run(self.root, "contest", "B1", "--again")
        self.assertEqual(code, 2)   # ratified: settled

    def test_reparent_fixes_an_orphan(self):
        self._init_repo()
        run(self.root, "retire", "B1", "--by", "agent")          # C1 is now an orphan
        code, out = run(self.root, "validate")
        self.assertEqual(code, 1)
        self.assertIn("C1: ORPHAN", out)
        code, out = run(self.root, "reparent", "C1", "--parents", "B2", "--by", "agent")
        self.assertEqual(code, 2, out)   # C1 is human-made: a re-parent needs a human's name (B11)
        code, out = run(self.root, "reparent", "C1", "--parents", "B2", "--by", "agent", "--authorized-by", "owner")
        self.assertEqual(code, 0, out)
        self.assertIn("parents: [B2]", self._read("decisions/C/C1.md"))
        code, out = run(self.root, "validate")
        self.assertEqual(code, 0, out)
        code, out = run(self.root, "reparent", "C1", "--parents", "C1", "--by", "agent")
        self.assertEqual(code, 2)

    def test_next_reserves_ids_on_other_branches(self):
        # dte:C15
        self._init_repo()
        self._git("checkout", "-q", "-b", "feature")
        write_node(self.root, id="B3", parents="A1", made_by="ai")
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "B3 on feature")
        self._git("checkout", "-q", "-")
        self.assertFalse(os.path.exists(os.path.join(self.root, "decisions", "B", "B3.md")))
        self.assertEqual(run(self.root, "next", "B")[1].strip(), "B4")

    def test_ratify_many_and_tree_under(self):
        write_node(self.root, id="B3", parents="A1", made_by="ai", status="proposed")
        code, out = run(self.root, "ratify", "B1", "B3", "--by", "owner")
        self.assertEqual(code, 0, out)
        self.assertEqual(out.count("ratified "), 2)
        code, out = run(self.root, "tree", "--under", "B1")
        self.assertIn("B1 B1 title", out)
        self.assertIn("  C1 C1 title", out)
        self.assertNotIn("A1", out)


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


class TestVault(Base):
    # dte:B30, dte:B31, dte:B30

    def test_wikilink_parents_and_quoted_title_are_read(self):
        write_node(self.root, id="C2", parents='"[[B1]]"', title='"colon: inside"', made_by="ai")
        write_file(self.root, "src/w.py", "# [[C2]] and [[%s|text]]" % "B2" + chr(10))  # split: not a citation here
        write_file(self.root, "decisions/.obsidian/app.json", "{}")
        code, out = run(self.root, "validate", "--full")
        self.assertEqual(code, 0, out)
        self.assertIn("C2 colon: inside", out)
        tree = dte.Tree(self.root, os.path.join(self.root, "decisions"))
        self.assertEqual(tree.leaves["C2"].parents, ["B1"])
        code, out = run(self.root, "blast", "C2")
        self.assertIn("src/w.py", out)

    def test_links_wikilink_writes_that_form(self):
        write_file(self.root, "dte.cfg", "links = wikilink\n")
        code, out = run(self.root, "new", "C", "--name", "auto5", "--title", "t: u", "--by", "agent", "--parents", "B1")
        self.assertEqual(code, 0, out)
        text = self._read("decisions/C/C2.md")
        self.assertIn('parents: ["[[B1]]"]', text)
        self.assertIn('title: "t: u"', text)
        code, out = run(self.root, "cite", os.path.join(self.root, "src", "none.py"), "C2")
        self.assertEqual(code, 0, out)
        self.assertIn("[[C2]]", self._read("src/none.py"))

    def test_null_reads_as_empty_and_aliases_still_rejected(self):
        p = self._read("decisions/B/B1.md")
        write_file(self.root, "decisions/B/B1.md", p.replace("ratified_by: ", "ratified_by: null"))
        code, out = run(self.root, "validate")
        self.assertEqual(code, 0, out)
        write_file(self.root, "decisions/B/B1.md", p.replace("made_by:", "aliases: [x, y]\nmade_by:"))
        code, out = run(self.root, "validate")
        self.assertEqual(code, 1)

    def test_outbox_lists_notes_and_tags_and_done_clears(self):
        write_file(self.root, "decisions/outbox/idea.md", "# Split B2\n\nplease\n")
        p = self._read("decisions/B/B1.md")
        write_file(self.root, "decisions/B/B1.md", p.replace("made_by:", "tags: [ratify]\nmade_by:"))
        code, out = run(self.root, "outbox")
        self.assertEqual(code, 0)
        self.assertIn("Split B2", out)
        self.assertIn("#ratify", out)
        code, out = run(self.root, "validate")
        self.assertIn("OUTBOX (2)", out)
        run(self.root, "outbox", "--done", "idea")
        run(self.root, "outbox", "--done", "B1")
        code, out = run(self.root, "outbox")
        self.assertIn("Outbox empty", out)
        self.assertNotIn("tags:", self._read("decisions/B/B1.md"))

    def test_name_is_a_unique_camelcase_handle(self):
        # dte:B32, dte:B16
        code, out = run(self.root, "new", "C", "--name", "shareImpl", "--title", "t", "--by", "agent", "--parents", "B1")
        self.assertEqual(code, 0, out)
        text = self._read("decisions/C/C2.md")
        self.assertNotIn("name: shareImpl", text)   # the first alias is the name (B32)
        self.assertIn("aliases: [shareImpl]", text)
        code, out = run(self.root, "tree")
        self.assertIn("C2 shareImpl: t", out)
        code, out = run(self.root, "set", "B1", "name", "shareImpl", "--by", "agent")
        self.assertEqual(code, 2)
        code, out = run(self.root, "set", "B1", "name", "Not-Camel", "--by", "agent")
        self.assertEqual(code, 2)
        code, out = run(self.root, "set", "B1", "name", "oneFile", "--by", "agent")
        self.assertEqual(code, 0, out)
        code, out = run(self.root, "find", "oneFile")
        self.assertIn("B1", out)


class TestFeedbackRound(Base):
    # dte:B33, dte:B61, dte:B37, dte:B33, dte:C21, dte:B60, dte:C23, dte:B37

    def test_validate_is_a_summary_and_unratified_lists(self):
        code, out = run(self.root, "validate")
        self.assertIn("Unratified AI/joint decisions: 1", out)
        self.assertNotIn("[ai: tester]", out)
        code, out = run(self.root, "unratified")
        self.assertIn("B1", out)
        self.assertNotIn("no children and no citing artifacts", out)

    def test_zz_is_a_placeholder_not_a_citation(self):
        write_file(self.root, "docs/how.md", "cite it as `dte:ZZ1` or `[[ZZ1]]`\n")
        code, out = run(self.root, "validate")
        self.assertEqual(code, 0, out)

    def test_cite_does_not_merge_into_a_line_level_citation(self):
        write_file(self.root, "src/h.py", "x = 1\n# headless (dte:C1, enforced by the rete test)\n")
        code, out = run(self.root, "cite", os.path.join(self.root, "src", "h.py"), "B2")
        self.assertEqual(code, 0, out)
        text = self._read("src/h.py")
        self.assertIn("# " + "dte" + ":B2\n", text)
        self.assertIn("(dte:C1, enforced", text)

    def test_body_file_and_import(self):
        write_file(self.root, "body.md", "## Decision\n\nD `x: y`\n\n## Why\n\nW\n")
        code, out = run(self.root, "new", "C", "--name", "auto6", "--title", "t", "--by", "a", "--parents", "B1", "--body-file", os.path.join(self.root, "body.md"))
        self.assertEqual(code, 0, out)
        self.assertIn("D `x: y`", self._read("decisions/C/C2.md"))
        write_file(self.root, "old/one.md", "---\nring: B\nname: oneRule\ntitle: rule one\nparents: [A1]\nratified_by: owner\n---\n## Decision\n\nd1\n\n## Why\n\nw1\n")
        write_file(self.root, "old/two.md", "---\nring: C\ntitle: rule two\nparents: [oneRule, B2]\n---\n## Decision\n\nd2\n\n## Why\n\nw2\n")
        write_file(self.root, "old/three.md", "---\nring: D\ntitle: rule three\nparents: [two]\n---\n## Decision\n\nd3\n\n## Why\n\nw3\n")
        code, out = run(self.root, "import", os.path.join(self.root, "old"), "--by", "agent")
        self.assertEqual(code, 0, out)
        self.assertIn("imported 3 leaves", out)
        self.assertIn("aliases: [oneRule]", self._read("decisions/B/B3.md"))
        b3 = self._read("decisions/B/B3.md")
        self.assertIn("ratified_by: owner", b3)
        self.assertIn("imported from", b3)
        c3 = self._read("decisions/C/C3.md")
        self.assertIn("parents: [B3, B2]", c3)
        self.assertIn("parents: [C3]", self._read("decisions/D/D1.md"))
        code, out = run(self.root, "validate")
        self.assertEqual(code, 0, out)
        self.assertIn("2 imported", out)
        self.assertNotIn("OUTBOX", out)   # a carried ratified_by is not a vault edit
        write_file(self.root, "old/bad.md", "---\nring: C\ntitle: bad\nparents: [nobody]\nenforced_by: x\n---\n## Decision\n\n## Why\n")
        code, out = run(self.root, "import", os.path.join(self.root, "old"), "--by", "agent")
        self.assertEqual(code, 2)
        self.assertIn("unknown property", out)

    def test_authorize_records_a_go_ahead(self):
        code, out = run(self.root, "authorize", "A1", "--by", "owner", "--note", "go all out")
        self.assertEqual(code, 0, out)
        text = self._read("decisions/A/A1.md")
        self.assertIn("authorized_by: owner", text)
        self.assertIn("authorized by owner: go all out", text)

    def test_retire_carries_contested_by_and_contest_can_write_winner(self):
        self._init_repo()
        code, out = run(self.root, "contest", "B1", "--record", "--chosen", "variant", "--by", "agent",
                        "--note", "variant costs less", "--title", "the variant", "--name", "theVariant",
                        "--decision", "v", "--why", "w")
        self.assertEqual(code, 0, out)
        self.assertIn("created B3", out)
        self.assertIn("retired B1", out)
        b3 = self._read("decisions/B/B3.md")
        self.assertIn("contested_by: agent", b3)
        self.assertIn("won the contest of B1", b3)
        self.assertIn("Carried from B1", b3)
        self.assertIn("parents: [A1]", b3)
        code, out = run(self.root, "validate")
        self.assertEqual(code, 0, out)
        self.assertIn("1 contested", out)

    def test_body_change_without_history_warns(self):
        self._init_repo()
        p = self._read("decisions/B/B1.md")
        write_file(self.root, "decisions/B/B1.md", p.replace("## Decision\nx", "## Decision\nchanged"))
        code, out = run(self.root, "validate")
        self.assertIn("body changed in this working tree with no new History line", out)
        self.assertIn("[body changed, no History line]", out)
        write_file(self.root, "decisions/B/B1.md", self._read("decisions/B/B1.md") + "\n## History\n\n- 2026-09-18 reworded by agent.\n")
        code, out = run(self.root, "validate")
        self.assertNotIn("no new History line", out)
        self.assertIn("[body changed]", out)

    def test_layers_are_derived_from_globs(self):
        write_file(self.root, "dte.cfg", "tests = tests/*\nspecs = specs/*\nagents = CLAUDE.md\ndocs = *.md\n")
        write_file(self.root, "tests/test_a.py", "# dte:C1\n")
        write_file(self.root, "specs/a.md", "<!-- dte:B1 -->\n")
        write_file(self.root, "CLAUDE.md", "dte" + ":B2\n")
        code, out = run(self.root, "show", "C1")
        self.assertIn("enforced by:", out)
        self.assertIn("implemented by:", out)
        code, out = run(self.root, "show", "B1")
        self.assertIn("specified by:", out)
        code, out = run(self.root, "coverage")
        self.assertIn("specs         1/1", out)   # specs/a.md cites B1 (B45)
        self.assertIn("MUSTs         0/0", out)
        code, out = run(self.root, "scope")
        self.assertNotIn("B2", out)   # instructed by CLAUDE.md counts as reach (K9)

    def test_scope_comments_lists_migration_candidates(self):
        write_file(self.root, "src/heavy.py", "".join("# because reasons %d\n" % i for i in range(6)) + "x = 1\n")
        write_file(self.root, "src/cited.py", "# " + "dte" + ":C1\n" + "".join("# note %d\n" % i for i in range(6)))
        write_file(self.root, "src/light.py", "# one\nx = 1\n")
        code, out = run(self.root, "scope", "--comments")
        self.assertEqual(code, 0, out)
        self.assertIn("MIGRATION CANDIDATES (1)", out)
        self.assertIn("src/heavy.py", out)
        self.assertNotIn("cited.py", out)
        self.assertNotIn("light.py", out)

    def test_vendor_copies_rules_renders_decisions_and_ignores_them(self):
        code, out = run(self.root, "vendor", "--from", os.path.join(HERE, ".."))
        self.assertEqual(code, 0, out)
        for f in ("PROTOCOL.md", "SPEC.md", "ADOPTING.md", "README.md", "WALKTHROUGH.md", "DECISIONS.md"):
            text = self._read("vendor/dte/" + f)
            self.assertTrue(text.startswith("<!-- vendored from DTE "), f)
        dec = self._read("vendor/dte/DECISIONS.md")
        self.assertNotIn(os.path.abspath(os.path.join(HERE, "..")), dec)   # no local path in what ships
        # feedback items 2, 3: the stamp is the copy's own refresh command, --dir included
        self.assertIn("refresh with: python tools/dte.py vendor --from <a DTE checkout> --dir vendor/dte -->", dec)
        self.assertTrue(os.path.isfile(os.path.join(self.root, "tools", "dte.py")))
        self.assertIn("## Ring A", dec)
        self.assertIn("B39 vendoredRules", dec)
        self.assertIn("**Decision.**", dec)
        self.assertIn("vendor/dte/", self._read(".dteignore"))
        write_file(self.root, ".dteignore", self._read(".dteignore") + "tools/dte.py\n")
        code, out = run(self.root, "validate")
        self.assertEqual(code, 0, out)   # DTE's own citations do not leak into this tree (I1)
        code, out = run(self.root, "vendor", "--from", os.path.join(HERE, ".."))
        self.assertEqual(self._read(".dteignore").count("vendor/dte"), 1)   # feedback item 15: no duplicate entry
        self.assertIn("No A or B leaf of DTE changed", out)
        # a stale render missing a B leaf: the next vendor names it as new (feedback item 10)
        write_file(self.root, "vendor/dte/DECISIONS.md", dec.replace("### B39 ", "### X39 "))
        code, out = run(self.root, "vendor", "--from", os.path.join(HERE, ".."))
        self.assertIn("new      B39 vendoredRules", out)
        code, out = run(self.root, "vendor", "--from", self.root)
        self.assertEqual(code, 2)
        self.assertIn("not a DTE 0.2 checkout", out)

    def test_contest_prompt_weighs_an_incident_free_why(self):
        code, out = run(self.root, "contest", "B1")
        self.assertEqual(code, 0, out)
        self.assertIn("names none is", out)

    def test_show_survives_a_non_cp1252_character_on_a_narrow_console(self):
        write_node(self.root, id="C2", parents="B1", title="arrows")
        write_file(self.root, "decisions/C/C2.md", self._read("decisions/C/C2.md").replace("## Decision\nx", "## Decision\na \u2192 b"))
        env = dict(os.environ, PYTHONIOENCODING="cp1252")
        r = subprocess.run([sys.executable, os.path.join(HERE, "..", "tools", "dte.py"), "--root", self.root, "show", "C2"],
                           capture_output=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace"))
        self.assertIn(b"arrows", r.stdout)

    def test_ratify_drops_contest_keeps_alternatives_and_validate_warns_if_kept(self):
        p = "decisions/B/B1.md"
        write_file(self.root, p, self._read(p) + "\n## Alternatives considered\n\n- a flag instead\n\n## Contest\n\n### Contest 2026-09-02 by agent: keep wins\n\nRubric: A1.\n- opposite: lost\nVerdict: keep.\n\n## History\n\n- 2026-09-02 created.\n")
        code, out = run(self.root, "ratify", "B1", "--by", "owner")
        self.assertEqual(code, 0, out)
        text = self._read(p)
        self.assertNotIn("## Contest", text)
        self.assertNotIn("opposite: lost", text)
        self.assertIn("## Alternatives considered\n\n- a flag instead\n", text)
        self.assertIn("ratified by owner; earlier contest and history in git", text)
        self.assertNotIn("- 2026-09-02 created.", text)   # a ratified leaf is present governance (B41)
        write_file(self.root, p, text + "\n## Contest\n\n- back again\n")
        code, out = run(self.root, "validate")
        self.assertIn("ratified but still carries", out)

    def test_append_history_ignores_the_heading_named_in_prose(self):
        text = "## Decision\n\nsee `## History`\n\n## Why\n\nw\n"
        out = dte.append_history(text, "- 2026-09-18 x.")
        self.assertIn("\n## History\n\n- 2026-09-18 x.\n", out)

    def test_reflowed_body_is_not_a_body_change(self):
        self._init_repo()
        p = "decisions/B/B1.md"
        write_file(self.root, p, self._read(p).replace("## Decision\nx", "## Decision\n\nx"))
        code, out = run(self.root, "validate")
        self.assertNotIn("[body changed", out)

    def test_spec_skeleton_cites_node_and_lists_subtree(self):
        write_file(self.root, "dte.cfg", "specs = specs/*\n")
        code, out = run(self.root, "spec", "B1", "--out", os.path.join(self.root, "specs", "b1.md"))
        self.assertEqual(code, 0, out)
        text = self._read("specs/b1.md")
        self.assertTrue(text.startswith("<!-- " + "dte" + ":B1 -->"), text[:40])
        self.assertIn("## Purpose", text)
        self.assertIn("- A1", text)          # parent as constraint
        self.assertIn("- C1", text)          # descendant as covered decision
        self.assertIn("## Requirements", text)
        code, out = run(self.root, "show", "B1")
        self.assertIn("specified by:", out)
        code, out = run(self.root, "spec", "B1", "--out", os.path.join(self.root, "specs", "b1.md"))
        self.assertEqual(code, 2)            # never overwrites

    def test_gap_is_an_inbox_item_that_place_refuses(self):
        write_file(self.root, "specs/b1.md", "<!-- " + "dte" + ":B1 -->\n# Spec\n")
        code, out = run(self.root, "gap", os.path.join(self.root, "specs", "b1.md"), "--title", "Retry policy", "--by", "builder", "--note", "spec says nothing about retries")
        self.assertEqual(code, 0, out)
        self.assertIn("kind: gap", self._read("decisions/inbox/gap-retry-policy.md"))
        code, out = run(self.root, "inbox")
        self.assertIn("SPEC GAPS (1)", out)
        self.assertNotIn("PENDING PLACEMENT", out)
        code, out = run(self.root, "place", "gap-retry-policy", "C", "--by", "owner")
        self.assertEqual(code, 2)
        self.assertIn("spec gap, not a decision", out)
        code, out = run(self.root, "validate")
        self.assertEqual(code, 0, out)
        os.remove(os.path.join(self.root, "specs", "b1.md"))
        code, out = run(self.root, "validate")
        self.assertIn("names a spec that does not exist", out)

    def test_builder_brief_prints_rules_and_spec_without_ring(self):
        write_file(self.root, "specs/b1.md", "<!-- " + "dte" + ":B1 -->\n# Spec\n\nbuild the thing\n")
        code, out = run(self.root, "brief", "--builder", os.path.join(self.root, "specs", "b1.md"))
        self.assertEqual(code, 0, out)
        self.assertIn("BUILDER BRIEF", out)
        self.assertIn("cite <file> B1", out)
        self.assertIn("build the thing", out)
        self.assertNotIn("Decisions above your ring", out)
        self.assertNotIn("DTE_RING=", out)
        code, out = run(self.root, "brief")
        self.assertEqual(code, 2)

    def test_init_ignores_the_tool(self):
        code, out = run(self.root, "init")
        self.assertEqual(code, 0, out)
        self.assertIn("dte.py", self._read(".dteignore"))


class TestZeroTwo(Base):
    """DTE 0.2: what Solenoid's copy proved, and the open items of its feedback, by item number."""

    def setUp(self):
        super().setUp()
        os.environ["DTE_NO_REMOTE"] = "1"

    def _validate(self, *extra):
        return run(self.root, "validate", *extra)

    # lean frontmatter, items 24, 25, 41, 46
    def test_new_writes_lean_frontmatter_and_reads_joint_back(self):
        code, out = run(self.root, "new", "C", "--name", "jointCall", "--title", "t", "--by", "owner and agent",
                        "--made-by", "joint", "--parents", "B1", "--decision", "d", "--why", "w")
        self.assertEqual(code, 0, out)
        text = self._read("decisions/C/C2.md")
        for gone in ("status:", "supersedes", "superseded_by", "confidence", "name:"):
            self.assertNotIn(gone, text)
        self.assertIn("made_by: joint", text)
        self.assertIn("(joint, unratified)", run(self.root, "show", "C2")[1])
        code, out = run(self.root, "new", "C", "--title", "t", "--by", "a", "--parents", "B1")
        self.assertEqual(code, 2)   # a leaf always has a name (A5)

    def test_upgrade_brings_a_01_tree_to_02_and_is_idempotent(self):
        write_file(self.root, "decisions/B/B3.md",
                   "---\nid: B3\ntitle: old\nstatus: active\nparents: [A1]\nsupersedes: []\nsuperseded_by:\n"
                   "conflicts_with: []\nmade_by: ai\nby: agent\ndate: 2026-09-02\nratified_by:\nconfidence: low\n"
                   "name: oldRule\naliases: [oldRule]\n---\n\n## Decision\n\nd\n\n## Why\n\nw\n")
        code, out = self._validate()
        self.assertIn("'confidence' is a 0.1 field", out)
        self.assertIn("dte upgrade", out)
        code, out = run(self.root, "upgrade")
        self.assertEqual(code, 0, out)
        text = self._read("decisions/B/B3.md")
        self.assertRegex(text, r"\nid: B3\nuuid: [0-9a-f-]{36}\n")
        for gone in ("status:", "supersedes", "confidence", "name:", "made_by"):
            self.assertNotIn(gone, text)
        self.assertIn("aliases: [oldRule]", text)
        self.assertIn("by: agent", text)
        self.assertEqual(self._validate()[0], 0)
        first = text
        run(self.root, "upgrade")
        self.assertEqual(self._read("decisions/B/B3.md"), first)   # stable uuid, nothing else to do

    # item 7
    def test_empty_section_warns(self):
        p = "decisions/B/B1.md"
        write_file(self.root, p, self._read(p) + "\n## Consequences\n\n## History\n\n- x\n")
        self.assertIn("B1: section '## Consequences' is empty", self._validate()[1])

    # item 27
    def test_a_must_is_tested_or_labeled(self):
        p = "decisions/B/B1.md"
        base = self._read(p).replace("\nx\n", "\nEvery card MUST show its unit.\n")
        write_file(self.root, p, base)
        self.assertIn("B1: states a MUST that no test cites", self._validate()[1])
        write_file(self.root, p, base + "\n## Consequences\n\n- *Unenforced:* a unit is visual; no test can see it.\n")
        self.assertNotIn("states a MUST", self._validate()[1])
        write_file(self.root, p, base)
        write_file(self.root, "tests/test_units.py", "# dte" ":B1\n")
        self.assertNotIn("states a MUST", self._validate()[1])
        write_file(self.root, p, self._read(p).replace("MUST show", "should show") + "\n## History\n\n- it MUST once\n")
        self.assertNotIn("states a MUST", self._validate()[1])   # History records other times

    # item 38
    def test_a_leaf_cites_only_up_its_lineage(self):
        p = "decisions/B/B1.md"
        write_file(self.root, p, self._read(p).replace("\nx\n", "\nx, refined by [[C1]].\n"))
        code, out = self._validate()
        self.assertEqual(code, 1)
        self.assertIn("B1: cites C1, a deeper ring", out)
        write_file(self.root, p, self._read(p).replace("x, refined by [[C1]].", "x") + "\n## History\n\n- split into [[C1]].\n")
        self.assertEqual(self._validate()[0], 0)   # History may name anything

    # item 40
    def test_clearing_history_is_not_an_unlogged_edit(self):
        p = "decisions/B/B1.md"
        write_file(self.root, p, self._read(p) + "\n## History\n\n- one\n- two\n- three\n")
        self._init_repo()
        write_file(self.root, p, self._read(p).replace("\nx\n", "\nx, sharper\n").replace("- one\n- two\n- three\n", "- reworded, history reset\n"))
        self.assertNotIn("no new History line", self._validate()[1])

    # item 21
    def test_editorial_log_covers_a_wording_sweep_once(self):
        self._init_repo()
        for p in ("decisions/B/B1.md", "decisions/C/C1.md"):
            write_file(self.root, p, self._read(p).replace("\ny\n", "\ny, in the new vocabulary\n"))
        out = self._validate()[1]
        self.assertIn("B1: body changed in this working tree with no new History line", out)
        code, out = run(self.root, "editorial", "--by", "agent", "--note", "node -> leaf")
        self.assertEqual(code, 0, out)
        self.assertIn("2 leaves", out)
        self.assertNotIn("no new History line", self._validate()[1])
        write_file(self.root, "decisions/B/B1.md", self._read("decisions/B/B1.md").replace("\nx\n", "\nx changed again\n"))
        self.assertIn("B1: body changed", self._validate()[1])   # the hash no longer matches

    # item 22
    def test_retire_carries_the_winners_name_and_collapses_repeats(self):
        write_node(self.root, id="B3", parents="A1", made_by="ai", name="winnerRule")
        write_node(self.root, id="B1", parents="A1", made_by="ai", name="loserRule")
        write_file(self.root, "docs/x.md", "Uses [[B1]] loserRule here.\nBoth ([[B3]] winnerRule) and ([[B1]] loserRule).\n")
        self._init_repo()
        code, out = run(self.root, "retire", "B1", "--by", "agent", "--superseded-by", "B3")
        self.assertEqual(code, 0, out)
        doc = self._read("docs/x.md")
        self.assertIn("Uses [[B3]] winnerRule here.", doc)
        self.assertIn("Both ([[B3]] winnerRule).", doc)
        self.assertNotIn("()", doc)

    # item 43
    def test_absorbing_successor_does_not_inherit_a_contest(self):
        write_node(self.root, id="B3", parents="A1", made_by="ai")
        self._init_repo()
        run(self.root, "contest", "B1", "--record", "--chosen", "keep", "--by", "agent", "--note", "kept")
        code, out = run(self.root, "retire", "B1", "--by", "agent", "--superseded-by", "B3")
        self.assertEqual(code, 0, out)
        b3 = self._read("decisions/B/B3.md")
        self.assertNotIn("## Contest", b3)
        self.assertNotIn("contested_by", b3)

    # item 33
    def test_cite_does_nothing_when_the_header_already_cites_by_name(self):
        write_file(self.root, "src/c.ts", "// [" "[B2]] leafTwo, [" "[C1]] some name\nexport {}\n")
        code, out = run(self.root, "cite", "src/c.ts", "C1")
        self.assertEqual(code, 0, out)
        self.assertIn("already cites", out)
        self.assertEqual(self._read("src/c.ts").count("C1"), 1)

    # item 35
    def test_unratified_sorts_by_ring_then_reach_and_validate_names_the_top(self):
        write_node(self.root, id="B3", parents="A1", made_by="ai")
        write_node(self.root, id="C2", parents="B3", made_by="ai")
        write_node(self.root, id="C3", parents="B3", made_by="ai")
        out = run(self.root, "unratified")[1]
        self.assertLess(out.index("B3 "), out.index("B1 "))   # B3 has two below, B1 one
        self.assertLess(out.index("B1 "), out.index("C1 ") if "C1 " in out else len(out))
        self.assertIn("in rings A and B (2)", self._validate()[1])

    # items 14, 16, 17, 18, 30
    def test_three_gauges_covers_and_the_exclusion_store(self):
        write_file(self.root, "dte.cfg", "specs = specs/*\ntests = tests/*\n")
        write_file(self.root, "specs/cards.md", "<!-- dte" ":B1 -->\n<!-- covers: src/cards/* -->\n# Cards\n")
        write_file(self.root, "specs/loose.md", "# nothing cited\n")
        write_file(self.root, "src/cards/one.ts", "".join("// why %d\n" % k for k in range(6)) + "x\n")
        write_file(self.root, ".dtecoverage", "why: fixtures need no decision\nsrc/none.py\nwhy: gone\nsrc/missing/*\n")
        code, out = run(self.root, "coverage", "--check")
        self.assertEqual(code, 1, out)
        self.assertIn("(1 through a spec's covers:)", out)
        self.assertIn("specs         1/2", out)
        self.assertIn("specs/loose.md", out)
        self.assertIn("src/missing/*", out)   # stale
        self.assertIn("src/cards/one.ts", out.split("Next worklist")[1])
        self.assertIn("via specs/cards.md", run(self.root, "show", "B1")[1])
        self.assertIn("Built to specs/cards.md", run(self.root, "blast", "B1")[1])
        write_file(self.root, "specs/loose.md", "<!-- dte" ":B2 -->\n")
        write_file(self.root, ".dtecoverage", "why: fixtures need no decision\nsrc/none.py\ndte.cfg\n")
        code, out = run(self.root, "coverage", "--check")
        self.assertEqual(code, 0, out)
        write_file(self.root, ".dtecoverage", "src/none.py\n")
        self.assertEqual(run(self.root, "coverage")[0], 2)   # a glob before any why: line

    # item 45
    def test_fold_puts_an_aspect_back_into_its_parent(self):
        write_node(self.root, id="D1", parents="C1", made_by="ai")
        write_node(self.root, id="C1", parents="B1", made_by="ai", name="aspectOf")
        self._init_repo()
        code, out = run(self.root, "fold", "C1", "--by", "agent")
        self.assertEqual(code, 0, out)
        b1 = self._read("decisions/B/B1.md")
        self.assertIn("## Consequences\n\n- x", b1)
        self.assertIn("C1 aspectOf folded in", b1)
        self.assertIn("dte" ":B1", self._read("src/a.py"))
        self.assertIn("parents: [B1]", self._read("decisions/D/D1.md"))
        self.assertIn("\tfolded\tB1\t", self._read("decisions/RETIRED"))
        self.assertEqual(self._validate()[0], 0)
        self.assertIn("folded into B1", run(self.root, "show", "C1")[1])

    def test_to_spec_turns_mechanics_into_spec_text(self):
        write_file(self.root, "dte.cfg", "specs = specs/*\n")
        write_node(self.root, id="D1", parents="C1", made_by="ai")
        write_node(self.root, id="C1", parents="B1", made_by="ai", name="loadOrder", title="Load the cache first")
        self._init_repo()
        code, out = run(self.root, "to-spec", "C1", "specs/loading.md", "--by", "agent")
        self.assertEqual(code, 0, out)
        spec = self._read("specs/loading.md")
        self.assertIn("dte" ":B1", spec.split("\n")[0])
        self.assertIn("## Load the cache first\n\nx", spec)
        self.assertIn("dte" ":B1", self._read("src/a.py"))
        self.assertIn("parents: [B1]", self._read("decisions/D/D1.md"))
        self.assertIn("\tto-spec\tspecs/loading.md\t", self._read("decisions/RETIRED"))
        self.assertEqual(self._validate()[0], 0)
        self.assertIn("now spec text in specs/loading.md", run(self.root, "show", "C1")[1])

    # items 32, 42
    def test_renumber_keeps_the_leaf_and_validate_knows_it_by_uuid(self):
        self._init_repo()
        uuid = re.search(r"uuid: (\S+)", self._read("decisions/C/C1.md")).group(1)
        code, out = run(self.root, "renumber", "C1", "--by", "agent")
        self.assertEqual(code, 0, out)
        self.assertIn("uuid: " + uuid, self._read("decisions/C/C2.md"))
        self.assertIn("dte" ":C2", self._read("src/a.py"))
        code, out = run(self.root, "validate", "--as", "C")
        self.assertNotIn("deleted with no ledger line", out)
        self.assertNotIn("renamed", out)
        self.assertNotIn("C1\t", self._read("decisions/RETIRED") if os.path.exists(os.path.join(self.root, "decisions/RETIRED")) else "")

    def test_merge_ids_renumbers_what_the_base_gave_another_leaf(self):
        self._init_repo()
        self._git("checkout", "-q", "-b", "feature")
        write_node(self.root, id="C2", parents="B1", made_by="ai", title="feature's C2", name="featureTwo",
                   uuid=dte.new_uuid(0, "feature"))
        write_file(self.root, "src/f.py", "# dte" ":C2\n")
        self._git("add", "-A"); self._git("commit", "-q", "-m", "feature")
        self._git("checkout", "-q", "master") if self._git("rev-parse", "--verify", "master").returncode == 0 else self._git("checkout", "-q", "main")
        write_node(self.root, id="C2", parents="B1", made_by="ai", title="base's C2", name="baseTwo")
        self._git("add", "-A"); self._git("commit", "-q", "-m", "base")
        base = self._git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        self._git("checkout", "-q", "feature")
        code, out = run(self.root, "merge-ids", base, "--by", "agent")
        self.assertEqual(code, 0, out)
        self.assertIn("renumbered C2 -> C3", out)
        self.assertIn("dte" ":C3", self._read("src/f.py"))
        self.assertIn("feature's C2", self._read("decisions/C/C3.md"))
        self.assertIn("no id collisions", run(self.root, "merge-ids", base, "--by", "agent")[1])

    # item 44
    def test_branch_local_subtree(self):
        write_node(self.root, id="A2", made_by="human")
        p = "decisions/A/A2.md"
        write_file(self.root, p, self._read(p).replace("parents: []", "parents: []\nbranch: bleeding"))
        write_node(self.root, id="B3", parents="A2", made_by="ai")
        self._init_repo()
        out = self._validate()[1]
        self.assertIn("A2: belongs to branch bleeding", out)
        self.assertIn("branch: bleeding", run(self.root, "show", "B3")[1])
        os.remove(os.path.join(self.root, p))
        os.remove(os.path.join(self.root, "decisions/B/B3.md"))
        out = self._validate()[1]
        self.assertNotIn("deleted with no ledger line", out)

    # item 31
    def test_tree_change_with_no_ring_declared_warns(self):
        self._init_repo()
        p = "decisions/C/C1.md"
        write_file(self.root, p, self._read(p) + "\n## History\n\n- touched\n")
        self.assertIn("no ring declared", self._validate()[1])
        self.assertNotIn("no ring declared", self._validate("--as", "B")[1])
        os.environ["DTE_OWNER"] = "1"
        try:
            self.assertNotIn("no ring declared", self._validate()[1])
        finally:
            del os.environ["DTE_OWNER"]

    def test_editorial_replace_sweeps_titles_and_bodies_but_not_history(self):
        p = "decisions/B/B1.md"
        write_file(self.root, p, self._read(p).replace("\nx\n", "\nEvery node counts. Nodes too.\n")
                   .replace("title: B1 title", 'title: "A node rule"') + "\n## History\n\n- made as a node\n")
        self._init_repo()
        code, out = run(self.root, "editorial", "--by", "agent", "--note", "node -> leaf",
                        "--replace", "nodes=leaves", "--replace", "node=leaf")
        self.assertEqual(code, 0, out)
        text = self._read(p)
        self.assertIn('title: "A leaf rule"', text)
        self.assertIn("Every leaf counts. Leaves too.", text)
        self.assertIn("- made as a node", text)
        self.assertNotIn("no new History line", self._validate()[1])
        self.assertIn("node -> leaf", self._read("decisions/EDITORIAL"))
