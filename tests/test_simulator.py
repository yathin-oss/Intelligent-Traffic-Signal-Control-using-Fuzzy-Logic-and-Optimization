import numpy as np
import pytest

from traffic_signal.config import SCENARIOS, Config, NoiseParams
from traffic_signal.controllers import CONTROLLER_NAMES, FixedTimeController, build_controller
from traffic_signal.demand import arrival_rates, generate_arrivals, make_streams
from traffic_signal.metrics import compute_metrics
from traffic_signal.simulator import GREEN, Simulator
from traffic_signal.webster import webster_delay, webster_plan

CFG = Config()


def run(name, scenario="balanced", seed=100, noise=NoiseParams()):
    sc = SCENARIOS[scenario]
    arr_rng, noise_rng = make_streams(seed)
    arrivals = generate_arrivals(arrival_rates(sc, CFG.sim.duration), arr_rng)
    return arrivals, Simulator(CFG).run(build_controller(name, CFG, sc), arrivals, noise_rng, noise)


@pytest.mark.parametrize("name", CONTROLLER_NAMES)
def test_vehicle_conservation(name):
    arrivals, res = run(name, "heavy")
    assert len(res.veh_arrival) == arrivals.sum()
    departed = (res.veh_departure >= 0).sum()
    assert departed + res.queues[-1].sum() == arrivals.sum()
    assert (res.veh_departure[res.veh_departure >= 0] >= res.veh_arrival[res.veh_departure >= 0]).all()


@pytest.mark.parametrize("name", CONTROLLER_NAMES)
def test_timing_constraints_never_violated(name):
    _, res = run(name, "peak")
    greens = [d for (_, _, d) in res.greens]
    assert min(greens) >= CFG.timing.g_min
    assert max(greens) <= CFG.timing.g_max
    pairs = [a + b + 2 * CFG.timing.clearance for a, b in zip(greens, greens[1:])]
    assert max(pairs) <= CFG.timing.c_max
    phases = [p for (p, _, _) in res.greens]
    assert all(a != b for a, b in zip(phases, phases[1:]))  # strict alternation


def test_same_seed_is_deterministic_and_seeds_differ():
    _, a = run("fuzzy_opt", seed=7)
    _, b = run("fuzzy_opt", seed=7)
    _, c = run("fuzzy_opt", seed=8)
    assert np.array_equal(a.veh_departure, b.veh_departure)
    assert not np.array_equal(a.queues, c.queues)


def test_noise_does_not_change_arrivals():
    arr_clean, _ = run("actuated", seed=3)
    arr_noisy, _ = run("actuated", seed=3, noise=NoiseParams(4.0, 0.2))
    assert np.array_equal(arr_clean, arr_noisy)


def test_discharge_never_exceeds_saturation_flow():
    _, res = run("fixed", "heavy")
    deps = res.veh_departure[res.veh_departure >= 0]
    per_second = np.bincount(deps, minlength=len(res.state))
    # one lane per approach, two approaches served, s = 0.5 veh/s -> at most 1 veh/s/approach
    assert per_second.max() <= 2
    assert per_second[res.state != GREEN].sum() == 0


def test_webster_formula_consistency():
    """Simulated delay under a Webster fixed plan should be close to Webster's formula
    (stationary Poisson arrivals, undersaturated). A consistency check, not validation."""
    sc = SCENARIOS["balanced"]
    rate = sc.base[0] / 3600
    greens, cycle = webster_plan(np.array(sc.base) / 3600, CFG)
    eff_green = greens[0] - CFG.traffic.startup_lost
    theory = webster_delay(rate, cycle, eff_green, CFG.traffic.saturation_flow)
    sims = [compute_metrics(run("webster", "balanced", seed=s)[1], CFG)["mean_delay"]
            for s in range(10)]
    assert abs(np.mean(sims) - theory) / theory < 0.25, (np.mean(sims), theory)


def test_invalid_arrivals_rejected():
    with pytest.raises(ValueError):
        Simulator(CFG).run(FixedTimeController((20, 20)), np.zeros((10, 3), dtype=int),
                           np.random.default_rng(0))
