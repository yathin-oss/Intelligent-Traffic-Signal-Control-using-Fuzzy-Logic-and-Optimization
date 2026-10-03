import numpy as np

from traffic_signal.config import Config
from traffic_signal.optimizer import GreenTimeOptimizer

CFG = Config()
OPT = GreenTimeOptimizer(CFG)
RATES = np.array([0.15, 0.15, 0.12, 0.12])


def test_returns_argmin_within_bounds():
    r = OPT.optimize(0, np.array([8, 6, 5, 4]), RATES, 10, 55)
    assert 10 <= r.green <= 55
    assert r.objective[r.candidates == r.green][0] == r.objective.min()
    assert r.candidates.min() == 10 and r.candidates.max() == 55


def test_longer_own_queue_gets_no_less_green():
    greens = [OPT.optimize(0, np.array([q, q, 3, 3]), RATES, 10, 60).green for q in (2, 10, 20, 30)]
    assert all(b >= a for a, b in zip(greens, greens[1:])), greens


def test_busier_competition_gets_no_more_green():
    greens = [OPT.optimize(0, np.array([10, 10, q, q]), RATES, 10, 60).green for q in (0, 10, 25)]
    assert all(b <= a for a, b in zip(greens, greens[1:])), greens


def test_strong_prior_pulls_to_fuzzy_proposal():
    r = OPT.optimize(0, np.array([10, 10, 5, 5]), RATES, 10, 60, g_prior=42.0, w_fuzzy=1e6)
    assert r.green == 42


def test_empty_intersection_prefers_short_green():
    r = OPT.optimize(0, np.zeros(4), np.zeros(4), 10, 60)
    assert r.green == 10


def test_never_returns_invalid_timing_on_random_states():
    """500 random traffic states, random bounds and priors: g* is always a feasible integer
    and equals the brute-force minimiser of J."""
    rng = np.random.default_rng(0)
    for _ in range(500):
        g_min = 10
        g_max_now = int(rng.integers(g_min, 61))
        queues = rng.integers(0, 45, size=4).astype(float)
        rates = rng.uniform(0.0, 0.3, size=4)
        prior = float(rng.uniform(10, 60)) if rng.random() < 0.7 else None
        r = OPT.optimize(int(rng.integers(0, 2)), queues, rates, g_min, g_max_now, prior,
                         w_fuzzy=float(rng.choice([0.0, 0.25, 1.0, 4.0])))
        assert isinstance(r.green, int)
        assert g_min <= r.green <= g_max_now
        assert r.objective[r.candidates == r.green][0] == r.objective.min()
        assert np.all(np.isfinite(r.objective))
