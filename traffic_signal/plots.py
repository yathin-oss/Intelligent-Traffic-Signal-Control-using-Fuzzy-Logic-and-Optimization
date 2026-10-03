"""Figures generated exclusively from the CSVs written by scripts/run_experiments.py.

Colour: fixed categorical slot per controller (validated for colour-vision deficiency on
adjacent pairs), ordinal blue ramp for ordered fuzzy terms, blue<->red diverging map with
a grey midpoint for improvement percentages. Colour is never the only identity cue:
every multi-series chart has a legend and/or direct labels.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

from .config import APPROACHES, SCENARIOS, Config  # noqa: E402
from .demand import mean_rates  # noqa: E402
from .fuzzy import GREEN_TERMS, INTENSITY_TERMS, QUEUE_TERMS, FuzzyGreenController, trapmf  # noqa: E402

SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
CONTROLLERS = ["fixed", "webster", "actuated", "fuzzy_only", "opt_only", "fuzzy_opt"]
LABELS = {"fixed": "Fixed (equal split)", "webster": "Fixed (Webster)", "actuated": "Actuated",
          "fuzzy_only": "Fuzzy only", "opt_only": "Optimisation only", "fuzzy_opt": "Fuzzy + Opt"}
COLORS = dict(zip(CONTROLLERS, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]))
PHASE_COLORS = {"NS": "#4a3aa7", "EW": "#e34948"}  # violet / red slots, distinct from controllers
APPROACH_COLORS = dict(zip(APPROACHES, ["#4a3aa7", "#9085e9", "#e34948", "#f0a3a2"]))
ORDINAL = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]  # blue ramp 250..650
SCENARIO_ORDER = ["low", "balanced", "heavy", "imbalanced", "peak"]
DIVERGING = LinearSegmentedColormap.from_list(
    "improve", ["#b83232", "#e34948", "#f0efec", "#3987e5", "#1c5cab"])

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "sans-serif", "font.size": 9.5, "text.color": INK,
    "axes.labelcolor": INK2, "axes.edgecolor": AXIS, "axes.titlesize": 10.5,
    "axes.titleweight": "bold", "axes.titlecolor": INK, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.axisbelow": True, "xtick.color": MUTED, "ytick.color": MUTED,
    "xtick.labelcolor": INK2, "ytick.labelcolor": INK2, "legend.frameon": False,
    "lines.linewidth": 2.0, "figure.dpi": 110, "savefig.dpi": 160, "savefig.bbox": "tight",
})


def _save(fig, out: Path, name: str) -> Path:
    path = out / name
    fig.savefig(path)
    plt.close(fig)
    return path


def _legend_top(fig, controllers, ncol=6):
    handles = [plt.Rectangle((0, 0), 1, 1, color=COLORS[c]) for c in controllers]
    fig.legend(handles, [LABELS[c] for c in controllers], loc="upper center", ncol=ncol,
               bbox_to_anchor=(0.5, 1.02), handlelength=1.0, columnspacing=1.4)


def demand_profiles(cfg: Config, out: Path) -> Path:
    from .demand import arrival_rates
    fig, axes = plt.subplots(1, 5, figsize=(13, 2.6), sharey=True)
    t0, t1 = cfg.sim.window
    for ax, name in zip(axes, SCENARIO_ORDER):
        r = arrival_rates(SCENARIOS[name], cfg.sim.duration)[t0:t1] * 3600
        minutes = (np.arange(t0, t1) - t0) / 60
        for i, (label, col) in enumerate((("N/S", PHASE_COLORS["NS"]), ("E/W", PHASE_COLORS["EW"]))):
            ax.plot(minutes, r[:, 2 * i], color=col, label=label)
            ax.annotate(label, (minutes[-1], r[-1, 2 * i]), xytext=(3, 0),
                        textcoords="offset points", va="center", fontsize=8, color=INK2)
        ax.set_title(name.capitalize())
        ax.set_xlabel("minutes into measurement window")
    axes[0].set_ylabel("demand per approach (veh/h)")
    fig.suptitle("Traffic demand by scenario (expected arrival rate; actual arrivals are Poisson)",
                 y=1.04, fontsize=11)
    return _save(fig, out, "fig01_demand_profiles.png")


def traffic_distribution(cfg: Config, out: Path) -> Path:
    fig, ax = plt.subplots(figsize=(7.5, 2.8))
    for row, name in enumerate(SCENARIO_ORDER):
        rates = mean_rates(SCENARIOS[name], *cfg.sim.window)
        share = rates / rates.sum() * 100
        left = 0.0
        for i, a in enumerate(APPROACHES):
            ax.barh(row, share[i], left=left, color=APPROACH_COLORS[a], edgecolor=SURFACE,
                    linewidth=2, height=0.6)
            if share[i] >= 8:
                ax.text(left + share[i] / 2, row, f"{a} {share[i]:.0f}%", ha="center",
                        va="center", fontsize=7.5, color=INK if i in (1, 3) else "white")
            left += share[i]
    ax.set_yticks(range(5), [s.capitalize() for s in SCENARIO_ORDER])
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("share of arriving vehicles (%)")
    ax.grid(axis="y", visible=False)
    ax.set_title("Traffic distribution between approaches (measurement window)")
    return _save(fig, out, "fig02_traffic_distribution.png")


def metric_comparison(summary: pd.DataFrame, out: Path) -> Path:
    panels = [("mean_delay", "Mean delay per vehicle (s)"), ("p95_delay", "95th-percentile delay (s)"),
              ("worst_approach_delay", "Worst-approach mean delay (s)"),
              ("mean_queue", "Mean queue per approach (veh)"), ("max_queue", "Max queue (veh)"),
              ("throughput_vph", "Throughput (veh/h)")]
    fig, axes = plt.subplots(2, 3, figsize=(13, 6.4))
    width = 0.8 / len(CONTROLLERS)
    x = np.arange(len(SCENARIO_ORDER))
    for ax, (m, title) in zip(axes.flat, panels):
        for k, c in enumerate(CONTROLLERS):
            d = summary[summary.controller == c].set_index("scenario").loc[SCENARIO_ORDER]
            ax.bar(x + (k - 2.5) * width, d[f"{m}_mean"], width, yerr=d[f"{m}_ci95"],
                   color=COLORS[c], edgecolor=SURFACE, linewidth=1.2,
                   error_kw={"elinewidth": 0.9, "ecolor": INK2, "capsize": 0})
        ax.set_xticks(x, [s.capitalize() for s in SCENARIO_ORDER])
        ax.set_title(title)
        ax.grid(axis="x", visible=False)
    _legend_top(fig, CONTROLLERS)
    fig.text(0.5, -0.01, "Bars: mean over 30 paired seeds; whiskers: 95% confidence interval.",
             ha="center", color=MUTED, fontsize=8.5)
    fig.tight_layout()
    return _save(fig, out, "fig03_metric_comparison.png")


def improvement_heatmap(comp: pd.DataFrame, out: Path, metric: str = "mean_delay") -> Path:
    ctrls = [c for c in CONTROLLERS if c not in ("fixed",)]
    fig, axes = plt.subplots(1, 2, figsize=(13, 3.6), gridspec_kw={"wspace": 0.45})
    for ax, base in zip(axes, ("fixed", "webster")):
        cols = [c for c in ctrls if c != base]
        sub = comp[(comp.baseline == base) & (comp.metric == metric)]
        grid = sub.pivot(index="scenario", columns="controller", values="improvement_pct") \
            .loc[SCENARIO_ORDER, cols]
        sig = sub.pivot(index="scenario", columns="controller", values="significant") \
            .loc[SCENARIO_ORDER, cols]
        lim = max(10, float(np.nanmax(np.abs(grid.values))))
        im = ax.imshow(grid.values, cmap=DIVERGING, vmin=-lim, vmax=lim, aspect="auto")
        for i in range(grid.shape[0]):
            for j in range(grid.shape[1]):
                v = grid.values[i, j]
                txt = f"{v:+.1f}%" + ("" if sig.values[i, j] else "\n(n.s.)")
                ax.text(j, i, txt, ha="center", va="center", fontsize=8,
                        color="white" if abs(v) > 0.55 * lim else INK)
        ax.set_xticks(range(len(cols)), [LABELS[c] for c in cols], rotation=20, ha="right")
        ax.set_yticks(range(len(SCENARIO_ORDER)), [s.capitalize() for s in SCENARIO_ORDER])
        ax.grid(False)
        ax.set_title(f"vs {LABELS[base]}")
        cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
        cb.set_label("improvement (%)", color=INK2)
        cb.outline.set_visible(False)
    fig.suptitle("Change in mean delay relative to baseline (positive = lower delay = better; "
                 "n.s. = 95% CI of paired difference includes 0)", fontsize=10.5, y=1.03)
    return _save(fig, out, f"fig04_improvement_{metric}.png")


def queue_timeseries(ts: pd.DataFrame, out: Path,
                     controllers=("webster", "actuated", "fuzzy_opt")) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(13, 3.4), sharey=False)
    for ax, sc in zip(axes, ("peak", "imbalanced")):
        for c in controllers:
            d = ts[(ts.scenario == sc) & (ts.controller == c)]
            total = d[[f"queue_{a}" for a in APPROACHES]].sum(axis=1).rolling(60).mean()
            minutes = (d.t - d.t.min()) / 60
            ax.plot(minutes, total, color=COLORS[c], label=LABELS[c], linewidth=1.6)
        ax.set_title(f"{sc.capitalize()} scenario (seed 100)")
        ax.set_xlabel("minutes into measurement window")
        ax.set_ylabel("vehicles queued, all approaches\n(60 s rolling mean)")
        ax.legend(loc="upper left")
    fig.suptitle("Queue length over time (one representative seed)", y=1.03, fontsize=11)
    return _save(fig, out, "fig05_queue_timeseries.png")


def green_allocation(greens: pd.DataFrame, cfg: Config, out: Path, scenario: str = "peak",
                     controllers=("webster", "actuated", "fuzzy_opt")) -> Path:
    t0, t1 = cfg.sim.window
    fig, axes = plt.subplots(1, len(controllers), figsize=(13, 3.2), sharey=True)
    for ax, c in zip(axes, controllers):
        d = greens[(greens.scenario == scenario) & (greens.controller == c)
                   & (greens.start >= t0) & (greens.start < t1)]
        for ph, col in PHASE_COLORS.items():
            e = d[d.phase == ph]
            ax.plot((e.start - t0) / 60, e.green, color=col, marker="o", markersize=2.5,
                    linewidth=1.2, label=f"{ph} green")
        ax.set_title(LABELS[c])
        ax.set_xlabel("minutes into measurement window")
    axes[0].set_ylabel("green duration (s)")
    axes[0].legend(loc="upper left")
    fig.suptitle(f"Signal green-time allocation per phase — {scenario} scenario (seed 100)",
                 y=1.04, fontsize=11)
    return _save(fig, out, f"fig06_green_allocation_{scenario}.png")


def density_estimate(ts: pd.DataFrame, out: Path, scenario: str = "peak") -> Path:
    d = ts[(ts.scenario == scenario) & (ts.controller == "fuzzy_opt")]
    minutes = (d.t - d.t.min()) / 60
    fig, ax = plt.subplots(figsize=(8, 3.2))
    for a, ph in (("N", "NS"), ("E", "EW")):
        col = PHASE_COLORS[ph]
        ax.plot(minutes, d[f"true_rate_{a}"] / 0.5, color=col, linewidth=1.0, linestyle="--",
                label=f"{a}: true demand")
        ax.plot(minutes, d[f"est_rate_{a}"] / 0.5, color=col, linewidth=1.8,
                label=f"{a}: detector estimate (EWMA)")
    ax.set_ylabel("arrival intensity y = λ / s")
    ax.set_xlabel("minutes into measurement window")
    ax.set_title(f"Traffic density proxy over time — {scenario} scenario (seed 100)")
    ax.legend(ncol=2, loc="upper left", fontsize=8)
    return _save(fig, out, f"fig07_arrival_intensity_{scenario}.png")


def fuzzy_membership(cfg: Config, out: Path) -> Path:
    p = cfg.fuzzy
    specs = [("Queue length of critical approach (veh)", p.queue_universe, p.queue_terms, QUEUE_TERMS),
             ("Arrival intensity y (own or competing phase)", p.intensity_universe,
              p.intensity_terms, INTENSITY_TERMS),
             ("Green time output (s)", p.green_universe, p.green_terms, GREEN_TERMS)]
    fig, axes = plt.subplots(1, 3, figsize=(13, 2.8))
    for ax, (title, uni, terms, names) in zip(axes, specs):
        x = np.linspace(*uni, 801)
        ramp = [ORDINAL[0], ORDINAL[2], ORDINAL[4]] if len(names) == 3 else ORDINAL
        for n, col in zip(names, ramp):
            mu = trapmf(x, terms[n])
            ax.plot(x, mu, color=col, linewidth=2)
            xm = (terms[n][1] + terms[n][2]) / 2
            ha = "center"
            if terms[n][0] == terms[n][1] == uni[0]:
                xm, ha = uni[0], "left"
            elif terms[n][2] == terms[n][3] == uni[1]:
                xm, ha = uni[1], "right"
            ax.text(xm, 1.06, n.replace("_", " "), ha=ha, fontsize=7.5, color=INK2)
        ax.set_ylim(0, 1.18)
        ax.set_title(title)
        ax.set_ylabel("membership μ")
    fig.suptitle("Fuzzy membership functions", y=1.05, fontsize=11)
    return _save(fig, out, "fig08_membership_functions.png")


def control_surface(cfg: Config, out: Path) -> Path:
    fis = FuzzyGreenController(cfg.fuzzy)
    q = np.linspace(0, 40, 81)
    a = np.linspace(0, 0.6, 61)
    Q, A = np.meshgrid(q, a, indexing="ij")
    seq = LinearSegmentedColormap.from_list("seq", ["#cde2fb", "#6da7ec", "#2a78d6", "#184f95", "#0d366b"])
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.4), sharey=True)
    for ax, (c, label) in zip(axes, ((0.05, "LOW"), (0.25, "MEDIUM"), (0.45, "HIGH"))):
        G = fis.infer(Q.ravel(), A.ravel(), c).reshape(Q.shape)
        im = ax.imshow(G.T, origin="lower", aspect="auto", cmap=seq, vmin=10, vmax=60,
                       extent=(q[0], q[-1], a[0], a[-1]))
        cs = ax.contour(q, a, G.T, levels=[15, 20, 30, 40, 50], colors="white", linewidths=0.6)
        ax.clabel(cs, fmt="%d s", fontsize=7)
        ax.set_title(f"competing intensity = {c} ({label})")
        ax.set_xlabel("queue (veh)")
        ax.grid(False)
    axes[0].set_ylabel("own arrival intensity y")
    cb = fig.colorbar(im, ax=axes, fraction=0.02, pad=0.01)
    cb.set_label("fuzzy green time (s)", color=INK2)
    cb.outline.set_visible(False)
    fig.suptitle("Fuzzy control surface", y=1.03, fontsize=11)
    return _save(fig, out, "fig09_control_surface.png")


def fuzzy_vs_optimized(decisions: pd.DataFrame, out: Path) -> Path:
    d = decisions[decisions.controller == "fuzzy_opt"].dropna(subset=["g_fuzzy"])
    fig, axes = plt.subplots(1, 5, figsize=(13, 2.9), sharex=True, sharey=True)
    for ax, sc in zip(axes, SCENARIO_ORDER):
        e = d[d.scenario == sc]
        ax.plot([10, 60], [10, 60], color=AXIS, linewidth=1, linestyle="--")
        ax.scatter(e.g_fuzzy, e.g_opt, s=12, color=COLORS["fuzzy_opt"], alpha=0.55,
                   edgecolors=SURFACE, linewidths=0.5)
        ax.set_title(sc.capitalize())
        ax.set_xlabel("fuzzy proposal (s)")
    axes[0].set_ylabel("optimised green (s)")
    fig.suptitle("How the optimiser refines the fuzzy proposal (each dot = one phase decision, "
                 "seed 100; dashed = no change)", y=1.05, fontsize=10.5)
    return _save(fig, out, "fig10_fuzzy_vs_optimized.png")


def noise_robustness(noise_summary: pd.DataFrame, out: Path) -> Path:
    levels = ["none", "moderate", "severe"]
    ctrls = [c for c in CONTROLLERS if c in set(noise_summary.controller)]
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.4))
    for ax, sc in zip(axes, ("heavy", "peak")):
        for c in ctrls:
            d = noise_summary[(noise_summary.scenario == sc) & (noise_summary.controller == c)] \
                .set_index("noise").loc[levels]
            x = np.arange(3)
            ax.errorbar(x, d.mean_delay_mean, yerr=d.mean_delay_ci95, color=COLORS[c],
                        marker="o", markersize=5, capsize=0, elinewidth=0.9, label=LABELS[c])
        ax.set_xticks(range(3), ["none", "moderate\n(σ=2 veh, 10% missed)",
                                 "severe\n(σ=4 veh, 20% missed)"])
        ax.set_title(f"{sc.capitalize()} scenario")
        ax.set_ylabel("mean delay (s)")
        ax.grid(axis="x", visible=False)
    axes[0].legend(loc="upper left", fontsize=8)
    fig.suptitle("Robustness to sensor noise (Webster is sensor-free and serves as a reference)",
                 y=1.03, fontsize=11)
    return _save(fig, out, "fig11_noise_robustness.png")


def weight_sweep(sweep: pd.DataFrame, out: Path) -> Path:
    g = sweep.groupby(["scenario", "w_fuzzy"])["mean_delay"].agg(["mean", "std", "count"]).reset_index()
    g["ci"] = 1.96 * g["std"] / np.sqrt(g["count"])
    ws = sorted(g.w_fuzzy.unique())
    labels = ["0\n(opt only)" if w == 0 else ("∞\n(fuzzy only)" if np.isinf(w) else f"{w:g}") for w in ws]
    fig, axes = plt.subplots(1, 5, figsize=(13, 2.9))
    for ax, sc in zip(axes, SCENARIO_ORDER):
        d = g[g.scenario == sc].set_index("w_fuzzy").loc[ws]
        x = np.arange(len(ws))
        ax.fill_between(x, d["mean"] - d["ci"], d["mean"] + d["ci"], color=COLORS["fuzzy_opt"],
                        alpha=0.15, linewidth=0)
        ax.plot(x, d["mean"], color=COLORS["fuzzy_opt"], marker="o", markersize=4)
        ax.set_xticks(x, labels, fontsize=7)
        ax.set_title(sc.capitalize())
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("mean delay (s)")
    fig.suptitle("Sensitivity to the fuzzy-prior weight w_F (band: 95% CI)", y=1.05, fontsize=11)
    return _save(fig, out, "fig12_weight_sweep.png")


def results_tables(summary: pd.DataFrame, comp: pd.DataFrame, out_md: Path) -> Path:
    """Markdown tables of the main results (the table view behind the charts)."""
    lines = ["# Results tables (generated from results/*.csv)", "",
             "Mean ± 95% CI over paired seeds. Delay in seconds, queue in vehicles.", ""]
    cols = [("mean_delay", "Mean delay"), ("p95_delay", "P95 delay"),
            ("worst_approach_delay", "Worst-approach delay"), ("mean_queue", "Mean queue"),
            ("max_queue", "Max queue"), ("stops_per_vehicle", "Stops/veh"),
            ("throughput_vph", "Throughput (veh/h)")]
    for sc in SCENARIO_ORDER:
        lines += [f"## {sc.capitalize()}", "",
                  "| Controller | " + " | ".join(c[1] for c in cols) + " |",
                  "|---|" + "---:|" * len(cols)]
        for c in CONTROLLERS:
            r = summary[(summary.scenario == sc) & (summary.controller == c)].iloc[0]
            cells = []
            for m, _ in cols:
                prec = 2 if m in ("stops_per_vehicle", "mean_queue") else 1
                if m == "throughput_vph":
                    prec = 0
                cells.append(f"{r[m + '_mean']:.{prec}f} ± {r[m + '_ci95']:.{prec}f}")
            lines.append(f"| {LABELS[c]} | " + " | ".join(cells) + " |")
        lines.append("")
    lines += ["## Mean-delay change vs baselines (paired)", "",
              "Positive = lower delay than the baseline. CI is for the paired difference "
              "(controller − baseline, seconds).", "",
              "| Scenario | Controller | Baseline | Baseline (s) | Controller (s) | Δ (s) [95% CI] | "
              "Improvement | Seeds better |", "|---|---|---|---:|---:|---:|---:|---:|"]
    d = comp[(comp.metric == "mean_delay") & comp.baseline.isin(["fixed", "webster", "actuated"])]
    for _, r in d.iterrows():
        lines.append(
            f"| {r.scenario} | {LABELS[r.controller]} | {LABELS[r.baseline]} | {r.baseline_mean:.1f} | "
            f"{r.controller_mean:.1f} | {r.diff_mean:+.1f} [{r.diff_ci_low:+.1f}, {r.diff_ci_high:+.1f}] | "
            f"{r.improvement_pct:+.1f}%{'' if r.significant else ' (n.s.)'} | {r.frac_seeds_better:.0%} |")
    lines += ["", "## Ablation: Fuzzy + Opt vs its components (mean delay, paired)", "",
              "| Scenario | Compared with | Other (s) | Fuzzy + Opt (s) | Δ (s) [95% CI] | Improvement |",
              "|---|---|---:|---:|---:|---:|"]
    abl = comp[(comp.metric == "mean_delay") & (comp.controller == "fuzzy_opt")
               & comp.baseline.isin(["opt_only", "fuzzy_only"])]
    for _, r in abl.iterrows():
        lines.append(
            f"| {r.scenario} | {LABELS[r.baseline]} | {r.baseline_mean:.1f} | {r.controller_mean:.1f} | "
            f"{r.diff_mean:+.2f} [{r.diff_ci_low:+.2f}, {r.diff_ci_high:+.2f}] | "
            f"{r.improvement_pct:+.1f}%{'' if r.significant else ' (n.s.)'} |")
    out_md.write_text("\n".join(lines) + "\n")
    return out_md


def make_all(results: Path, cfg: Config | None = None) -> list[Path]:
    cfg = cfg or Config()
    out = results / "figures"
    out.mkdir(parents=True, exist_ok=True)
    summary = pd.read_csv(results / "summary.csv")
    comp = pd.read_csv(results / "comparisons.csv")
    ts = pd.read_csv(results / "timeseries.csv")
    greens = pd.read_csv(results / "greens.csv")
    decisions = pd.read_csv(results / "decisions.csv")
    paths = [
        demand_profiles(cfg, out), traffic_distribution(cfg, out),
        metric_comparison(summary, out), improvement_heatmap(comp, out, "mean_delay"),
        improvement_heatmap(comp, out, "p95_delay"),
        queue_timeseries(ts, out), green_allocation(greens, cfg, out, "peak"),
        green_allocation(greens, cfg, out, "imbalanced"), density_estimate(ts, out),
        fuzzy_membership(cfg, out), control_surface(cfg, out), fuzzy_vs_optimized(decisions, out),
    ]
    if (results / "noise_summary.csv").exists():
        paths.append(noise_robustness(pd.read_csv(results / "noise_summary.csv"), out))
    if (results / "weight_sweep.csv").exists():
        paths.append(weight_sweep(pd.read_csv(results / "weight_sweep.csv"), out))
    paths.append(results_tables(summary, comp, results / "results_tables.md"))
    return paths
