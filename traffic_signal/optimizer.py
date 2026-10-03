"""Model-predictive refinement of the current phase's green time.

At each phase start we choose g for the phase about to be served:

    g* = argmin_{g in {g_min..g_max_now}} J(g)
    J(g) = sum_t sum_i q_i(t)              total predicted delay over a FIXED horizon H
         + rho     * sum_i q_i(H)          terminal backlog (delay pushed past H)
         + w_queue * max_{i,t} q_i(t)      storage / spill-back proxy
         + w_fuzzy * (g - g_fuzzy)^2       fuzzy prior (0 => optimisation only)

Predictor: fluid queues q_i(t+1) = max(0, q_i(t) + lambda_i - s*u_i(t)), starting from
the observed queues and using the detector's *estimated* rates (never true future
arrivals). After the candidate green, the prediction continues with a Webster split
computed from the same estimates, which is independent of the fuzzy system so that
the only difference between optimisation-only and fuzzy+optimisation is w_fuzzy.

Decision variable: g, the integer green time (s) of the phase about to start.
Constraints: g_min <= g <= g_max_now, where g_max_now = min(g_max, C_max - 2*(Y+AR) -
previous green of the other phase); g_max_now >= g_min always holds (the simulator
clamps it), so the feasible set is never empty.
Algorithm and stopping criterion: exhaustive enumeration of every feasible integer g
(at most g_max - g_min + 1 = 51 candidates), evaluated in one vectorised pass. It stops
after the last candidate is evaluated - there is no iteration count, tolerance or time
limit - and returns the exact minimiser of J (ties -> shortest green). Every returned g
is one of the enumerated feasible candidates, so an invalid timing cannot be produced.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import N_APPROACHES, N_PHASES, PHASES, Config
from .webster import webster_plan


@dataclass
class OptimizationResult:
    green: int
    candidates: np.ndarray
    objective: np.ndarray
    delay: np.ndarray
    terminal: np.ndarray
    max_queue: np.ndarray


class GreenTimeOptimizer:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg

    def _service_mask(self, phase: int, candidates: np.ndarray, rates: np.ndarray) -> np.ndarray:
        """(K, H, n_approaches) bool: approach discharging at second t under candidate k."""
        cfg, tm = self.cfg, self.cfg.timing
        H, startup = cfg.optimizer.horizon, cfg.traffic.startup_lost
        cont, _ = webster_plan(rates, cfg)
        mask = np.zeros((len(candidates), H, N_APPROACHES), dtype=bool)
        for k, g in enumerate(candidates):
            t, p, green, prev = 0, phase, int(g), None
            while t < H:
                if prev is not None:  # respect the two-phase cycle cap in the rollout too
                    cap = tm.c_max - N_PHASES * tm.clearance - prev
                    green = int(max(tm.g_min, min(green, cap)))
                start, end = min(t + startup, H), min(t + green, H)
                if end > start:
                    mask[k, start:end, list(PHASES[p])] = True
                t += green + tm.clearance
                prev, p = green, (p + 1) % N_PHASES
                green = int(cont[p])
        return mask

    def optimize(self, phase: int, queues: np.ndarray, rates: np.ndarray, g_min: int,
                 g_max_now: int, g_prior: float | None = None,
                 w_fuzzy: float | None = None) -> OptimizationResult:
        opt = self.cfg.optimizer
        w_fuzzy = opt.w_fuzzy if w_fuzzy is None else w_fuzzy
        if g_max_now < g_min:
            raise ValueError("g_max_now must be >= g_min")
        candidates = np.arange(g_min, g_max_now + 1)
        serve = self._service_mask(phase, candidates, rates)
        s = self.cfg.traffic.saturation_flow
        q = np.tile(np.asarray(queues, dtype=float), (len(candidates), 1))  # (K, 4)
        lam = np.asarray(rates, dtype=float)
        delay = np.zeros(len(candidates))
        max_q = q.max(axis=1)
        for t in range(opt.horizon):
            q = np.maximum(0.0, q + lam - s * serve[:, t, :])
            delay += q.sum(axis=1)
            max_q = np.maximum(max_q, q.max(axis=1))
        terminal = q.sum(axis=1)
        J = delay + opt.rho * terminal + opt.w_queue * max_q
        if g_prior is not None and w_fuzzy > 0:
            J = J + w_fuzzy * (candidates - g_prior) ** 2
        best = int(np.argmin(J))
        return OptimizationResult(int(candidates[best]), candidates, J, delay, terminal, max_q)
