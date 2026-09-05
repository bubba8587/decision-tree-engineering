"""Time every dte command on a synthetic tree of large-project size.  dte:B6,C8

Run: python tools/scale.py [nodes-per-ring-scale]
Builds a temporary git repo with rings A-D and thousands of citing files,
runs each command twice (cold, warm), prints seconds and output lines.
"""
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time

DTE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dte.py")
scale = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
N_A, N_B, N_C, N_D = 6, int(60 * scale), int(300 * scale), int(400 * scale)
N_FILES = int(3000 * scale)
root = tempfile.mkdtemp(prefix="dte-scale-")
random.seed(1)

NODE = ("---\nid: {id}\ntitle: {id} synthetic decision about {topic}\nstatus: active\n"
        "parents: [{parents}]\nsupersedes: []\nsuperseded_by:\nconflicts_with: []\n"
        "made_by: ai\nby: gen\ndate: 2026-09-02\nratified_by:\n---\n\n## Decision\n\n"
        "{id} decides {topic}.\n\n## Why\n\nBecause of its parents.\n")
ids = {"A": [], "B": [], "C": [], "D": []}
topics = ["caching", "auth", "routing", "storage", "logging", "billing", "search", "ui", "sync", "export"]


def mk(ring, n, parent_rings):
    d = os.path.join(root, "decisions", ring)
    os.makedirs(d, exist_ok=True)
    for k in range(1, n + 1):
        i = "%s%d" % (ring, k)
        parents = []
        for pr in parent_rings:
            parents += random.sample(ids[pr], min(len(ids[pr]), random.choice([1, 1, 2])))
        with open(os.path.join(d, i + ".md"), "w") as fh:
            fh.write(NODE.format(id=i, topic=random.choice(topics), parents=", ".join(parents)))
        ids[ring].append(i)


mk("A", N_A, [])
mk("B", N_B, ["A"])
mk("C", N_C, ["B"])
mk("D", N_D, ["C"])
allids = ids["B"] + ids["C"] + ids["D"]
for k in range(N_FILES):
    p = os.path.join(root, "src", "pkg%d" % (k % 40), "mod%d.py" % k)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    cites = random.sample(allids, random.choice([0, 1, 1, 2, 3]))
    with open(p, "w") as fh:
        if cites:
            fh.write("# dte:%s\n" % ",".join(cites))
        fh.write("def f():\n    return %d\n" % k * 20)
subprocess.run(["git", "-C", root, "init", "-q"], capture_output=True)
subprocess.run(["git", "-C", root, "add", "-A"], capture_output=True)
subprocess.run(["git", "-C", root, "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-q", "-m", "x"],
               capture_output=True)

print("nodes %d, files %d" % (N_A + N_B + N_C + N_D, N_FILES))
print("%-28s %8s %8s %8s" % ("command", "cold s", "warm s", "lines"))
for cmd in (["validate"], ["tree"], ["blast", "B1"], ["trace", os.path.join(root, "src", "pkg0", "mod0.py")],
            ["show", "D1"], ["scope"], ["coverage"], ["brief", "D", "--under", "C1"],
            ["export", "--out", os.path.join(root, "t.json")], ["validate", "--as", "D"], ["find", "caching"]):
    times = []
    for _ in range(2):
        t = time.time()
        r = subprocess.run([sys.executable, DTE, "--root", root] + cmd, capture_output=True, text=True)
        times.append(time.time() - t)
    print("%-28s %8.2f %8.2f %8d" % (" ".join(cmd[:2]), times[0], times[1], r.stdout.count("\n")))
shutil.rmtree(root, ignore_errors=True)
