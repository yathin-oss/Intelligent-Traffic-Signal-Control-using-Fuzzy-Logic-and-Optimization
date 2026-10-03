# Intelligent Traffic Signal Control Using Fuzzy Logic and Optimization

A reproducible simulation study of an adaptive traffic-signal controller for an isolated
four-way intersection. A **Mamdani fuzzy inference system** proposes a green time from
the observed traffic state. A **model-predictive optimizer** then refines it under
signal-timing constraints. The controller is compared against fixed-time (equal split
and Webster) and vehicle-actuated baselines. The comparison uses 5 demand scenarios and
30 paired random seeds, and includes ablations, sensor-noise tests and a sensitivity
analysis.

> **Scope:** this is a research prototype evaluated in a simplified simulator, **not** a
> deployable system. Every number below was produced by the code in this repository and
> can be regenerated with the commands in [Reproducing the results](#reproducing-the-results).

---

## Headline results (mean delay per vehicle, seconds; 30 paired seeds)

| Scenario | Fixed (equal) | Fixed (Webster) | Actuated | Fuzzy only | Opt. only | **Fuzzy + Opt** |
|---|---:|---:|---:|---:|---:|---:|
| Low | 18.1 | 11.1 | **10.5** | 12.1 | 12.1 | 12.1 |
| Balanced | 21.8 | 18.7 | **14.6** | 17.6 | 17.9 | 17.4 |
| Heavy | 33.5 | 33.5 | **26.5** | 34.6 | 31.7 | 31.1 |
| Imbalanced | 39.9 | 15.5 | **13.3** | 15.2 | 14.8 | 14.7 |
| Peak | 26.3 | 36.6 | **15.8** | 19.6 | 19.1 | 18.6 |

The 95% confidence intervals, other metrics and paired-difference tests are in
[results/results_tables.md](results/results_tables.md).

**What the experiments show:**

1. **Fuzzy + Opt beats both fixed-time baselines in 4 of 5 scenarios.** Mean-delay
   reduction vs Webster: balanced 7.0%, heavy 7.2%, imbalanced 5.3%, peak 49.2%. All are
   significant (95% CI of the paired difference excludes zero).
   - **Exception:** under **low** traffic it is 8.6% *worse* than Webster (12.1 s vs 11.1 s).
   - The peak gain is large because a single Webster plan is timed for the hour's
     *average* demand and becomes oversaturated during the surge. Real deployments
     mitigate this with time-of-day plans, which are not modelled here.
2. **The hybrid is better than either component on its own, but the margins are small.**
   - **vs optimization only:** 2.0–2.8% lower delay (balanced, heavy, peak; significant).
     Not significant in low and imbalanced.
   - **vs fuzzy only:** 3.3–10.1% lower delay (heavy, imbalanced, peak; significant).
     Not significant in low and balanced.
3. **The vehicle-actuated baseline outperforms every other controller in every
   scenario.** Fuzzy + Opt has 10–19% higher mean delay than actuated. Our (untested)
   hypothesis:
   - The actuated controller re-decides every second and ends green as soon as the
     queue clears.
   - Our controller commits to a green duration at phase start, based on
     smoothed rate estimates.
   - A receding-horizon version that re-optimizes during the green would test this;
     see [Future work](#future-work).
4. **Sensor noise (Experiment F):** the fuzzy-based controllers degrade the least, but
   actuated is not overtaken.
   - Under severe noise (queue σ = 4 veh, 20% missed detections), actuated delay rises
     23% (heavy) and 26% (peak).
   - Fuzzy + Opt rises 12.5% and 10.7%; fuzzy only rises 1.0% and 4.8%.
   - In the peak scenario the gap to actuated nearly closes (19.9 ± 0.4 s vs
     20.6 ± 0.5 s). In heavy traffic actuated remains clearly better.
   - In heavy traffic, severe noise pushes every adaptive controller except actuated
     (32.6 s) above the sensor-free Webster plan (33.5 s): Fuzzy + Opt reaches 35.0 s.
5. **Throughput is identical across controllers.** All scenarios are undersaturated on
   average, so every controller eventually serves the demand. Delay and queue metrics
   are what separate them.

These findings hold **only for this simulator and its assumptions** (see
[Limitations](#assumptions-and-limitations)).

---

## How it works

```
arrivals (seeded Poisson) ─► Simulator (1 s steps, point queues, 2-phase signal)
                                  │ Observation (queues, EWMA arrival rates) — optional noise
                                  ▼
          ┌──── at each phase start ─────────────────────────────────────────────┐
          │ Features: Q = critical queue, A = own arrival intensity λ̂/s,         │
          │           C = competing phase arrival intensity                      │
          │ Fuzzy (Mamdani, 27 rules) ─► proposal g_fuzzy                        │
          │ Optimizer: g* = argmin J(g) over integer g ∈ [g_min, g_max_now]      │
          └───────────────────────────────────────────────────────────────────────┘
                                  ▼
             Simulator enforces min/max green + cycle cap ─► metrics
```

- **Fuzzy system.**
  - Trapezoidal/triangular membership functions, with breakpoints tied to physical
    quantities. Example: a SHORT queue (≤ ~4 veh) is one that clears within the 10 s
    minimum green.
  - A hand-designed, monotone 27-rule base; min for AND, max for aggregation, centroid
    defuzzification.
  - See [fig08](results/figures/fig08_membership_functions.png) and
    [fig09](results/figures/fig09_control_surface.png).
- **Optimization.**
  - Objective: J(g) = predicted delay over a fixed 120 s horizon + 30·(terminal backlog)
    + 20·(peak queue) + w_F·(g − g_fuzzy)².
  - The prediction uses a fluid queue model driven by *estimated* rates. The controller
    never sees future arrivals.
  - It is solved exactly by exhaustive integer search. w_F = 0 gives "optimization only".
- **Baselines.**
  - Equal-split fixed time (C = 90 s).
  - Webster fixed time, given oracle knowledge of each scenario's average demand. This
    favours the baseline.
  - Vehicle-actuated gap-out control.
  - The actuated gap and w_F got equal tuning budgets, on a separate tuning scenario and
    tuning seeds.

The full method is in [docs/methodology.md](docs/methodology.md). That includes the
rule table, the mathematical formulation, the design decisions and a design-revision log.

---

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m pytest                          # 30 tests (conservation, constraints, fuzzy, optimizer validity, Webster check)
python scripts/run_demo.py --scenario peak --controller fuzzy_opt
python scripts/build_dashboard.py          # opens the browser prototype (results/dashboard.html) in Chrome
python scripts/inspect_fuzzy.py            # membership functions, 27-rule table, sample inferences
python scripts/explain_decision.py --scenario peak --seed 100 --time 2400   # step-by-step trace of one decision
```

## Reproducing the results

```bash
python scripts/run_experiments.py         # ~90 s on a 10-core laptop; writes results/*.csv
python scripts/make_plots.py              # writes results/figures/*.png and results/results_tables.md
```

`--quick` uses 5 seeds and `--workers N` sets the number of processes. Runs are
deterministic for a given seed. `results/run_metadata.json` records the seeds, tuned
parameters, full configuration and package versions.

| Output | Contents |
|---|---|
| `metrics.csv` | one row per (scenario, controller, seed): all metrics |
| `summary.csv` | mean, std, 95% CI per scenario × controller |
| `comparisons.csv` | paired differences vs each baseline, with CIs and % improvement |
| `tuning.csv` | tuning-grid results (tuning scenario only) |
| `noise_metrics.csv`, `noise_summary.csv` | Experiment F (sensor noise) |
| `weight_sweep.csv` | sensitivity to the fuzzy-prior weight |
| `timeseries.csv`, `greens.csv`, `decisions.csv` | per-second / per-phase logs for seed 100 |

## Figures

| | |
|---|---|
| fig01 demand profiles | fig02 traffic distribution between approaches |
| fig03 all metrics × scenario × controller (with CIs) | fig04 % improvement heatmaps (mean and p95 delay) |
| fig05 queue length over time | fig06 green-time allocation per phase (peak, imbalanced) |
| fig07 arrival intensity (density proxy): true vs detector estimate | fig08 membership functions |
| fig09 fuzzy control surface | fig10 fuzzy proposal vs optimized green |
| fig11 robustness to sensor noise | fig12 sensitivity to the fuzzy-prior weight |

## Repository layout

```
traffic_signal/
  config.py       all parameters, scenarios, seeds (single source of truth)
  demand.py       time-varying demand, seeded Poisson arrivals, separate noise stream
  simulator.py    intersection, signal state machine, detector/observation layer
  fuzzy.py        membership functions, rule base, vectorized Mamdani engine, explain()
  optimizer.py    fluid predictor, objective, exhaustive search
  webster.py      Webster signal settings and delay formula
  controllers.py  fixed, Webster, actuated, fuzzy-only, opt-only, fuzzy+opt
  metrics.py      per-run metrics
  experiments.py  tuning, paired multi-seed runs, noise, sweep, statistics
  plots.py        figures and results tables from CSVs
scripts/          run_experiments, make_plots, build_dashboard, run_demo, explain_decision, inspect_fuzzy
tests/            simulator, fuzzy, optimizer tests
docs/             methodology.md
results/          generated outputs (committed from the final run)
```

## Assumptions and limitations

- **Simplified traffic model:**
  - One lane per approach and two phases (NS/EW).
  - No turning movements, pedestrians, lane changes or spill-back.
  - Point (vertical) queues, a deterministic saturation flow of 1800 veh/h, and Poisson
    arrivals.
  - The simulator is **not calibrated against field data**. Agreement with Webster's
    delay formula (within 0–6% for the Webster plans in the low/balanced/heavy
    scenarios) is a consistency check, not a validation.
- **The predictor and simulator share the same queueing structure.** The optimizer's
  model is therefore more accurate than it would be on a real road. The noise
  experiment probes this only partially.
- **Single isolated intersection.** No coordination or network effects.
- **Hand-designed fuzzy parameters.** They were set from physical reasoning. The rule
  table was corrected once after a smoke test (documented in the methodology). They are
  not learned or field-tuned.
- **"Optimal" means optimal for the predictive model over a 120 s horizon**, not for the
  real system.
- **Fixed-time baselines use one plan per scenario.** Real fixed-time systems often use
  time-of-day plans, which would narrow the peak-scenario gap.

## Future work

- **Receding-horizon re-optimization during the green.** This tests whether decision
  frequency explains the gap to actuated control.
- **More realistic simulation:** turning movements, protected-left phases, pedestrian
  phases, and a microscopic simulator (e.g. SUMO via TraCI). The controllers only depend
  on the `Observation` interface.
- **Real sensor inputs and coordination:** camera/loop-detector inputs through the same
  observation layer, and coordination across multiple intersections.
- **Tuning the fuzzy system from data** (e.g. optimizing membership-function
  breakpoints on tuning scenarios).

None of these are implemented.

## Background references

Check these against the original publications before citing them in a report.

- L. A. Zadeh, "Fuzzy sets," *Information and Control*, 8(3), 1965.
- E. H. Mamdani and S. Assilian, "An experiment in linguistic synthesis with a fuzzy logic controller," *Int. J. Man-Machine Studies*, 7(1), 1975.
- C. P. Pappis and E. H. Mamdani, "A fuzzy logic controller for a traffic junction," *IEEE Trans. Systems, Man, and Cybernetics*, 7(10), 1977.
- F. V. Webster, "Traffic signal settings," Road Research Technical Paper No. 39, HMSO, 1958.
- P. Varaiya, "Max pressure control of a network of signalized intersections," *Transportation Research Part C*, 36, 2013.
