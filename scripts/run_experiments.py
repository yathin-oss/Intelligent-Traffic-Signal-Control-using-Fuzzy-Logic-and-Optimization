"""Run every experiment and write CSVs to results/.

    python scripts/run_experiments.py            # full study (30 seeds)
    python scripts/run_experiments.py --quick    # 5 seeds, for a fast check
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd  # noqa: E402

from traffic_signal.config import EVAL_SEEDS, Config  # noqa: E402
from traffic_signal import experiments as ex  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="use 5 evaluation seeds")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--out", type=Path, default=Path("results"))
    ap.add_argument("--skip-noise", action="store_true")
    ap.add_argument("--skip-sweep", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log = logging.getLogger("run_experiments")
    args.out.mkdir(parents=True, exist_ok=True)
    cfg = Config()
    seeds = EVAL_SEEDS[:5] if args.quick else EVAL_SEEDS
    t0 = time.time()

    log.info("1/5 tuning on the tuning scenario (never on evaluation data)")
    tuned, tuning = ex.tune(cfg, args.workers)
    tuning.to_csv(args.out / "tuning.csv", index=False)

    log.info("2/5 main experiment: 5 scenarios x 6 controllers x %d seeds", len(seeds))
    main_df = ex.run_main(cfg, tuned, seeds, args.workers)
    main_df.to_csv(args.out / "metrics.csv", index=False)
    ex.summarize(main_df, ["scenario", "controller"]).to_csv(args.out / "summary.csv", index=False)
    pd.concat([ex.paired_comparison(main_df, b) for b in ("webster", "fixed", "actuated", "opt_only", "fuzzy_only")]).to_csv(
        args.out / "comparisons.csv", index=False)

    if not args.skip_noise:
        log.info("3/5 experiment F: sensor-noise robustness")
        noise_df = ex.run_noise(cfg, tuned, seeds, workers=args.workers)
        noise_df.to_csv(args.out / "noise_metrics.csv", index=False)
        ex.summarize(noise_df, ["scenario", "noise", "controller"]).to_csv(
            args.out / "noise_summary.csv", index=False)

    if not args.skip_sweep:
        log.info("4/5 sensitivity: fuzzy-prior weight sweep")
        sweep = ex.run_weight_sweep(cfg, seeds, workers=args.workers)
        sweep.to_csv(args.out / "weight_sweep.csv", index=False)

    log.info("5/5 representative time series (seed %d)", seeds[0])
    ts, greens, decisions = ex.representative_runs(cfg, tuned, seeds[0])
    ts.to_csv(args.out / "timeseries.csv", index=False)
    greens.to_csv(args.out / "greens.csv", index=False)
    decisions.to_csv(args.out / "decisions.csv", index=False)

    ex.write_metadata(args.out / "run_metadata.json", cfg, tuned,
                      {"seeds_used": list(seeds), "quick": args.quick,
                       "runtime_s": round(time.time() - t0, 1)})
    log.info("done in %.0f s -> %s", time.time() - t0, args.out)


if __name__ == "__main__":
    main()
