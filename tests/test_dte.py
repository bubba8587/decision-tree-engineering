"""Tests for tools/dte.py.  dte:B6,C2,B4,B5

Run: python -m unittest discover -s tests
"""
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import dte  # noqa: E402

NODE = """---
id: {id}
title: {id} title
status: {status}
parents: [{parents}]
supersedes: [{supersedes}]
superseded_by: {superseded_by}
conflicts_with: [{conflicts}]
aliases: [{aliases}]
made_by: {made_by}
by: tester
date: 2026-09-02
---

## Decision
x

## Why
y
"""


def write_node(root, **kw):
    kw.setdefault("status", "active")
    kw.setdefault("parents", "")
    kw.setdefault("supersedes", "")
    kw.setdefault("superseded_by", "")
    kw.setdefault("conflicts", "")
    kw.setdefault("aliases", "")
    kw.setdefault("made_by", "human")
    ring = kw["id"][0]
    d = os.path.join(root, "decisions", ring)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, kw["id"] + ".md"), "w", encoding="utf-8") as fh:
        fh.write(NODE.format(**kw))


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
        write_node(self.root, id="B1", parents="A1", status="reverted")
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
        # dte:B2  move B2 -> C2, keep alias
        os.remove(os.path.join(self.root, "decisions", "B", "B2.md"))
        write_node(self.root, id="C2", parents="A1", aliases="B2")
        code, out = run(self.root, "validate")
        self.assertEqual(code, 0, out)
        self.assertIn("B2 is an alias of C2", out)


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
        write_node(self.root, id="B2", parents="A1", status="superseded", superseded_by="B3")
        write_node(self.root, id="B3", parents="A1", supersedes="B2")
        code, out = run(self.root, "blast", "B3")
        self.assertIn("candidates to return", out)
        self.assertIn("B2", out)

    def test_conflict_resolved_by_ring(self):
        write_node(self.root, id="C1", parents="B1", conflicts="B2")
        code, out = run(self.root, "conflicts")
        self.assertIn("B2 wins", out)

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
        write_node(self.root, id="C2", parents="A1", aliases="B2")
        self.assertEqual(run(self.root, "next", "B")[1].strip(), "B3")
        self.assertEqual(run(self.root, "next", "D")[1].strip(), "D1")


if __name__ == "__main__":
    unittest.main()
