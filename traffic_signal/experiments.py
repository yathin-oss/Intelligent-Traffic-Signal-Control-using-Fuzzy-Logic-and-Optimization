"""Experiment runner: tuning, paired multi-seed comparisons, robustness and sensitivity.

Fairness protocol
- Common random numbers: for a given (scenario, seed) every controller sees the same
  arrival stream; sensor noise uses a separate stream.
- Tuning uses TUNING_SCENARIO and TUNING_SEEDS only, never the evaluation scenarios/seeds.
- The proposed controller (w_fuzzy) and the actuated baseline (gap) get equal tuning budgets.
"""

from __future__ import annotations

import json
import logging
import platform
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, replace
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from .config import (
    ACTUATED_GAP_GRID, APPROACHES, EVAL_SEEDS, NOISE_LEVELS, PHASE_NAMES, SCENARIOS,
    TUNING_SCENARIO, TUNING_SEEDS, W_FUZZY_GRID, Config, NoiseParams, Scenario,
)
from .controllers import CONTROLLER_NAMES, Controller, OptimizedController, build_controller
from .demand import arrival_rates, generate_arrivals, make_streams
from .metrics import LOWER_IS_BETTER, METRICS, compute_metrics
from .simulator import SimResult, Simulator

log = logging.getLogger(__name__)


def simulate(scenario: Scenario, controller: Controller, seed: int, cfg: Config,
             noise: NoiseParams = NoiseParams()) -> SimResult:
    arr_rng, noise_rng = make_streams(seed)
    arrivals = generate_arrivals(arrival_rates(scenario, cfg.sim.duration), arr_rng)
    return Simulator(cfg).run(controller, arrivals, noise_rng, noise)


def _job(args: tuple) -> dict:
    """One run -> one metrics row (top-level so it can be pickled for multiprocessing)."""
    scenario, ctrl_name, seed, cfg, tuned, noise, labels = args
    if ctrl_name.startswith("w_fuzzy="):  # sensitivity sweep entries
        w = float(ctrl_name.split("=", 1)[1])
        controller: Controller = OptimizedController(cfg, w_fuzzy=w)
    else:
        controller = build_controller(ctrl_name, cfg, scenario, tuned)
    res = simulate(scenario, controller, seed, cfg, noise)
    return {"scenario": scenario.name, "controller": ctrl_name, "seed": seed, **labels,
            **compute_metrics(res, cfg)}


def run_jobs(jobs: list[tuple], workers: int) -> pd.DataFrame:
    if workers <= 1:
        rows = [_job(j) for j in jobs]
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            rows = list(pool.map(_job, jobs, chunksize=8))
    return pd.DataFrame(rows)


def tune(cfg: Config, workers: int = 1) -> tuple[dict[str, float], pd.DataFrame]:
    """Pick actuated gap and fuzzy-prior weight by mean delay on the tuning scenario."""
    jobs = []
    for gap in ACTUATED_GAP_GRID:
        jobs += [(TUNING_SCENARIO, "actuated", s, cfg, {"actuated_gap": gap}, NoiseParams(),
                  {"param": "actuated_gap", "value": gap}) for s in TUNING_SEEDS]
    for w in W_FUZZY_GRID:
        jobs += [(TUNING_SCENARIO, "fuzzy_opt", s, cfg, {"w_fuzzy": w}, NoiseParams(),
                  {"param": "w_fuzzy", "value": w}) for s in TUNING_SEEDS]
    df = run_jobs(jobs, workers)
    table = df.groupby(["param", "value"], as_index=False)["mean_delay"].mean()
    tuned = {p: float(g.loc[g["mean_delay"].idxmin(), "value"]) for p, g in table.groupby("param")}
    log.info("tuned parameters: %s", tuned)
    return tuned, table


def run_main(cfg: Config, tuned: dict, seeds=EVAL_SEEDS, workers: int = 1) -> pd.DataFrame:
    jobs = [(sc, c, s, cfg, tuned, NoiseParams(), {})
            for sc in SCENARIOS.values() for c in CONTROLLER_NAMES for s in seeds]
    return run_jobs(jobs, workers)


def run_noise(cfg: Config, tuned: dict, seeds=EVAL_SEEDS, scenarios=("heavy", "peak"),
              controllers=("webster", "actuated", "fuzzy_only", "opt_only", "fuzzy_opt"),
              workers: int = 1) -> pd.DataFrame:
    jobs = [(SCENARIOS[sc], c, s, cfg, tuned, noise, {"noise": level})
            for level, noise in NOISE_LEVELS.items()
            for sc in scenarios for c in controllers for s in seeds]
    return run_jobs(jobs, workers)


def run_weight_sweep(cfg: Config, seeds=EVAL_SEEDS, grid=(0.0, 0.25, 1.0, 4.0, 16.0, 64.0),
                     workers: int = 1) -> pd.DataFrame:
    """Sensitivity of the hybrid to the fuzzy-prior weight (0 = optimisation only); the
    fuzzy-only controller is the w -> infinity limit. Analysis only, not used for tuning."""
    names = [f"w_fuzzy={w}" for w in grid] + ["fuzzy_only"]
    jobs = [(sc, n, s, cfg, {}, NoiseParams(), {}) for sc in SCENARIOS.values()
            for n in names for s in seeds]
    df = run_jobs(jobs, workers)
    df["w_fuzzy"] = df["controller"].map(
        lambda n: float(n.split("=")[1]) if n.startswith("w_fuzzy=") else np.inf)
    return df


