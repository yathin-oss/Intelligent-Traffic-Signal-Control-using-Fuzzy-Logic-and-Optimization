"""Central configuration: every tunable number in the project lives here.

The intersection is a four-way junction with approaches N, S, E, W (indices 0-3),
one lane per approach, and two signal phases served in fixed order:
phase 0 = North-South, phase 1 = East-West.
"""

from __future__ import annotations

from dataclasses import dataclass, field

APPROACHES: tuple[str, ...] = ("N", "S", "E", "W")
PHASES: tuple[tuple[int, int], ...] = ((0, 1), (2, 3))
PHASE_NAMES: tuple[str, ...] = ("NS", "EW")
N_APPROACHES = len(APPROACHES)
N_PHASES = len(PHASES)


@dataclass(frozen=True)
class SignalTiming:
    """Hard signal-timing constraints, enforced by the simulator for every controller."""

    g_min: int = 10  # minimum green (s) - pedestrian / driver-expectation proxy
    g_max: int = 60  # maximum green (s)
    yellow: int = 3  # yellow interval (s), no discharge
    all_red: int = 2  # all-red clearance (s)
    c_max: int = 120  # max duration of any two consecutive phases incl. clearance (s)

    def __post_init__(self) -> None:
        if not (0 < self.g_min <= self.g_max):
            raise ValueError("require 0 < g_min <= g_max")
        if self.yellow < 0 or self.all_red < 0:
            raise ValueError("clearance intervals must be non-negative")
        if self.c_max < 2 * (self.g_min + self.clearance):
            raise ValueError("c_max too small to fit two minimum greens")

    @property
    def clearance(self) -> int:
        return self.yellow + self.all_red


@dataclass(frozen=True)
class TrafficParams:
    """Physical parameters of vehicle discharge."""

    saturation_flow: float = 0.5  # veh/s/lane during green (= 1800 veh/h)
    startup_lost: int = 2  # s at the start of green with no discharge

    def __post_init__(self) -> None:
        if self.saturation_flow <= 0:
            raise ValueError("saturation_flow must be positive")
        if self.startup_lost < 0:
            raise ValueError("startup_lost must be non-negative")


@dataclass(frozen=True)
class SimulationParams:
    """Run protocol. Metrics use vehicles arriving inside the measurement window."""

    warmup: int = 600
    measure: int = 3600
    cooldown: int = 900  # arrivals continue; lets measured vehicles clear
    ewma_tau: float = 120.0  # time constant (s) of the detector's arrival-rate estimate

    def __post_init__(self) -> None:
        if min(self.warmup, self.measure, self.cooldown) < 0 or self.measure == 0:
            raise ValueError("invalid run protocol durations")
        if self.ewma_tau <= 0:
            raise ValueError("ewma_tau must be positive")

    @property
    def duration(self) -> int:
        return self.warmup + self.measure + self.cooldown

    @property
    def window(self) -> tuple[int, int]:
        return self.warmup, self.warmup + self.measure


@dataclass(frozen=True)
class NoiseParams:
    """Sensor imperfections applied in the observation layer (Experiment F)."""

    queue_sigma: float = 0.0  # std-dev of Gaussian error on observed queue (veh)
    miss_rate: float = 0.0  # probability an arrival is not detected

    def __post_init__(self) -> None:
        if self.queue_sigma < 0 or not (0.0 <= self.miss_rate < 1.0):
            raise ValueError("invalid noise parameters")


@dataclass(frozen=True)
class FuzzyParams:
    """Membership-function breakpoints. See docs/methodology.md for the physical anchors.

    Each term is a trapezoid (a, b, c, d); a triangle has b == c.
    """

    queue_universe: tuple[float, float] = (0.0, 40.0)
    queue_terms: dict[str, tuple[float, float, float, float]] = field(
        default_factory=lambda: {
            "SHORT": (0.0, 0.0, 3.0, 8.0),  # clears within g_min: (10-2) s * 0.5 veh/s = 4 veh
            "MEDIUM": (5.0, 12.0, 12.0, 20.0),
            "LONG": (15.0, 25.0, 40.0, 40.0),  # 25 veh needs 2 + 50 s = g_max-level green
        }
    )
    intensity_universe: tuple[float, float] = (0.0, 1.0)
    intensity_terms: dict[str, tuple[float, float, float, float]] = field(
        default_factory=lambda: {
            "LOW": (0.0, 0.0, 0.08, 0.18),
            "MEDIUM": (0.10, 0.25, 0.25, 0.40),  # two phases at y=0.25 -> Y=0.5, moderate load
            "HIGH": (0.32, 0.45, 1.0, 1.0),  # y=0.44 per phase ~ capacity limit 1 - L/C_max
        }
    )
    green_universe: tuple[float, float] = (10.0, 60.0)
    green_terms: dict[str, tuple[float, float, float, float]] = field(
        default_factory=lambda: {
            "VERY_SHORT": (10.0, 10.0, 12.0, 20.0),
            "SHORT": (12.0, 20.0, 20.0, 30.0),
            "MEDIUM": (22.0, 32.0, 32.0, 42.0),
            "LONG": (34.0, 44.0, 44.0, 54.0),
            "VERY_LONG": (46.0, 56.0, 60.0, 60.0),
        }
    )
    resolution: int = 501  # output-universe samples for centroid defuzzification


