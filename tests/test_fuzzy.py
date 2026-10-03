import numpy as np
import pytest

from traffic_signal.config import FuzzyParams
from traffic_signal.fuzzy import RULES, FuzzyGreenController, trapmf

FIS = FuzzyGreenController()


def test_trapmf_shapes():
    x = np.array([0, 2.5, 5, 7.5, 10, 12])
    assert np.allclose(trapmf(x, (0, 5, 5, 10)), [0, 0.5, 1, 0.5, 0, 0])
    assert np.allclose(trapmf(np.array([0.0, 3, 5.5, 8]), (0, 0, 3, 8)), [1, 1, 0.5, 0])
    with pytest.raises(ValueError):
        trapmf(x, (5, 0, 5, 10))


def test_every_input_fires_some_rule():
    """Input MFs must cover their universes, so centroid is always defined."""
    p = FuzzyParams()
    for terms, (lo, hi) in ((p.queue_terms, p.queue_universe),
                            (p.intensity_terms, p.intensity_universe)):
        x = np.linspace(lo, hi, 2001)
        total = np.max([trapmf(x, t) for t in terms.values()], axis=0)
        assert total.min() > 0


def test_rule_table_monotone():
    # rises with queue (axis 1) and own intensity (axis 2), falls with competing (axis 0)
    assert (np.diff(RULES, axis=1) >= 0).all()
    assert (np.diff(RULES, axis=2) >= 0).all()
    assert (np.diff(RULES, axis=0) <= 0).all()


def test_output_near_monotone_on_grid():
    """A monotone rule table does not make max-min Mamdani + centroid strictly monotone:
    in overlap regions the centroid can dip slightly. We require no reversal larger than
    the 1 s resolution at which greens are applied (measured worst case ~0.6 s)."""
    tol = 1.0
    q = np.linspace(0, 40, 161)
    a = np.linspace(0, 1, 161)
    Q, A = np.meshgrid(q, a, indexing="ij")
    for c in (0.0, 0.05, 0.15, 0.25, 0.35, 0.5):
        G = FIS.infer(Q.ravel(), A.ravel(), c).reshape(Q.shape)
        assert np.diff(G, axis=0).min() > -tol
        assert np.diff(G, axis=1).min() > -tol
    for q0, a0 in ((15, 0.3), (5, 0.2), (30, 0.4)):
        assert np.diff(FIS.infer(q0, a0, np.linspace(0, 1, 201))).max() < tol
    # the global trend is strongly monotone
    assert FIS.infer(35, 0.5, 0.05)[0] - FIS.infer(2, 0.05, 0.05)[0] > 30


def test_hand_computed_single_rule_case():
    """queue=0 (SHORT=1), intensity=0 (LOW=1) fire only rules with output VERY_SHORT,
    whose centroid is that of trapezoid (10,10,12,20)."""
    g = FIS.infer(0.0, 0.0, 0.0)[0]
    x = FIS.universe
    mu = trapmf(x, (10, 10, 12, 20))
    assert g == pytest.approx((mu * x).sum() / mu.sum())


def test_extremes_and_bounds():
    assert FIS.infer(40, 1.0, 0.0)[0] > 50
    g = FIS.infer(np.array([0, 10, 25, 40]), 0.3, 0.3)
    assert (g >= 10).all() and (g <= 60).all()
    with pytest.raises(ValueError):
        FIS.infer(np.nan, 0.1, 0.1)


def test_explain_matches_infer():
    e = FIS.explain(14, 0.3, 0.2)
    assert e.green == pytest.approx(FIS.infer(14, 0.3, 0.2)[0])
    assert e.fired_rules and all(w > 0 for _, w in e.fired_rules)
