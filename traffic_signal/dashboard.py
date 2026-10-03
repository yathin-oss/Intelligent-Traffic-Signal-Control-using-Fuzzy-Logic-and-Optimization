"""Build a self-contained browser dashboard (results/dashboard.html) from results/*.csv.

The page replays recorded simulation runs (seed 100) and shows the 30-seed results. It
does not run the controller live: every number it shows comes from the CSVs written by
scripts/run_experiments.py.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .config import APPROACHES, SCENARIOS, Config
from .demand import mean_rates
from .plots import COLORS, LABELS, CONTROLLERS, SCENARIO_ORDER
from .webster import webster_plan

TEMPLATE = Path(__file__).with_name("dashboard_template.html")
SUMMARY_METRICS = ("mean_delay", "p95_delay", "max_delay", "worst_approach_delay",
                   "mean_queue", "max_queue", "stops_per_vehicle", "throughput_vph")


def _runs(ts: pd.DataFrame) -> dict:
    runs = {}
    for (sc, ctrl), g in ts.groupby(["scenario", "controller"], sort=False):
        g = g.sort_values("t")
        runs[f"{sc}|{ctrl}"] = {
            "q": [g[f"queue_{a}"].astype(int).tolist() for a in APPROACHES],
            # one digit per second: phase * 3 + state (state 0 green, 1 yellow, 2 all-red)
            "s": "".join(str(int(p) * 3 + int(s)) for p, s in zip(g["phase"], g["state"])),
        }
    return runs


def _demand(ts: pd.DataFrame, step: int = 30) -> dict:
    out = {}
    for sc, g in ts[ts.controller == "fixed"].groupby("scenario", sort=False):
        g = g.sort_values("t")
        out[sc] = {a: (g[f"true_rate_{a}"].to_numpy()[::step] * 3600).round(0).tolist()
                   for a in ("N", "E")}
    return out


def _decisions(dec: pd.DataFrame) -> dict:
    out = {}
    cols = ["time", "phase", "green", "queue", "intensity", "competing", "g_fuzzy", "g_opt"]
    for (sc, ctrl), g in dec.groupby(["scenario", "controller"], sort=False):
        rows = g[[c for c in cols if c in g]].to_numpy(dtype=float)
        out[f"{sc}|{ctrl}"] = [[None if np.isnan(v) else round(float(v), 3) for v in r]
                               for r in rows]
    return out


def build(results: Path, cfg: Config | None = None) -> Path:
    cfg = cfg or Config()
    ts = pd.read_csv(results / "timeseries.csv")
    summary = pd.read_csv(results / "summary.csv")
    comp = pd.read_csv(results / "comparisons.csv")
    tuning = pd.read_csv(results / "tuning.csv")
    meta = json.loads((results / "run_metadata.json").read_text())

    plans = {}
    for sc in SCENARIO_ORDER:
        greens, cycle = webster_plan(mean_rates(SCENARIOS[sc], *cfg.sim.window), cfg)
        plans[sc] = {"webster": [int(g) for g in greens], "webster_cycle": int(cycle)}
    gap = tuning[tuning.param == "actuated_gap"].sort_values("mean_delay").iloc[0]["value"]

    data = {
        "meta": {
            "windowStart": cfg.sim.window[0], "duration": cfg.sim.measure,
            "seed": int(meta.get("seeds_used", [100])[0]),
            "nSeeds": len(meta.get("seeds_used", [])), "generated": meta.get("generated_utc"),
            "fixedGreen": (90 - 2 * cfg.timing.clearance) // 2, "actuatedGap": float(gap),
            "wFuzzy": meta.get("tuned", {}).get("w_fuzzy"),
        },
        "controllers": [{"id": c, "label": LABELS[c], "color": COLORS[c]} for c in CONTROLLERS],
        "scenarios": SCENARIO_ORDER,
        "scenarioDemand": {sc: {"NS": SCENARIOS[sc].base[0], "EW": SCENARIOS[sc].base[2],
                                "peakNS": (SCENARIOS[sc].peak or SCENARIOS[sc].base)[0],
                                "peakEW": (SCENARIOS[sc].peak or SCENARIOS[sc].base)[2]}
                           for sc in SCENARIO_ORDER},
        "plans": plans,
        "runs": _runs(ts),
        "demand": _demand(ts),
        "decisions": _decisions(pd.read_csv(results / "decisions.csv")),
        "summary": [
            {"scenario": r.scenario, "controller": r.controller,
             **{m: round(float(getattr(r, f"{m}_mean")), 3) for m in SUMMARY_METRICS},
             **{f"{m}_ci": round(float(getattr(r, f"{m}_ci95")), 3) for m in SUMMARY_METRICS}}
            for r in summary.itertuples()
        ],
        "comparisons": [
            {"scenario": r.scenario, "baseline": r.baseline, "metric": r.metric,
             "improvement": round(float(r.improvement_pct), 2), "significant": bool(r.significant),
             "baselineMean": round(float(r.baseline_mean), 2),
             "controllerMean": round(float(r.controller_mean), 2)}
            for r in comp[(comp.controller == "fuzzy_opt")].itertuples()
        ],
    }
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    html = TEMPLATE.read_text().replace("__DATA_JSON__", payload)
    out = results / "dashboard.html"
    out.write_text(html)
    return out
