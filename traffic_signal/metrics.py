"""Per-run performance metrics.

Evaluation set: vehicles that ARRIVE inside the measurement window. Delay is
departure second - arrival second (point-queue model, so delay == waiting time at the
stop line). A vehicle still queued at the end of the run (after cool-down) is counted
with its wait so far (censored) and reported in `residual_vehicles`.

A vehicle is counted as *stopped* if it arrived when its approach was not discharging
freely: signal not green, start-up lost time, or vehicles already queued ahead.
"""

from __future__ import annotations

import numpy as np

from .config import N_APPROACHES, N_PHASES, Config
from .simulator import SimResult

METRICS = (
    "mean_delay", "p95_delay", "max_delay", "worst_approach_delay",
    "mean_queue", "max_queue", "stops_per_vehicle", "throughput_vph",
    "vehicles_measured", "residual_vehicles", "mean_cycle",
)
LOWER_IS_BETTER = {
    "mean_delay", "p95_delay", "max_delay", "worst_approach_delay",
    "mean_queue", "max_queue", "stops_per_vehicle", "residual_vehicles",
}


def compute_metrics(res: SimResult, cfg: Config) -> dict[str, float]:
    start, end = cfg.sim.window
    T = res.queues.shape[0]
    in_window = (res.veh_arrival >= start) & (res.veh_arrival < end)
    arr, dep = res.veh_arrival[in_window], res.veh_departure[in_window]
    approach, stopped = res.veh_approach[in_window], res.veh_stopped[in_window]
    departed = dep >= 0
    delay = np.where(departed, dep - arr, (T - 1) - arr).astype(float)

    per_approach = [delay[approach == i].mean() for i in range(N_APPROACHES)
                    if (approach == i).any()]
    q = res.queues[start:end]
    departures_in_window = ((res.veh_departure >= start) & (res.veh_departure < end)).sum()
    cycles = [d for (_, s, d) in res.greens if start <= s < end]
    # mean cycle = mean green per phase * n_phases + clearances
    mean_cycle = N_PHASES * (np.mean(cycles) + cfg.timing.clearance) if cycles else float("nan")

    n = len(delay)
    return {
        "mean_delay": float(delay.mean()) if n else 0.0,
        "p95_delay": float(np.percentile(delay, 95)) if n else 0.0,
        "max_delay": float(delay.max()) if n else 0.0,
        "worst_approach_delay": float(max(per_approach)) if per_approach else 0.0,
        "mean_queue": float(q.mean()),
        "max_queue": float(q.max()),
        "stops_per_vehicle": float(stopped.mean()) if n else 0.0,
        "throughput_vph": float(departures_in_window * 3600.0 / (end - start)),
        "vehicles_measured": float(n),
        "residual_vehicles": float((~departed).sum()),
        "mean_cycle": float(mean_cycle),
    }
