# Methodology

This document specifies every component of the study precisely enough to explain,
critique or re-implement it. All parameter values live in `traffic_signal/config.py`.

## 1. Problem statement and objectives

Fixed-time signals repeat the same timing regardless of the traffic actually present.
This study asks:

1. Can a controller that combines **fuzzy inference** (expert rules over imprecise
   traffic measurements) with **constrained optimization** (a short-horizon queue
   prediction) allocate green time better than fixed-time and conventional adaptive
   (actuated) control?
2. What does each part contribute on its own?
3. How robust is the controller to imperfect sensors?

Performance is measured in simulation using delay, queue, stop and throughput metrics,
over five demand scenarios and 30 paired random seeds.

## 2. Simulation model (`simulator.py`, `demand.py`)

| Element | Model |
|---|---|
| Geometry | Isolated 4-way intersection; approaches N, S, E, W; one lane each |
| Phases | Two, served in fixed order: NS then EW. Each green is followed by 3 s yellow and 2 s all-red |
| Time step | 1 s |
| Arrivals | Poisson with a time-varying rate λᵢ(t); pre-generated per (scenario, seed) |
| Queues | Point (vertical) queues, FIFO, each vehicle tracked individually |
| Discharge | Saturation flow s = 0.5 veh/s (1800 veh/h) during green, after a 2 s start-up lost time; none during yellow/all-red. A credit accumulator handles the fractional rate; unused capacity cannot be banked |
| Lost time | 2 s start-up + 3 s yellow + 2 s all-red = 7 s per phase, so L = 14 s per cycle |
| Constraints | Enforced by the simulator for every controller: 10 s ≤ green ≤ 60 s; any two consecutive greens plus clearances ≤ 120 s |
| Run protocol | 600 s warm-up (not measured), 3600 s measurement window, then up to 900 s cool-down with arrivals continuing so measured vehicles can clear |

**Sensor layer (`Detector`).** Controllers never read the simulator's internals. They
receive an `Observation` containing:
- observed queue counts;
- an exponentially-weighted moving average (EWMA, τ = 120 s) of *detected* arrivals,
  used as the arrival-rate estimate;
- time since the last detection;
- the timing limits currently in force.

Experiment F adds Gaussian noise to the queue counts and drops a fraction of arrival
detections. The noise uses its own random stream, so the arrival sequence is identical
with and without noise.

**Scenarios** (veh/h per approach; demand is chosen so that Webster's optimal cycle
fits under the 120 s cap and the fixed-time baseline is not handicapped by constraints):

| Scenario | N, S | E, W | Notes |
|---|---|---|---|
| Low | 200 | 200 | stationary |
| Balanced | 450 | 450 | stationary |
| Heavy | 650 | 650 | stationary; flow-ratio sum Y = 0.72, Webster cycle ≈ 94 s |
| Imbalanced | 700 | 200 | stationary |
| Peak | 250 → 750 | 250 → 500 | Gaussian surge centred mid-window, σ = 10 min |
| *Tuning* | 400/350 → 650/600 | 350/300 → 450/400 | used only for parameter tuning |

**Consistency check.** Under Webster plans with stationary demand, simulated mean delay
matches Webster's delay formula:

| Scenario | Formula | Simulation | Difference |
|---|---|---|---|
| Low | 11.1 s | 11.1 s | +0% |
| Balanced | 17.6 s | 18.7 s | +6% |
| Heavy | 32.8 s | 33.5 s | +2% |

(30 seeds; the balanced case is also in `tests/test_simulator.py`.) This is internal
consistency with queueing theory, not validation against real traffic.

## 3. Fuzzy inference system (`fuzzy.py`)

The fuzzy system is evaluated **at the start of each phase**, for the phase about to be
served. The critical approach is the one in the phase with the larger queue or rate.

### 3.1 Linguistic variables and membership functions

Each term is a trapezoid (a, b, c, d); a triangle has b = c.

| Variable | Definition | Universe | Terms |
|---|---|---|---|
| **Queue Q** | queue on the phase's critical approach (veh) | 0–40 | SHORT (0,0,3,8) · MEDIUM (5,12,12,20) · LONG (15,25,40,40) |
| **Own intensity A** | y = λ̂ / s for the served phase (max over its approaches) | 0–1 | LOW (0,0,.08,.18) · MEDIUM (.10,.25,.25,.40) · HIGH (.32,.45,1,1) |
| **Competing intensity C** | y for the conflicting phase | 0–1 | same terms as A |
| **Green time** (output) | seconds | 10–60 | VERY_SHORT (10,10,12,20) · SHORT (12,20,20,30) · MEDIUM (22,32,32,42) · LONG (34,44,44,54) · VERY_LONG (46,56,60,60) |

