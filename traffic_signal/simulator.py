"""Discrete-time (1 s) simulator of an isolated four-way signalised intersection.

Model: one lane per approach, point (vertical) queues, Poisson arrivals, deterministic
saturation-flow discharge after a start-up lost time, and a two-phase signal
(NS, EW) cycling GREEN -> YELLOW -> ALL_RED. Constraints (min/max green and the
two-phase cycle cap) are enforced here, not trusted to controllers, like the
conflict monitor in a real signal cabinet.

Controllers never see simulator internals or future arrivals, only `Observation`s
produced by the `Detector` (which can add sensor noise).
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from .config import N_APPROACHES, N_PHASES, PHASES, Config, NoiseParams

if TYPE_CHECKING:
    from .controllers import Controller

GREEN, YELLOW, ALL_RED = 0, 1, 2


@dataclass(frozen=True)
class Observation:
    """What a controller can see at one second."""

    time: int
    phase: int  # phase currently green (or about to be green at a phase start)
    green_elapsed: int  # seconds of green completed in the current phase
    queues: np.ndarray  # observed queue per approach (veh), possibly noisy
    rates: np.ndarray  # estimated arrival rate per approach (veh/s), EWMA of detections
    time_since_arrival: np.ndarray  # s since last detected arrival per approach
    g_min: int
    g_max_now: int  # max green allowed for the current phase (g_max and cycle cap)
    prev_green: np.ndarray  # last completed green duration per phase (s)


class Detector:
    """Sensor layer: queue counts and arrival detections, with optional noise."""

    def __init__(self, cfg: Config, noise: NoiseParams, rng: np.random.Generator) -> None:
        self.noise = noise
        self.rng = rng
        self.alpha = 1.0 - math.exp(-1.0 / cfg.sim.ewma_tau)
        self.rates = np.zeros(N_APPROACHES)
        self.last_arrival = np.full(N_APPROACHES, -1e9)

    def update(self, t: int, arrivals: np.ndarray) -> None:
        detected = arrivals
        if self.noise.miss_rate > 0:
            detected = self.rng.binomial(arrivals, 1.0 - self.noise.miss_rate)
        self.rates += self.alpha * (detected - self.rates)
        self.last_arrival[detected > 0] = t

    def observe_queues(self, true_queues: np.ndarray) -> np.ndarray:
        if self.noise.queue_sigma == 0:
            return true_queues.astype(float)
        noisy = true_queues + self.rng.normal(0.0, self.noise.queue_sigma, N_APPROACHES)
        return np.maximum(0.0, np.round(noisy))


@dataclass
class SimResult:
    """Raw per-vehicle and per-second records of one run."""

    veh_arrival: np.ndarray  # arrival second
    veh_departure: np.ndarray  # departure second, -1 if still queued at the end
    veh_approach: np.ndarray
    veh_stopped: np.ndarray  # bool
    queues: np.ndarray  # (T, 4) true queue at end of each second
    est_rates: np.ndarray  # (T, 4) detector arrival-rate estimate (veh/s)
    phase: np.ndarray  # (T,) phase index
    state: np.ndarray  # (T,) GREEN / YELLOW / ALL_RED
    greens: list[tuple[int, int, int]]  # (phase, start second, green duration)


class Simulator:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg

    def _g_max_now(self, phase: int, prev_green: np.ndarray) -> int:
        tm = self.cfg.timing
        other = 1 - phase
        cap = tm.c_max - N_PHASES * tm.clearance - int(prev_green[other])
        return max(tm.g_min, min(tm.g_max, cap))

    def run(
        self,
        controller: Controller,
        arrivals: np.ndarray,
        noise_rng: np.random.Generator,
        noise: NoiseParams = NoiseParams(),
    ) -> SimResult:
        """Simulate `arrivals` (shape (T, 4) counts per second) under `controller`."""
        cfg, tm = self.cfg, self.cfg.timing
        sat, startup = cfg.traffic.saturation_flow, cfg.traffic.startup_lost
        T = arrivals.shape[0]
        if arrivals.ndim != 2 or arrivals.shape[1] != N_APPROACHES or T == 0:
            raise ValueError("arrivals must have shape (T, n_approaches) with T > 0")

        n_veh = int(arrivals.sum())
        veh_arrival = np.empty(n_veh, dtype=np.int64)
        veh_departure = np.full(n_veh, -1, dtype=np.int64)
        veh_approach = np.empty(n_veh, dtype=np.int64)
        veh_stopped = np.zeros(n_veh, dtype=bool)
        queues_ts = np.zeros((T, N_APPROACHES), dtype=np.int32)
        rates_ts = np.zeros((T, N_APPROACHES))
        phase_ts = np.zeros(T, dtype=np.int8)
        state_ts = np.zeros(T, dtype=np.int8)
        greens: list[tuple[int, int, int]] = []

        detector = Detector(cfg, noise, noise_rng)
        queues: list[deque[int]] = [deque() for _ in range(N_APPROACHES)]
        credit = np.zeros(N_APPROACHES)
        prev_green = np.full(N_PHASES, tm.g_min, dtype=np.int64)

        phase, state, elapsed, green_start = 0, GREEN, 0, 0
        g_max_now = self._g_max_now(phase, prev_green)
        next_id = 0

        def observe(t: int) -> Observation:
            true_q = np.array([len(q) for q in queues])
            return Observation(
                time=t,
                phase=phase,
                green_elapsed=elapsed if state == GREEN else 0,
                queues=detector.observe_queues(true_q),
                rates=detector.rates.copy(),
                time_since_arrival=t - detector.last_arrival,
                g_min=tm.g_min,
                g_max_now=g_max_now,
                prev_green=prev_green.copy(),
            )

        controller.reset()
        controller.on_phase_start(observe(0))

        for t in range(T):
            served = PHASES[phase] if state == GREEN else ()
            # 1. arrivals join the back of the queue
            for i in range(N_APPROACHES):
                for _ in range(arrivals[t, i]):
                    free_flow = i in served and elapsed >= startup and not queues[i]
                    veh_arrival[next_id] = t
                    veh_approach[next_id] = i
                    veh_stopped[next_id] = not free_flow
                    queues[i].append(next_id)
                    next_id += 1
            # 2. discharge at saturation flow after the start-up lost time
            if state == GREEN and elapsed >= startup:
                for i in served:
                    credit[i] += sat
                    while credit[i] >= 1.0 and queues[i]:
                        veh_departure[queues[i].popleft()] = t
                        credit[i] -= 1.0
                    if not queues[i]:
                        credit[i] = min(credit[i], 1.0)  # unused capacity cannot be banked
            elapsed += 1
            detector.update(t, arrivals[t])

            queues_ts[t] = [len(q) for q in queues]
            rates_ts[t] = detector.rates
            phase_ts[t] = phase
            state_ts[t] = state

            # 3. signal state machine
            if state == GREEN:
                end = elapsed >= g_max_now or (
                    elapsed >= tm.g_min and controller.should_end_green(observe(t))
                )
                if end:
                    greens.append((phase, green_start, elapsed))
                    prev_green[phase] = elapsed
                    state, elapsed = YELLOW, 0
            elif state == YELLOW and elapsed >= tm.yellow:
                state, elapsed = ALL_RED, 0
            elif state == ALL_RED and elapsed >= tm.all_red:
                phase = (phase + 1) % N_PHASES
                state, elapsed, green_start = GREEN, 0, t + 1
                g_max_now = self._g_max_now(phase, prev_green)
                credit[:] = 0.0
                controller.on_phase_start(observe(t))

        return SimResult(
            veh_arrival, veh_departure, veh_approach, veh_stopped,
            queues_ts, rates_ts, phase_ts, state_ts, greens,
        )
