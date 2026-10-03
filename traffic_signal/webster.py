"""Webster's (1958) classical fixed-time signal-setting method and delay formula."""

from __future__ import annotations

import numpy as np

from .config import N_PHASES, PHASES, Config

MAX_FLOW_RATIO_SUM = 0.85  # guard: Webster's cycle diverges as Y -> 1


def phase_flow_ratios(rates: np.ndarray, cfg: Config) -> np.ndarray:
    """Critical flow ratio y_p = max approach rate in phase / saturation flow."""
    s = cfg.traffic.saturation_flow
    return np.array([max(rates[i] for i in PHASES[p]) / s for p in range(N_PHASES)])


def webster_plan(rates: np.ndarray, cfg: Config) -> tuple[np.ndarray, float]:
    """Displayed green per phase and cycle length from arrival rates (veh/s).

    C0 = (1.5 L + 5) / (1 - Y); effective greens split in proportion to y_p.
    Displayed green = effective green + start-up lost time (no discharge in yellow).
    """
    tm = cfg.timing
    y = phase_flow_ratios(rates, cfg)
    Y = min(float(y.sum()), MAX_FLOW_RATIO_SUM)
    L = N_PHASES * cfg.lost_time_per_phase
    c_min = N_PHASES * (tm.g_min + tm.clearance)
    cycle = float(np.clip((1.5 * L + 5.0) / (1.0 - Y), c_min, tm.c_max))
    share = y / y.sum() if y.sum() > 0 else np.full(N_PHASES, 1.0 / N_PHASES)
    greens = (cycle - L) * share + cfg.traffic.startup_lost
    greens = np.clip(np.round(greens), tm.g_min, tm.g_max)
    return greens, float(greens.sum() + N_PHASES * tm.clearance)


def webster_delay(flow: float, cycle: float, eff_green: float, sat: float) -> float:
    """Webster's average delay per vehicle (s) for one approach (flow, sat in veh/s)."""
    lam = eff_green / cycle
    x = flow / (sat * lam)
    if x >= 1.0:
        return float("inf")
    uniform = cycle * (1 - lam) ** 2 / (2 * (1 - lam * x))
    random = x**2 / (2 * flow * (1 - x))
    correction = 0.65 * (cycle / flow**2) ** (1 / 3) * x ** (2 + 5 * lam)
    return uniform + random - correction
