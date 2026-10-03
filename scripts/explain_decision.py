"""Trace one fuzzy + optimisation decision step by step (fuzzification, fired rules,
aggregation, centroid, optimiser objective) and save a figure.

    # a real decision from a simulation run (first phase start at/after --time seconds)
    python scripts/explain_decision.py --scenario peak --seed 100 --time 2400
    # or hand-picked fuzzy inputs only
    python scripts/explain_decision.py --queue 14 --intensity 0.30 --competing 0.20
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from traffic_signal.config import PHASE_NAMES, SCENARIOS, Config  # noqa: E402
from traffic_signal.controllers import OptimizedController, fuzzy_inputs  # noqa: E402
from traffic_signal.experiments import simulate  # noqa: E402
from traffic_signal.fuzzy import FuzzyGreenController  # noqa: E402
from traffic_signal.optimizer import GreenTimeOptimizer  # noqa: E402
from traffic_signal.plots import COLORS, INK2  # noqa: E402


class _Capture(OptimizedController):
    """Fuzzy+Opt controller that records the observation at the first phase start >= t."""

    def __init__(self, cfg: Config, w: float, t: int) -> None:
        super().__init__(cfg, w)
        self.t, self.obs = t, None

    def on_phase_start(self, obs) -> None:
        if self.obs is None and obs.time >= self.t:
            self.obs = obs
        super().on_phase_start(obs)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--scenario", choices=sorted(SCENARIOS), default="peak")
    ap.add_argument("--seed", type=int, default=100)
    ap.add_argument("--time", type=int, default=2400)
    ap.add_argument("--w-fuzzy", type=float, default=1.0)
    ap.add_argument("--queue", type=float)
    ap.add_argument("--intensity", type=float)
    ap.add_argument("--competing", type=float)
    ap.add_argument("--out", type=Path, default=Path("results/figures/explain_decision.png"))
    args = ap.parse_args()
    cfg = Config()
    fis = FuzzyGreenController(cfg.fuzzy)

    opt_res = None
    if args.queue is not None:
        if args.intensity is None or args.competing is None:
            sys.exit("--queue needs --intensity and --competing")
        q, a, c = args.queue, args.intensity, args.competing
    else:
        ctrl = _Capture(cfg, args.w_fuzzy, args.time)
        simulate(SCENARIOS[args.scenario], ctrl, args.seed, cfg)
        obs = ctrl.obs
        if obs is None:
            sys.exit("no phase start after --time")
        q, a, c = fuzzy_inputs(obs, cfg.traffic.saturation_flow)
        print(f"Scenario {args.scenario}, seed {args.seed}: phase {PHASE_NAMES[obs.phase]} starts "
              f"at t={obs.time + 1} s")
        print(f"  observed queues N,S,E,W = {obs.queues.astype(int).tolist()} veh")
        print(f"  estimated rates N,S,E,W = {(obs.rates * 3600).round(0).tolist()} veh/h")
        print(f"  allowed green range = [{obs.g_min}, {obs.g_max_now}] s")

    e = fis.explain(q, a, c)
    print("\n1. Crisp inputs:", {k: round(v, 3) for k, v in e.inputs.items()})
    print("2. Fuzzification:")
    for var, mu in e.memberships.items():
        print(f"     {var:10s} {mu}")
    print("3. Rule evaluation (AND = min), fired rules:")
    for text, w in e.fired_rules:
        print(f"     {w:.3f}  {text}")
    print("4. Aggregation (max per output term):", e.term_activation)
    print(f"5. Centroid defuzzification -> fuzzy green = {e.green:.1f} s")

    if args.queue is None:
        opt_res = GreenTimeOptimizer(cfg).optimize(obs.phase, obs.queues, obs.rates, obs.g_min,
                                                   obs.g_max_now, e.green, args.w_fuzzy)
        order = np.argsort(opt_res.objective)[:5]
        print(f"6. Optimisation over g in [{obs.g_min}, {obs.g_max_now}] (w_fuzzy={args.w_fuzzy}):")
        for k in order:
            print(f"     g={opt_res.candidates[k]:2d} s  J={opt_res.objective[k]:8.1f}  "
                  f"delay={opt_res.delay[k]:7.1f}  terminal={opt_res.terminal[k]:5.1f}  "
                  f"maxq={opt_res.max_queue[k]:5.1f}")
        print(f"   -> final green = {opt_res.green} s (fuzzy proposal {e.green:.1f} s)")

    ncols = 2 if opt_res is not None else 1
    fig, axes = plt.subplots(1, ncols, figsize=(5.5 * ncols, 3.2), squeeze=False)
    ax = axes[0, 0]
    ax.fill_between(e.universe, e.aggregated, color="#2a78d6", alpha=0.35, linewidth=0)
    ax.plot(e.universe, e.aggregated, color="#2a78d6")
    ax.axvline(e.green, color=INK2, linestyle="--", linewidth=1)
    ax.text(e.green, 1.02, f" centroid {e.green:.1f} s", color=INK2, fontsize=8)
    ax.set_ylim(0, 1.1)
    ax.set_xlabel("green time (s)")
    ax.set_ylabel("aggregated membership")
    ax.set_title("Fuzzy output (clipped + aggregated)")
    if opt_res is not None:
        ax = axes[0, 1]
        ax.plot(opt_res.candidates, opt_res.objective, color=COLORS["fuzzy_opt"])
        ax.axvline(opt_res.green, color=COLORS["fuzzy_opt"], linestyle="--", linewidth=1)
        ax.axvline(e.green, color=INK2, linestyle=":", linewidth=1)
        ax.set_xlabel("candidate green g (s)")
        ax.set_ylabel("objective J(g)")
        ax.set_title(f"Optimiser: g* = {opt_res.green} s (dotted = fuzzy)")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(args.out)
    print(f"\nfigure -> {args.out}")


if __name__ == "__main__":
    main()