@dataclass(frozen=True)
class OptimizerParams:
    """Objective J(g) = delay + rho*terminal_backlog + w_queue*max_queue + w_fuzzy*(g-g_f)^2."""

    horizon: int = 120  # fixed prediction window (s), identical for every candidate
    rho: float = 30.0  # s of extra delay charged per vehicle still queued at horizon end
    w_queue: float = 20.0  # veh.s per vehicle of peak predicted queue (storage proxy)
    w_fuzzy: float = 1.0  # veh/s; weight of the fuzzy prior (0 => optimization-only)

    def __post_init__(self) -> None:
        if self.horizon <= 0 or min(self.rho, self.w_queue, self.w_fuzzy) < 0:
            raise ValueError("invalid optimizer parameters")


@dataclass(frozen=True)
class Scenario:
    """Demand per approach (veh/h). A Gaussian surge from `base` to `peak` is centred at
    `peak_time` (s from simulation start) with std-dev `peak_width`; peak == base means
    stationary Poisson demand."""

    name: str
    base: tuple[float, float, float, float]
    peak: tuple[float, float, float, float] | None = None
    peak_time: float = 2400.0
    peak_width: float = 600.0

    def __post_init__(self) -> None:
        if len(self.base) != N_APPROACHES or any(v < 0 for v in self.base):
            raise ValueError(f"{self.name}: base needs {N_APPROACHES} non-negative rates")
        if self.peak is not None and (
            len(self.peak) != N_APPROACHES or any(v < 0 for v in self.peak)
        ):
            raise ValueError(f"{self.name}: peak needs {N_APPROACHES} non-negative rates")
        if self.peak_width <= 0:
            raise ValueError(f"{self.name}: peak_width must be positive")


SCENARIOS: dict[str, Scenario] = {
    "low": Scenario("low", (200, 200, 200, 200)),
    "balanced": Scenario("balanced", (450, 450, 450, 450)),
    "heavy": Scenario("heavy", (650, 650, 650, 650)),
    "imbalanced": Scenario("imbalanced", (700, 700, 200, 200)),
    "peak": Scenario("peak", (250, 250, 250, 250), peak=(750, 750, 500, 500)),
}

# Used only for parameter tuning; never reported as an evaluation result.
TUNING_SCENARIO = Scenario(
    "tuning", (400, 350, 350, 300), peak=(650, 600, 450, 400), peak_time=2000.0, peak_width=900.0
)

EVAL_SEEDS: tuple[int, ...] = tuple(range(100, 130))
TUNING_SEEDS: tuple[int, ...] = tuple(range(0, 5))
ACTUATED_GAP_GRID: tuple[int, ...] = (2, 3, 4)
W_FUZZY_GRID: tuple[float, ...] = (0.25, 1.0, 4.0)
FIXED_CYCLE: int = 90  # cycle of the naive equal-split fixed-time baseline

NOISE_LEVELS: dict[str, NoiseParams] = {
    "none": NoiseParams(0.0, 0.0),
    "moderate": NoiseParams(2.0, 0.10),
    "severe": NoiseParams(4.0, 0.20),
}


@dataclass(frozen=True)
class Config:
    timing: SignalTiming = field(default_factory=SignalTiming)
    traffic: TrafficParams = field(default_factory=TrafficParams)
    sim: SimulationParams = field(default_factory=SimulationParams)
    fuzzy: FuzzyParams = field(default_factory=FuzzyParams)
    optimizer: OptimizerParams = field(default_factory=OptimizerParams)

    @property
    def lost_time_per_phase(self) -> int:
        """Start-up lost time + yellow + all-red (no discharge during yellow)."""
        return self.traffic.startup_lost + self.timing.clearance