def summarize(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """Mean, std and 95% t-confidence half-width for every metric."""
    rows = []
    for key, g in df.groupby(by, sort=False):
        key = key if isinstance(key, tuple) else (key,)
        row = dict(zip(by, key))
        n = len(g)
        row["n"] = n
        for m in METRICS:
            v = g[m].to_numpy(dtype=float)
            sd = v.std(ddof=1) if n > 1 else 0.0
            row[f"{m}_mean"] = v.mean()
            row[f"{m}_std"] = sd
            row[f"{m}_ci95"] = stats.t.ppf(0.975, n - 1) * sd / np.sqrt(n) if n > 1 else 0.0
        rows.append(row)
    return pd.DataFrame(rows)


def paired_comparison(df: pd.DataFrame, baseline: str,
                      metrics=("mean_delay", "p95_delay", "worst_approach_delay", "mean_queue",
                               "max_queue", "stops_per_vehicle", "throughput_vph")) -> pd.DataFrame:
    """Per-seed paired differences (controller - baseline) with 95% CIs.

    improvement_pct = (baseline_mean - controller_mean) / baseline_mean * 100, sign-flipped
    for higher-is-better metrics, so positive always means better than the baseline.
    """
    rows = []
    for sc, g in df.groupby("scenario", sort=False):
        base = g[g["controller"] == baseline].set_index("seed")
        for ctrl, h in g.groupby("controller", sort=False):
            if ctrl == baseline:
                continue
            h = h.set_index("seed").loc[base.index]
            for m in metrics:
                d = (h[m] - base[m]).to_numpy(dtype=float)
                n = len(d)
                half = stats.t.ppf(0.975, n - 1) * d.std(ddof=1) / np.sqrt(n) if n > 1 else 0.0
                bm = base[m].mean()
                sign = 1.0 if m in LOWER_IS_BETTER else -1.0
                better = (sign * d < 0).mean()
                rows.append({
                    "scenario": sc, "controller": ctrl, "baseline": baseline, "metric": m,
                    "baseline_mean": bm, "controller_mean": h[m].mean(),
                    "diff_mean": d.mean(), "diff_ci_low": d.mean() - half,
                    "diff_ci_high": d.mean() + half,
                    "improvement_pct": sign * (bm - h[m].mean()) / bm * 100 if bm else np.nan,
                    "significant": bool((d.mean() - half) * (d.mean() + half) > 0),
                    "frac_seeds_better": better,
                })
    return pd.DataFrame(rows)


def representative_runs(cfg: Config, tuned: dict, seed: int) -> tuple[pd.DataFrame, ...]:
    """Per-second time series, green log and decision log for one seed (for plots)."""
    ts_frames, green_rows, decision_rows = [], [], []
    start, end = cfg.sim.window
    for sc in SCENARIOS.values():
        true_rates = arrival_rates(sc, cfg.sim.duration)
        for name in CONTROLLER_NAMES:
            ctrl = build_controller(name, cfg, sc, tuned)
            res = simulate(sc, ctrl, seed, cfg)
            sl = slice(start, end)
            frame = pd.DataFrame({"t": np.arange(start, end), "scenario": sc.name,
                                  "controller": name, "phase": res.phase[sl],
                                  "state": res.state[sl]})
            for i, a in enumerate(APPROACHES):
                frame[f"queue_{a}"] = res.queues[sl, i]
                frame[f"est_rate_{a}"] = res.est_rates[sl, i].round(5)
                frame[f"true_rate_{a}"] = true_rates[sl, i].round(5)
            ts_frames.append(frame)
            green_rows += [{"scenario": sc.name, "controller": name, "phase": PHASE_NAMES[p],
                            "start": s, "green": d} for (p, s, d) in res.greens]
            for d in getattr(ctrl, "decisions", []):
                decision_rows.append({"scenario": sc.name, "controller": name, **d})
    return pd.concat(ts_frames), pd.DataFrame(green_rows), pd.DataFrame(decision_rows)


def write_metadata(path: Path, cfg: Config, tuned: dict, extra: dict) -> None:
    pkgs = {}
    for p in ("numpy", "pandas", "scipy", "matplotlib"):
        try:
            pkgs[p] = metadata.version(p)
        except metadata.PackageNotFoundError:
            pkgs[p] = None
    meta = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": sys.version.split()[0], "platform": platform.platform(), "packages": pkgs,
        "eval_seeds": list(EVAL_SEEDS), "tuning_seeds": list(TUNING_SEEDS),
        "tuned": tuned, "config": asdict(replace(cfg)),
        "scenarios": {k: asdict(v) for k, v in SCENARIOS.items()},
        "tuning_scenario": asdict(TUNING_SCENARIO),
        "noise_levels": {k: asdict(v) for k, v in NOISE_LEVELS.items()}, **extra,
    }
    path.write_text(json.dumps(meta, indent=2, default=str))
