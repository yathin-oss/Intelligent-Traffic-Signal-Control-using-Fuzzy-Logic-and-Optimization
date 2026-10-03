"""Generate every figure and the markdown results tables from results/*.csv.

    python scripts/make_plots.py [--results results]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from traffic_signal.plots import make_all  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", type=Path, default=Path("results"))
    args = ap.parse_args()
    if not (args.results / "summary.csv").exists():
        sys.exit(f"{args.results}/summary.csv not found - run scripts/run_experiments.py first")
    for p in make_all(args.results):
        print(p)


if __name__ == "__main__":
    main()