**Why these breakpoints.** They come from physical quantities, not arbitrary choice:
- **SHORT queue:** a minimum green of 10 s discharges (10 − 2) × 0.5 = 4 vehicles, so a
  SHORT queue (fully SHORT ≤ 3 veh, gone by 8) clears within minimum green.
- **LONG queue:** 25 vehicles need 2 + 25/0.5 = 52 s, which is about the maximum green.
- **MEDIUM intensity:** it peaks at y = 0.25. Two phases at that level give Y = 0.5, a
  moderately loaded intersection.
- **HIGH intensity:** it is full from y = 0.45. The capacity limit is
  Y < 1 − L/C_max = 1 − 14/120 ≈ 0.88, i.e. about 0.44 per phase.

**Why these shapes:**
- Trapezoid shoulders encode saturation: "anything above 25 vehicles is LONG".
- Triangles/trapezoids are piecewise-linear, interpretable and cheap.
- Adjacent terms overlap, so the control surface changes smoothly.
- Output shoulders reduce centroid compression at the extremes. The centroid still
  cannot reach exactly 10 s or 60 s; the minimum possible output is ≈ 13.4 s.

**Why "arrival intensity" rather than density.** Density is vehicles per km, which a
point-queue model does not represent. The flow ratio y = λ/s is the standard
signal-timing measure of demand intensity and serves as our density proxy.

**Why competing intensity instead of own waiting pressure.** This was a design-review
decision.
- At phase start, the mean wait of the phase's own queue is roughly proportional to its
  preceding red time, so it largely duplicates the queue input.
- Signal control is a competition: giving one phase more green costs the other phase
  delay. The competing phase's demand captures that trade-off. Pappis & Mamdani's fuzzy
  junction controller likewise uses red-side information.
- Waiting-time fairness is enforced by the cycle cap and measured by the p95 and
  worst-approach delay metrics.

### 3.2 Rule base (27 rules)

`RULES[C][Q][A]` gives the output term:

```
C = LOW                 C = MEDIUM              C = HIGH
Q \ A  LOW  MED  HIGH   Q \ A  LOW  MED  HIGH   Q \ A  LOW  MED  HIGH
SHORT  VS   S    M      SHORT  VS   S    S      SHORT  VS   VS   S
MEDIUM S    M    L      MEDIUM S    M    M      MEDIUM S    S    M
LONG   L    VL   VL     LONG   M    L    VL     LONG   M    M    L
```

Example: *IF queue is LONG AND intensity is MEDIUM AND competing is LOW THEN green is
VERY_LONG.*

**Design principles:**
- Green rises with queue (the backlog must be served) and with own intensity (arrivals
  during green must also be served). It falls with competing intensity (the cost
  imposed on the other phase).
- A LONG queue always gets at least MEDIUM green, because the backlog must be cleared
  whatever the competition.
- A SHORT queue with LOW demand always gets VERY_SHORT, to avoid wasted green. When the
  whole junction is light, short cycles minimize delay.
- VERY_LONG is reachable only if the competing phase is not HIGH.

The table is monotone in every input, and `tests/test_fuzzy.py` enforces this.

### 3.3 Inference steps

1. **Fuzzification:** compute the membership degree of each crisp input in each term.
2. **Rule evaluation:** firing strength = min of the three antecedent memberships (AND = min).
3. **Implication:** clip each rule's output MF at its firing strength (min).
4. **Aggregation:** pointwise max over all clipped output sets.
5. **Defuzzification:** centroid, g = ∫ y μ(y) dy / ∫ μ(y) dy, over 501 samples of [10, 60].

The engine is vectorized with NumPy so the control surface and batch evaluations are cheap.

**A property worth knowing.** A monotone rule table does *not* make max-min Mamdani with
centroid strictly monotone: in overlap regions the centroid can dip slightly. We measured
a worst dip of about 0.6 s on a fine grid, below the 1 s resolution at which greens are
applied. The test checks near-monotonicity with a 1 s tolerance.

### 3.4 Worked example (actual decision; `scripts/explain_decision.py`)

Peak scenario, seed 100. The NS phase starts at t = 2414 s.
- **Observed state:** queues N, S, E, W = 4, 7, 2, 5 veh; estimated rates
  659/733/464/494 veh/h.
- **Inputs:** Q = 7, A = 0.407, C = 0.274.
- **Fuzzification:** Q is SHORT 0.20 / MEDIUM 0.29; A is HIGH 0.67; C is MEDIUM 0.84.
- **Fired rules:** (MEDIUM, HIGH, MEDIUM) → MEDIUM at strength 0.286;
  (SHORT, HIGH, MEDIUM) → SHORT at strength 0.200.
- **Centroid:** 27.9 s.
- **Optimizer:** chooses 27 s. J(27) = 2384, J(26) = 2387, J(28) = 2404.

