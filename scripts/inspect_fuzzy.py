"""Print the fuzzy controller's configuration: membership functions, the full rule
table, and sample inferences across the input space.

    python scripts/inspect_fuzzy.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from traffic_signal.config import FuzzyParams  # noqa: E402
from traffic_signal.fuzzy import (  # noqa: E402
    GREEN_TERMS, INTENSITY_TERMS, QUEUE_TERMS, RULES, FuzzyGreenController,
)

SHORT_NAMES = {"VERY_SHORT": "VS", "SHORT": "S", "MEDIUM": "M", "LONG": "L", "VERY_LONG": "VL"}


def main() -> None:
    p = FuzzyParams()
    print("MEMBERSHIP FUNCTIONS  (trapezoid a, b, c, d; triangle when b == c)")
    for label, uni, terms in (("queue (veh)", p.queue_universe, p.queue_terms),
                              ("arrival intensity y (own and competing)", p.intensity_universe,
                               p.intensity_terms),
                              ("green time (s) [output]", p.green_universe, p.green_terms)):
        print(f"\n  {label}, universe {uni}")
        for name, abcd in terms.items():
            print(f"    {name:11s} {abcd}")

    print(f"\nRULE BASE  ({RULES.size} rules; AND = min, implication = min, aggregation = max, "
          "defuzzification = centroid)")
    for ci, cn in enumerate(INTENSITY_TERMS):
        print(f"\n  competing intensity = {cn}")
        print("    queue \\ own   " + "  ".join(f"{a:>6s}" for a in INTENSITY_TERMS))
        for qi, qn in enumerate(QUEUE_TERMS):
            row = "  ".join(f"{SHORT_NAMES[GREEN_TERMS[RULES[ci, qi, ai]]]:>6s}"
                            for ai in range(len(INTENSITY_TERMS)))
            print(f"    {qn:12s}  {row}")

    fis = FuzzyGreenController(p)
    print("\nSAMPLE INFERENCES  (green time in seconds)")
    print("    queue  own_y  competing_y  ->  green")
    for q, a, c in ((0, 0.05, 0.05), (4, 0.15, 0.15), (8, 0.25, 0.25), (12, 0.25, 0.10),
                    (12, 0.25, 0.45), (20, 0.40, 0.20), (30, 0.45, 0.05), (40, 1.0, 0.0)):
        print(f"    {q:5.0f}  {a:5.2f}  {c:11.2f}  ->  {fis.infer(q, a, c)[0]:5.1f}")
    print("\nStep-by-step trace of one input: "
          "python scripts/explain_decision.py --queue 14 --intensity 0.30 --competing 0.20")


if __name__ == "__main__":
    main()
