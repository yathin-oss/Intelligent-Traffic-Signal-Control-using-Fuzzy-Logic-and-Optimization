"""Time-varying traffic demand and seeded Poisson arrival streams."""

from __future__ import annotations

import numpy as np

from .config import N_APPROACHES, Scenario


def arrival_rates(scenario: Scenario, duration: int) -> np.ndarray:
    """Expected arrival rate (veh/s) for each second and approach, shape (duration, 4)."""
    t = np.arange(duration, dtype=float)[:, None]
    base = np.asarray(scenario.base, dtype=float)[None, :] / 3600.0
    if scenario.peak is None:
        return np.repeat(base, duration, axis=0)
    peak = np.asarray(scenario.peak, dtype=float)[None, :] / 3600.0
    bump = np.exp(-0.5 * ((t - scenario.peak_time) / scenario.peak_width) ** 2)
    return base + (peak - base) * bump


def mean_rates(scenario: Scenario, start: int, end: int) -> np.ndarray:
    """Average rate (veh/s) per approach over [start, end)."""
    return arrival_rates(scenario, end)[start:end].mean(axis=0)


def generate_arrivals(rates: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Poisson arrival counts per second and approach, shape like `rates`."""
    if rates.ndim != 2 or rates.shape[1] != N_APPROACHES:
        raise ValueError("rates must have shape (duration, n_approaches)")
    return rng.poisson(rates).astype(np.int64)


def make_streams(seed: int) -> tuple[np.random.Generator, np.random.Generator]:
    """Independent (arrivals, sensor-noise) generators for one seed.

    Separate streams mean enabling sensor noise never changes the arrival sequence, so
    every controller and noise level sees identical demand for a given seed.
    """
    arrivals_ss, noise_ss = np.random.SeedSequence(seed).spawn(2)
    return np.random.default_rng(arrivals_ss), np.random.default_rng(noise_ss)