## 4. Optimization layer (`optimizer.py`)

**Decision:** the green time g (integer seconds) of the phase about to start.

```
minimize    J(g) = Σ_{t=1..H} Σ_i q̂_i(t)            predicted total delay over the horizon [veh·s]
                 + ρ · Σ_i q̂_i(H)                   terminal backlog (delay pushed past H)
                 + w_Q · max_{i,t} q̂_i(t)           peak queue (storage / spill-back proxy)
                 + w_F · (g − g_fuzzy)²             fuzzy prior
subject to  g_min ≤ g ≤ g_max_now,   g ∈ ℤ
            g_max_now = min(g_max, C_max − 2·(Y + AR) − g_previous_other_phase)
```

H = 120 s, ρ = 30 s, w_Q = 20 s, and w_F is tuned from {0.25, 1, 4} veh/s; the tuning
selected 1.0.

**Predictor.** A deterministic fluid queue model per approach:
`q̂_i(t+1) = max(0, q̂_i(t) + λ̂_i − s·u_i(t))`.
- It starts from the *observed* queues and uses *estimated* rates, never the true future
  arrivals.
- u_i(t) = 1 when approach i discharges under the candidate schedule: the start-up lost
  time and clearance intervals are included.
- After the candidate green, the prediction continues with a Webster split computed from
  the same rate estimates, still under the cycle cap.

**Design choices and why:**
- **Fixed horizon for every candidate.** If the horizon grew with g, longer greens would
  accumulate delay over a longer window and candidates would not be comparable.
- **Terminal cost.** Without it, the optimizer could "hide" delay beyond the horizon.
- **Continuation that ignores the fuzzy system.** Optimization-only (w_F = 0) and
  Fuzzy + Opt then differ *only* in the prior term, which keeps the ablation clean.
- **Stops and imbalance are measured, not optimized.** A fluid model predicts them
  poorly; stops roughly follow delay and imbalance roughly follows peak queue. Fewer
  weights means fewer arbitrary choices.
- **Exhaustive integer search** over ≤ 51 candidates, evaluated in one vectorized pass.
  J is non-smooth (max, clipping at zero), so gradient methods such as SLSQP are
  unreliable. Brute force returns the exact minimizer of J, ties go to the shorter
  green, and it takes milliseconds.
- **Stopping criterion.** None is needed beyond enumeration: the search ends after the
  last feasible candidate is evaluated. There is no iteration limit, tolerance or time
  budget. Every returned g is one of the feasible candidates, so the optimizer cannot
  produce an invalid timing (checked on 500 random states in `tests/test_optimizer.py`).
- **Role of the fuzzy prior.** It acts as a trust region that keeps the model-based
  choice close to the rule-based judgement. That matters most when the model's
  estimates are wrong. The w_F sweep (fig12) shows how the trade-off behaves.

"Optimal" here means optimal **for the prediction model over the horizon**, not for the
real system.

## 5. Controllers (`controllers.py`)

All controllers share one interface:
- `on_phase_start(obs)` is called when a green begins.
- `should_end_green(obs)` is called every second after the minimum green.
- The simulator enforces the maximum itself.

| Controller | Logic |
|---|---|
| Fixed (equal split) | 40 s per phase (C = 90 s) |
| Fixed (Webster) | C₀ = (1.5L + 5)/(1 − Y), with greens proportional to the critical flow ratios. Uses the **true average demand** of each scenario's measurement window (oracle knowledge, which favours the baseline) |
| Actuated | Holds green while the served queue is non-empty or a vehicle was detected within `gap` s, otherwise ends it. `gap` is tuned from {2, 3, 4} s (tuning selected 2 s) |
| Fuzzy only | g = fuzzy output |
| Optimization only | g = argmin J with w_F = 0 (the fuzzy system is not consulted) |
| **Fuzzy + Opt** | g = argmin J with the fuzzy prior (w_F = 1.0) |

## 6. Metrics (`metrics.py`)

The evaluation set is vehicles *arriving* in the measurement window.

| Metric | Definition |
|---|---|
| Mean / p95 / max delay | departure − arrival (s). With point queues this equals waiting time at the stop line. Vehicles still queued at the end would be counted with their wait so far; none remained in any run |
| Worst-approach delay | largest of the four approaches' mean delays (a fairness measure) |
| Mean / max queue | queue per approach, time-averaged / maximum over the window |
| Stops per vehicle | share of vehicles that arrived on red/yellow, during start-up lost time, or behind a queue |
| Throughput | departures in the window (veh/h) |
| Residual vehicles | measured vehicles not served by the end of the run |

**Reading the metrics:**
- p95 is preferred to max delay, which is a single-vehicle extreme.
- Throughput equals demand whenever the intersection is undersaturated, so it does not
  separate the controllers here.
