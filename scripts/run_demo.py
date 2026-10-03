"""Run one simulation and print its metrics.

    python scripts/run_demo.py --scenario peak --controller fuzzy_opt --seed 100
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from traffic_signal.config import SCENARIOS, Config, NoiseParams  # noqa: E402
from traffic_signal.controllers import CONTROLLER_NAMES, build_controller  # noqa: E402
from traffic_signal.experiments import simulate  # noqa: E402
from traffic_signal.metrics import compute_metrics  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--scenario", choices=sorted(SCENARIOS), default="peak")
    ap.add_argument("--controller", choices=CONTROLLER_NAMES, default="fuzzy_opt")
    ap.add_argument("--seed", type=int, default=100)
    ap.add_argument("--queue-noise", type=float, default=0.0, help="queue sensor std-dev (veh)")
    ap.add_argument("--miss-rate", type=float, default=0.0, help="missed-detection probability")
    args = ap.parse_args()
    cfg = Config()
    sc = SCENARIOS[args.scenario]
    ctrl = build_controller(args.controller, cfg, sc)
    res = simulate(sc, ctrl, args.seed, cfg, NoiseParams(args.queue_noise, args.miss_rate))
    print(f"{args.controller} on '{args.scenario}' (seed {args.seed}):")
    for k, v in compute_metrics(res, cfg).items():
        print(f"  {k:22s} {v:10.2f}")


if __name__ == "__main__":
    main()
