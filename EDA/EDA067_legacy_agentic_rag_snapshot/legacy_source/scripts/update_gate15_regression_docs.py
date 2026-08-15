"""Record the promoted Gate-15 regression contract in the design document."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "src/pipeline_design.md"
MARKER = "## Formal Regression Baseline: Gate 15"
BLOCK = """

## Formal Regression Baseline: Gate 15

The active formal regression baseline is the deterministic Gate-15 baseline.

- valid: 17 correct / 0 incorrect / 13 blank
- test: 100 complete / 0 errors
- Gate: 15 allowed / 85 suppressed
- allowed IDs: 2, 3, 4, 19, 39, 41, 43, 56, 63, 72, 81, 82, 83, 89, 92
- cumulative additions from the former Gate-10 baseline: 4, 39, 56, 63, 83
- test 10, test 0, and test 85 remain suppressed
- Unit: 125 tests or more must pass

The 15 answers must be regenerated from runtime routes and structured Evidence.
Human review records are evaluation metadata only and must not be used as runtime,
Verification, or Gate input. The authoritative artifact set is kept in
`data/output/confirmed_gate_baseline_and_next_capability_v1/analysis/`.
"""


def main() -> None:
    content = DESIGN.read_text(encoding="utf-8")
    if MARKER not in content:
        DESIGN.write_text(content.rstrip() + BLOCK + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
