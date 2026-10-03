"""Mamdani fuzzy inference system for green-time allocation.

Inputs (evaluated at the start of a phase, for the phase about to be served):
    Q  queue length of the phase's critical approach (veh)          - backlog
    A  arrival intensity of the served phase, y = lambda_hat / s     - demand during green
    C  arrival intensity of the competing phase                      - cost to the other side
Output:
    green time (s)

Pipeline: fuzzification (trapezoidal MFs) -> rule evaluation (AND = min) ->
implication (min, clipping) -> aggregation (max) -> centroid defuzzification.
The engine is vectorised over a batch of inputs.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import FuzzyParams

QUEUE_TERMS = ("SHORT", "MEDIUM", "LONG")
INTENSITY_TERMS = ("LOW", "MEDIUM", "HIGH")
GREEN_TERMS = ("VERY_SHORT", "SHORT", "MEDIUM", "LONG", "VERY_LONG")
VS, S, M, L, VL = range(5)

# RULES[c][q][a] -> output term. Green time rises with queue (rows) and own intensity
# (columns) and falls with competing intensity (tables). Hand-designed nonlinearities:
#   - a LONG queue always gets at least MEDIUM (the backlog must be cleared),
#   - a SHORT queue with LOW demand gets VERY_SHORT whatever the competition (no wasted
#     green; short cycles minimise delay when the whole junction is light),
#   - VERY_LONG is reachable only when the competing phase is not HIGH.
RULES = np.array(
    [
        # competing LOW:  own intensity LOW, MEDIUM, HIGH
        [[VS, S, M], [S, M, L], [L, VL, VL]],  # queue SHORT / MEDIUM / LONG
        # competing MEDIUM
        [[VS, S, S], [S, M, M], [M, L, VL]],
        # competing HIGH
        [[VS, VS, S], [S, S, M], [M, M, L]],
    ],
    dtype=np.int64,
)


def trapmf(x: np.ndarray, params: tuple[float, float, float, float]) -> np.ndarray:
    """Trapezoidal membership (a, b, c, d); b == c gives a triangle, a == b or c == d a
    shoulder. Handles vertical edges without division by zero."""
    a, b, c, d = params
    if not (a <= b <= c <= d):
        raise ValueError(f"trapezoid parameters must be ordered, got {params}")
    x = np.asarray(x, dtype=float)
    rise = np.ones_like(x) if b == a else np.clip((x - a) / (b - a), 0.0, 1.0)
    fall = np.ones_like(x) if d == c else np.clip((d - x) / (d - c), 0.0, 1.0)
    mu = np.minimum(rise, fall)
    mu[(x < a) | (x > d)] = 0.0
    return mu


def fuzzify(x: np.ndarray, terms: dict[str, tuple[float, float, float, float]],
            names: tuple[str, ...]) -> np.ndarray:
    """Membership degrees, shape (N, n_terms)."""
    return np.stack([trapmf(x, terms[n]) for n in names], axis=-1)


@dataclass
class Explanation:
    """Every intermediate quantity of one inference, for inspection and teaching."""

    inputs: dict[str, float]
    memberships: dict[str, dict[str, float]]
    fired_rules: list[tuple[str, float]]  # (rule text, firing strength), strongest first
    term_activation: dict[str, float]  # aggregated activation per output term
    universe: np.ndarray
    aggregated: np.ndarray  # aggregated output membership over the universe
    green: float


class FuzzyGreenController:
    """Mamdani FIS mapping (queue, own intensity, competing intensity) -> green time."""

    def __init__(self, params: FuzzyParams = FuzzyParams()) -> None:
        self.p = params
        missing = [
            n for names, terms in (
                (QUEUE_TERMS, params.queue_terms),
                (INTENSITY_TERMS, params.intensity_terms),
                (GREEN_TERMS, params.green_terms),
            ) for n in names if n not in terms
        ]
        if missing:
            raise ValueError(f"missing membership functions: {missing}")
        self.universe = np.linspace(*params.green_universe, params.resolution)
        self.out_mf = fuzzify(self.universe, params.green_terms, GREEN_TERMS)  # (U, 5)

    def _clip_inputs(self, q, a, c) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        q = np.clip(np.atleast_1d(np.asarray(q, dtype=float)), *self.p.queue_universe)
        a = np.clip(np.atleast_1d(np.asarray(a, dtype=float)), *self.p.intensity_universe)
        c = np.clip(np.atleast_1d(np.asarray(c, dtype=float)), *self.p.intensity_universe)
        if np.isnan(q).any() or np.isnan(a).any() or np.isnan(c).any():
            raise ValueError("fuzzy inputs must not be NaN")
        return np.broadcast_arrays(q, a, c)

    def _infer(self, q, a, c):
        q, a, c = self._clip_inputs(q, a, c)
        mu_q = fuzzify(q, self.p.queue_terms, QUEUE_TERMS)  # (N, 3)
        mu_a = fuzzify(a, self.p.intensity_terms, INTENSITY_TERMS)
        mu_c = fuzzify(c, self.p.intensity_terms, INTENSITY_TERMS)
        # firing strength of rule (c, q, a) = min of antecedent memberships -> (N, 3, 3, 3)
        firing = np.minimum(
            np.minimum(mu_c[:, :, None, None], mu_q[:, None, :, None]), mu_a[:, None, None, :]
        )
        flat_rules = RULES.reshape(-1)
        flat_firing = firing.reshape(len(q), -1)
        activation = np.zeros((len(q), len(GREEN_TERMS)))
        for k in range(len(GREEN_TERMS)):
            mask = flat_rules == k
            if mask.any():
                activation[:, k] = flat_firing[:, mask].max(axis=1)
        clipped = np.minimum(activation[:, None, :], self.out_mf[None, :, :])  # (N, U, 5)
        aggregated = clipped.max(axis=2)  # (N, U)
        area = aggregated.sum(axis=1)
        centroid = np.where(
            area > 0,
            (aggregated * self.universe).sum(axis=1) / np.where(area > 0, area, 1.0),
            self.p.green_universe[0],  # nothing fired (cannot happen with full coverage)
        )
        return centroid, (q, a, c, mu_q, mu_a, mu_c, firing, activation, aggregated)

    def infer(self, queue, intensity, competing) -> np.ndarray:
        """Green time (s) for each input triple; accepts scalars or arrays."""
        return self._infer(queue, intensity, competing)[0]

    def explain(self, queue: float, intensity: float, competing: float) -> Explanation:
        centroid, (q, a, c, mu_q, mu_a, mu_c, firing, activation, aggregated) = self._infer(
            queue, intensity, competing
        )
        fired = []
        for ci, cn in enumerate(INTENSITY_TERMS):
            for qi, qn in enumerate(QUEUE_TERMS):
                for ai, an in enumerate(INTENSITY_TERMS):
                    w = float(firing[0, ci, qi, ai])
                    if w > 0:
                        text = (f"IF queue is {qn} AND intensity is {an} AND competing is {cn} "
                                f"THEN green is {GREEN_TERMS[RULES[ci, qi, ai]]}")
                        fired.append((text, w))
        fired.sort(key=lambda r: -r[1])
        return Explanation(
            inputs={"queue": float(q[0]), "intensity": float(a[0]), "competing": float(c[0])},
            memberships={
                "queue": dict(zip(QUEUE_TERMS, mu_q[0].round(3).tolist())),
                "intensity": dict(zip(INTENSITY_TERMS, mu_a[0].round(3).tolist())),
                "competing": dict(zip(INTENSITY_TERMS, mu_c[0].round(3).tolist())),
            },
            fired_rules=fired,
            term_activation=dict(zip(GREEN_TERMS, activation[0].round(3).tolist())),
            universe=self.universe,
            aggregated=aggregated[0],
            green=float(centroid[0]),
        )
