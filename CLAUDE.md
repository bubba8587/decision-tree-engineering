<!-- dte:B56,B52,B6,B62 -->
# Working in the DTE repository

This repository is DTE itself, kept as a DTE tree with its own tool (A9 treeStructure). Read and follow `PROTOCOL.md`: it is the protocol every DTE repo uses, and it holds everything below that is not specific to this repository.

## This repository's answers to the protocol

- **Your ring until the owner says:** B. The owner holds A; subagents get C or deeper.
- **Rings here:** `A` core goals, set by the owner (never add to it; inbox it and ask). `B` the format and rules of DTE. `C` the few calls about the reference tool a person could weigh. How the tool does things is spec: `specs/scanning.md`, `specs/retiring.md`, `specs/commands.md`.
- **The owner validates** with `DTE_OWNER=1` so the no-ring warning stays quiet.

## Conventions

- The tool is one file, Python 3.8+, standard library only (B6 singleScript). Tests: `python -m unittest discover -s tests`. A literal citation in a test fixture is written split (`"dte" ":B1"`), or the scanner counts it as DTE's own.
- Every change to DTE goes leaf first, then the tool and specs, then the docs.
- `WALKTHROUGH.md` is generated: `python tools/walkthrough.py` after any change to the tool's output.
- Keep prose short. The Why carries the reasoning and nothing else (B62 presentGovernance).
