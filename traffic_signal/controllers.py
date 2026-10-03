"""Signal controllers. All share one interface and the same physical knowledge.

The simulator calls `on_phase_start` when a green begins and `should_end_green` every
second once the minimum green has elapsed; it enforces the maximum itself.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from .config import FIXED_CYCLE, N_PHASES, PHASES, Config, Scenario
from .demand import mean_rates
from .fuzzy import FuzzyGreenController
from .optimizer import GreenTimeOptimizer
from .simulator import Observation
from .webster import webster_plan


class Controller(ABC):
    name: str = "controller"

    def reset(self) -> None:
        """Clear per-run state."""

    def on_phase_start(self, obs: Observation) -> None:
        """Called when a new green begins."""

    @abstractmethod
    def should_end_green(self, obs: Observation) -> bool:
        """Return True to terminate the current green (called after g_min)."""


class PlannedGreenController(Controller):
    """Decides the whole green duration at phase start, then runs it out."""

    def __init__(self) -> None:
        self.decisions: list[dict] = []
        self._target = 0

    def reset(self) -> None:
        self.decisions = []

    @abstractmethod
    def plan_green(self, obs: Observation) -> tuple[float, dict]:
        """Desired green (s) plus diagnostic info for the decision log."""

    def on_phase_start(self, obs: Observation) -> None:
        green, info = self.plan_green(obs)
        self._target = int(np.clip(round(green), obs.g_min, obs.g_max_now))
        self.decisions.append({"time": obs.time, "phase": obs.phase, "green": self._target, **info})

    def should_end_green(self, obs: Observation) -> bool:
        return obs.green_elapsed >= self._target


class FixedTimeController(PlannedGreenController):
    def __init__(self, greens: np.ndarray | tuple[int, ...], name: str = "fixed") -> None:
        super().__init__()
        if len(greens) != N_PHASES:
            raise ValueError(f"need one green per phase ({N_PHASES})")
        self.greens = np.asarray(greens, dtype=float)
        self.name = name

    def plan_green(self, obs: Observation) -> tuple[float, dict]:
        return float(self.greens[obs.phase]), {}


def equal_split_controller(cfg: Config, cycle: int = FIXED_CYCLE) -> FixedTimeController:
    green = (cycle - N_PHASES * cfg.timing.clearance) // N_PHASES
    return FixedTimeController((green,) * N_PHASES, name="fixed")


def webster_controller(cfg: Config, scenario: Scenario) -> FixedTimeController:
    """Fixed-time plan from Webster's method using the scenario's true average demand in
    the measurement window. This oracle knowledge favours the baseline."""
    rates = mean_rates(scenario, *cfg.sim.window)
    greens, _ = webster_plan(rates, cfg)
    return FixedTimeController(greens, name="webster")


class ActuatedController(Controller):
    """Vehicle-actuated gap-out control: hold green while the served queue is non-empty or
    a vehicle was detected within `gap` seconds; otherwise end green."""

    def __init__(self, gap: float = 3.0) -> None:
        if gap <= 0:
            raise ValueError("gap must be positive")
        self.gap = gap
        self.name = "actuated"

    def should_end_green(self, obs: Observation) -> bool:
        served = list(PHASES[obs.phase])
        if (obs.queues[served] > 0).any():
            return False
        return bool(obs.time_since_arrival[served].min() >= self.gap)


def fuzzy_inputs(obs: Observation, sat: float) -> tuple[float, float, float]:
    """(critical queue, own intensity, competing intensity) for the phase being served."""
    own, other = list(PHASES[obs.phase]), list(PHASES[(obs.phase + 1) % N_PHASES])
    return (float(obs.queues[own].max()), float(obs.rates[own].max() / sat),
            float(obs.rates[other].max() / sat))


class FuzzyOnlyController(PlannedGreenController):
    name = "fuzzy_only"

    def __init__(self, cfg: Config) -> None:
        super().__init__()
        self.cfg = cfg
        self.fis = FuzzyGreenController(cfg.fuzzy)

    def plan_green(self, obs: Observation) -> tuple[float, dict]:
        q, a, c = fuzzy_inputs(obs, self.cfg.traffic.saturation_flow)
        g = float(self.fis.infer(q, a, c)[0])
        return g, {"queue": q, "intensity": a, "competing": c, "g_fuzzy": g}


class OptimizedController(PlannedGreenController):
    """Fuzzy proposal refined by the optimizer (w_fuzzy > 0), or pure optimisation
    (w_fuzzy == 0, fuzzy system not consulted)."""

    def __init__(self, cfg: Config, w_fuzzy: float) -> None:
        super().__init__()
        self.cfg = cfg
        self.w_fuzzy = w_fuzzy
        self.name = "fuzzy_opt" if w_fuzzy > 0 else "opt_only"
        self.fis = FuzzyGreenController(cfg.fuzzy) if w_fuzzy > 0 else None
        self.optimizer = GreenTimeOptimizer(cfg)

    def plan_green(self, obs: Observation) -> tuple[float, dict]:
        info: dict = {}
        g_prior = None
        if self.fis is not None:
            q, a, c = fuzzy_inputs(obs, self.cfg.traffic.saturation_flow)
            g_prior = float(self.fis.infer(q, a, c)[0])
            info.update(queue=q, intensity=a, competing=c, g_fuzzy=g_prior)
        res = self.optimizer.optimize(obs.phase, obs.queues, obs.rates, obs.g_min,
                                      obs.g_max_now, g_prior, self.w_fuzzy)
        info["g_opt"] = res.green
        return float(res.green), info


CONTROLLER_NAMES = ("fixed", "webster", "actuated", "fuzzy_only", "opt_only", "fuzzy_opt")


def build_controller(name: str, cfg: Config, scenario: Scenario,
                     tuned: dict[str, float] | None = None) -> Controller:
    tuned = tuned or {}
    if name == "fixed":
        return equal_split_controller(cfg)
    if name == "webster":
        return webster_controller(cfg, scenario)
    if name == "actuated":
        return ActuatedController(tuned.get("actuated_gap", 3.0))
    if name == "fuzzy_only":
        return FuzzyOnlyController(cfg)
    if name == "opt_only":
        return OptimizedController(cfg, w_fuzzy=0.0)
    if name == "fuzzy_opt":
        return OptimizedController(cfg, w_fuzzy=tuned.get("w_fuzzy", cfg.optimizer.w_fuzzy))
    raise ValueError(f"unknown controller {name!r}; choose from {CONTROLLER_NAMES}")