- Percentage changes are always reported with absolute differences. Small absolute
  differences can look large at low demand.

## 7. Experimental protocol (`experiments.py`)

- **Paired design (common random numbers):** for a given (scenario, seed), every
  controller sees exactly the same arrivals.
- **Evaluation seeds** 100–129 (n = 30).
- **Tuning:** only on the separate tuning scenario with seeds 0–4. The actuated gap and
  w_F get equal grid sizes. Neither the evaluation scenarios nor the evaluation seeds
  were used for tuning.
- **Statistics:**
  - mean ± 95% t-interval per controller;
  - for comparisons, a 95% t-interval of the per-seed **paired difference**, marked
    "significant" if it excludes zero;
  - the share of seeds on which the controller beat the baseline.
  - No correction for multiple comparisons is applied, so treat borderline results
    cautiously.
- **Experiment F (noise):** heavy and peak scenarios.
  - none (σ = 0, miss 0%)
  - moderate (σ = 2 veh, miss 10%)
  - severe (σ = 4 veh, miss 20%)
- **Sensitivity analysis:** w_F ∈ {0, 0.25, 1, 4, 16, 64, ∞} on all scenarios. This is
  analysis only; it was not used for selection.

## 8. Design-revision log

Recorded for transparency:

1. **Rule table, after the first smoke test** (one evaluation seed, before any tuning or
   full experiment). The entry (C = LOW, Q = SHORT, A = LOW) was SHORT and
   (C = LOW, Q = MEDIUM, A = LOW/MEDIUM) were MEDIUM. This contradicted the stated
   "no wasted green" principle and produced overly long cycles at low demand.
   - Revised to VERY_SHORT and SHORT/MEDIUM respectively.
   - Membership functions were deliberately **not** retuned on evaluation data.
2. **Monotonicity test.** Strict output monotonicity failed (the Mamdani/centroid
   property in §3.3). The test now bounds reversals at 1 s instead of claiming strict
   monotonicity.
3. **Ablation comparisons** (Fuzzy + Opt vs each component) were added to the
   pipeline's comparison output after the first full run. The underlying runs were
   unchanged.

## 9. Assumptions and limitations

- **Traffic model:**
  - Point queues, one lane per approach, through movements only.
  - No pedestrians, turning conflicts, spill-back, platoon arrivals or driver variability.
  - Deterministic saturation flow.
- **No field calibration.** The results show relative behaviour within this model only.
- **Model accuracy.** The predictor has the same structure as the simulator, so the
  optimizer's model is optimistic compared with real roads.
- **Decision timing.** Controllers that plan the whole green at phase start cannot react
  to arrivals within the green. The actuated baseline can.
- **Fixed-time baseline.** One plan per scenario, not time-of-day plans.
- **Hand-designed fuzzy parameters** and hand-chosen objective weights (ρ, w_Q). The w_F
  sweep covers only one of these weights.

## 10. Anticipated viva questions

- **What does fuzzy logic add?** A rule-based prior that reflects traffic-engineering
  judgement. In our experiments Fuzzy + Opt beat optimization-only by 2.0–2.8% in
  balanced, heavy and peak (significant) and matched it elsewhere. On its own, fuzzy
  inference was the least noise-sensitive controller.
- **Why not just use the optimizer?** It is slightly worse without the prior (above). A
  moderate prior weight also guards against model error.
- **Why is actuated better?** Our hypothesis is decision frequency: it reacts every
  second and ends green exactly when the queue clears. We did not test this; a
  receding-horizon variant would.
- **Is the optimizer optimal?** Exactly optimal for J under the fluid model over 120 s;
  not globally optimal for the stochastic system.
- **Why centroid defuzzification?** It is the standard choice for Mamdani controllers
  and uses the whole aggregated shape. Downsides: some computational cost, a compressed
  output range (≈ 13.4–55.1 s), and small non-monotonic dips.
- **Why not scikit-fuzzy?** A small NumPy engine exposes every step (see
  `explain_decision.py`), is vectorized for speed, and avoids a dependency. It is
  verified against hand-computed cases in the tests.

## 11. Mapping to report sections

| Report section | Source in this repository |
|---|---|
| Problem statement & objectives | §1 above; README introduction |
| Literature review | README background references (verify before citing): fuzzy sets, Mamdani control, Pappis & Mamdani junction controller, Webster, max-pressure |
| Proposed methodology | §2–§5 above; fig08, fig09 |
| Implementation | `traffic_signal/` modules, tests, §7 protocol |
| Results & analysis | `results/results_tables.md`, fig03–fig07, fig10–fig12 |
| Conclusion & future scope | README "What the experiments show", limitations, future work |
| Presentation & Q&A | §3.4 worked example, §10, `scripts/explain_decision.py` output figure |
