# Results tables (generated from results/*.csv)

Mean ± 95% CI over paired seeds. Delay in seconds, queue in vehicles.

## Low

| Controller | Mean delay | P95 delay | Worst-approach delay | Mean queue | Max queue | Stops/veh | Throughput (veh/h) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Fixed (equal split) | 18.1 ± 0.2 | 49.6 ± 0.3 | 19.7 ± 0.3 | 1.01 ± 0.02 | 8.5 ± 0.4 | 0.66 ± 0.01 | 807 ± 12 |
| Fixed (Webster) | 11.1 ± 0.1 | 24.3 ± 0.2 | 11.9 ± 0.2 | 0.62 ± 0.01 | 6.1 ± 0.3 | 0.80 ± 0.01 | 806 ± 12 |
| Actuated | 10.5 ± 0.1 | 22.9 ± 0.1 | 11.2 ± 0.2 | 0.59 ± 0.01 | 6.1 ± 0.3 | 0.82 ± 0.01 | 807 ± 12 |
| Fuzzy only | 12.1 ± 0.2 | 29.3 ± 0.2 | 12.9 ± 0.2 | 0.68 ± 0.02 | 6.6 ± 0.3 | 0.75 ± 0.01 | 807 ± 12 |
| Optimisation only | 12.1 ± 0.2 | 28.5 ± 0.3 | 12.9 ± 0.3 | 0.68 ± 0.02 | 6.6 ± 0.3 | 0.75 ± 0.01 | 807 ± 12 |
| Fuzzy + Opt | 12.1 ± 0.2 | 28.4 ± 0.2 | 13.0 ± 0.2 | 0.68 ± 0.02 | 6.4 ± 0.3 | 0.76 ± 0.01 | 808 ± 12 |

## Balanced

| Controller | Mean delay | P95 delay | Worst-approach delay | Mean queue | Max queue | Stops/veh | Throughput (veh/h) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Fixed (equal split) | 21.8 ± 0.2 | 50.6 ± 0.2 | 22.9 ± 0.4 | 2.74 ± 0.05 | 14.6 ± 0.5 | 0.79 ± 0.00 | 1810 ± 17 |
| Fixed (Webster) | 18.7 ± 0.4 | 41.0 ± 1.6 | 20.6 ± 0.7 | 2.35 ± 0.07 | 13.4 ± 0.8 | 0.87 ± 0.01 | 1815 ± 17 |
| Actuated | 14.6 ± 0.2 | 31.6 ± 0.5 | 15.4 ± 0.2 | 1.84 ± 0.04 | 11.2 ± 0.5 | 0.91 ± 0.00 | 1812 ± 17 |
| Fuzzy only | 17.6 ± 0.2 | 38.6 ± 0.4 | 18.6 ± 0.3 | 2.21 ± 0.04 | 12.7 ± 0.5 | 0.85 ± 0.00 | 1811 ± 17 |
| Optimisation only | 17.9 ± 0.2 | 39.5 ± 0.4 | 18.8 ± 0.3 | 2.25 ± 0.05 | 13.2 ± 0.6 | 0.86 ± 0.00 | 1811 ± 17 |
| Fuzzy + Opt | 17.4 ± 0.2 | 38.2 ± 0.5 | 18.4 ± 0.3 | 2.19 ± 0.05 | 12.4 ± 0.6 | 0.86 ± 0.00 | 1810 ± 17 |

## Heavy

| Controller | Mean delay | P95 delay | Worst-approach delay | Mean queue | Max queue | Stops/veh | Throughput (veh/h) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Fixed (equal split) | 33.5 ± 1.3 | 74.9 ± 5.7 | 41.2 ± 4.0 | 6.08 ± 0.27 | 26.9 ± 1.8 | 0.92 ± 0.00 | 2611 ± 21 |
| Fixed (Webster) | 33.5 ± 1.1 | 74.4 ± 5.3 | 40.8 ± 3.6 | 6.08 ± 0.24 | 26.7 ± 1.7 | 0.92 ± 0.01 | 2607 ± 21 |
| Actuated | 26.5 ± 0.8 | 59.7 ± 1.8 | 28.4 ± 1.0 | 4.81 ± 0.18 | 21.6 ± 1.0 | 0.93 ± 0.00 | 2611 ± 22 |
| Fuzzy only | 34.6 ± 1.4 | 69.6 ± 2.6 | 38.8 ± 2.0 | 6.29 ± 0.30 | 24.3 ± 1.2 | 0.95 ± 0.00 | 2612 ± 21 |
| Optimisation only | 31.7 ± 1.1 | 67.1 ± 2.4 | 34.2 ± 1.7 | 5.76 ± 0.23 | 23.7 ± 1.3 | 0.92 ± 0.00 | 2613 ± 21 |
| Fuzzy + Opt | 31.1 ± 0.9 | 63.9 ± 2.1 | 34.6 ± 1.5 | 5.65 ± 0.21 | 23.0 ± 1.1 | 0.93 ± 0.00 | 2613 ± 22 |

## Imbalanced

| Controller | Mean delay | P95 delay | Worst-approach delay | Mean queue | Max queue | Stops/veh | Throughput (veh/h) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Fixed (equal split) | 39.9 ± 3.8 | 96.0 ± 12.6 | 53.8 ± 7.1 | 5.02 ± 0.51 | 30.4 ± 3.0 | 0.89 ± 0.01 | 1807 ± 20 |
| Fixed (Webster) | 15.5 ± 0.6 | 49.5 ± 3.7 | 38.7 ± 3.2 | 1.94 ± 0.09 | 11.7 ± 0.8 | 0.79 ± 0.01 | 1803 ± 20 |
| Actuated | 13.3 ± 0.2 | 29.2 ± 0.6 | 18.4 ± 0.5 | 1.68 ± 0.03 | 11.7 ± 0.5 | 0.89 ± 0.00 | 1809 ± 20 |
| Fuzzy only | 15.2 ± 0.2 | 37.1 ± 0.5 | 22.3 ± 0.5 | 1.90 ± 0.04 | 13.5 ± 0.7 | 0.82 ± 0.01 | 1807 ± 20 |
| Optimisation only | 14.8 ± 0.3 | 41.0 ± 1.1 | 28.1 ± 0.7 | 1.85 ± 0.05 | 12.7 ± 0.6 | 0.78 ± 0.01 | 1808 ± 20 |
| Fuzzy + Opt | 14.7 ± 0.2 | 36.4 ± 0.5 | 23.7 ± 0.5 | 1.84 ± 0.05 | 12.7 ± 0.5 | 0.82 ± 0.01 | 1808 ± 20 |

## Peak

| Controller | Mean delay | P95 delay | Worst-approach delay | Mean queue | Max queue | Stops/veh | Throughput (veh/h) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Fixed (equal split) | 26.3 ± 1.2 | 66.1 ± 6.7 | 34.2 ± 3.3 | 2.99 ± 0.16 | 23.4 ± 2.3 | 0.80 ± 0.01 | 1639 ± 18 |
| Fixed (Webster) | 36.6 ± 3.5 | 124.6 ± 17.1 | 57.0 ± 7.8 | 4.19 ± 0.44 | 32.3 ± 3.8 | 0.89 ± 0.00 | 1638 ± 18 |
| Actuated | 15.8 ± 0.3 | 38.3 ± 1.5 | 17.2 ± 0.4 | 1.80 ± 0.06 | 15.4 ± 0.9 | 0.90 ± 0.00 | 1639 ± 19 |
| Fuzzy only | 19.6 ± 0.6 | 46.2 ± 2.3 | 22.5 ± 1.1 | 2.23 ± 0.09 | 17.0 ± 1.1 | 0.85 ± 0.00 | 1639 ± 19 |
| Optimisation only | 19.1 ± 0.4 | 47.1 ± 1.3 | 22.2 ± 0.5 | 2.17 ± 0.06 | 16.9 ± 0.9 | 0.85 ± 0.00 | 1639 ± 18 |
| Fuzzy + Opt | 18.6 ± 0.4 | 44.1 ± 1.5 | 20.8 ± 0.8 | 2.12 ± 0.06 | 16.0 ± 1.1 | 0.85 ± 0.00 | 1639 ± 18 |

## Mean-delay change vs baselines (paired)

Positive = lower delay than the baseline. CI is for the paired difference (controller − baseline, seconds).

| Scenario | Controller | Baseline | Baseline (s) | Controller (s) | Δ (s) [95% CI] | Improvement | Seeds better |
|---|---|---|---:|---:|---:|---:|---:|
| low | Fixed (equal split) | Fixed (Webster) | 11.1 | 18.1 | +7.0 [+6.7, +7.2] | -62.5% | 0% |
| low | Actuated | Fixed (Webster) | 11.1 | 10.5 | -0.6 [-0.8, -0.5] | +5.6% | 90% |
| low | Fuzzy only | Fixed (Webster) | 11.1 | 12.1 | +0.9 [+0.7, +1.1] | -8.5% | 0% |
| low | Optimisation only | Fixed (Webster) | 11.1 | 12.1 | +1.0 [+0.8, +1.2] | -9.0% | 7% |
| low | Fuzzy + Opt | Fixed (Webster) | 11.1 | 12.1 | +1.0 [+0.8, +1.1] | -8.6% | 3% |
| balanced | Fixed (equal split) | Fixed (Webster) | 18.7 | 21.8 | +3.1 [+2.7, +3.4] | -16.4% | 0% |
| balanced | Actuated | Fixed (Webster) | 18.7 | 14.6 | -4.1 [-4.4, -3.8] | +21.8% | 100% |
| balanced | Fuzzy only | Fixed (Webster) | 18.7 | 17.6 | -1.1 [-1.5, -0.8] | +6.1% | 90% |
| balanced | Optimisation only | Fixed (Webster) | 18.7 | 17.9 | -0.8 [-1.2, -0.4] | +4.3% | 80% |
| balanced | Fuzzy + Opt | Fixed (Webster) | 18.7 | 17.4 | -1.3 [-1.6, -1.0] | +7.0% | 90% |
| heavy | Fixed (equal split) | Fixed (Webster) | 33.5 | 33.5 | -0.0 [-0.5, +0.4] | +0.1% (n.s.) | 53% |
| heavy | Actuated | Fixed (Webster) | 33.5 | 26.5 | -7.0 [-8.0, -6.1] | +21.0% | 100% |
| heavy | Fuzzy only | Fixed (Webster) | 33.5 | 34.6 | +1.1 [+0.1, +2.1] | -3.3% | 37% |
| heavy | Optimisation only | Fixed (Webster) | 33.5 | 31.7 | -1.8 [-2.8, -0.8] | +5.3% | 83% |
| heavy | Fuzzy + Opt | Fixed (Webster) | 33.5 | 31.1 | -2.4 [-3.3, -1.5] | +7.2% | 93% |
| imbalanced | Fixed (equal split) | Fixed (Webster) | 15.5 | 39.9 | +24.4 [+20.6, +28.2] | -157.7% | 0% |
| imbalanced | Actuated | Fixed (Webster) | 15.5 | 13.3 | -2.2 [-2.7, -1.6] | +13.9% | 100% |
| imbalanced | Fuzzy only | Fixed (Webster) | 15.5 | 15.2 | -0.3 [-0.8, +0.2] | +2.1% (n.s.) | 50% |
| imbalanced | Optimisation only | Fixed (Webster) | 15.5 | 14.8 | -0.7 [-1.2, -0.3] | +4.7% | 70% |
| imbalanced | Fuzzy + Opt | Fixed (Webster) | 15.5 | 14.7 | -0.8 [-1.3, -0.4] | +5.3% | 73% |
| peak | Fixed (equal split) | Fixed (Webster) | 36.6 | 26.3 | -10.4 [-12.9, -7.8] | +28.3% | 100% |
| peak | Actuated | Fixed (Webster) | 36.6 | 15.8 | -20.8 [-24.1, -17.5] | +56.9% | 100% |
| peak | Fuzzy only | Fixed (Webster) | 36.6 | 19.6 | -17.1 [-20.1, -14.0] | +46.6% | 100% |
| peak | Optimisation only | Fixed (Webster) | 36.6 | 19.1 | -17.5 [-20.9, -14.2] | +47.9% | 100% |
| peak | Fuzzy + Opt | Fixed (Webster) | 36.6 | 18.6 | -18.0 [-21.3, -14.7] | +49.2% | 100% |
| low | Fixed (Webster) | Fixed (equal split) | 18.1 | 11.1 | -7.0 [-7.2, -6.7] | +38.5% | 100% |
| low | Actuated | Fixed (equal split) | 18.1 | 10.5 | -7.6 [-7.8, -7.3] | +41.9% | 100% |
| low | Fuzzy only | Fixed (equal split) | 18.1 | 12.1 | -6.0 [-6.3, -5.7] | +33.3% | 100% |
| low | Optimisation only | Fixed (equal split) | 18.1 | 12.1 | -5.9 [-6.2, -5.7] | +32.9% | 100% |
| low | Fuzzy + Opt | Fixed (equal split) | 18.1 | 12.1 | -6.0 [-6.2, -5.8] | +33.2% | 100% |
| balanced | Fixed (Webster) | Fixed (equal split) | 21.8 | 18.7 | -3.1 [-3.4, -2.7] | +14.1% | 100% |
| balanced | Actuated | Fixed (equal split) | 21.8 | 14.6 | -7.1 [-7.3, -7.0] | +32.8% | 100% |
| balanced | Fuzzy only | Fixed (equal split) | 21.8 | 17.6 | -4.2 [-4.4, -4.0] | +19.3% | 100% |
| balanced | Optimisation only | Fixed (equal split) | 21.8 | 17.9 | -3.9 [-4.1, -3.6] | +17.8% | 100% |
| balanced | Fuzzy + Opt | Fixed (equal split) | 21.8 | 17.4 | -4.4 [-4.6, -4.2] | +20.1% | 100% |
| heavy | Fixed (Webster) | Fixed (equal split) | 33.5 | 33.5 | +0.0 [-0.4, +0.5] | -0.1% (n.s.) | 47% |
| heavy | Actuated | Fixed (equal split) | 33.5 | 26.5 | -7.0 [-8.0, -5.9] | +20.9% | 100% |
| heavy | Fuzzy only | Fixed (equal split) | 33.5 | 34.6 | +1.2 [+0.1, +2.2] | -3.4% | 27% |
| heavy | Optimisation only | Fixed (equal split) | 33.5 | 31.7 | -1.7 [-2.8, -0.7] | +5.2% | 80% |
| heavy | Fuzzy + Opt | Fixed (equal split) | 33.5 | 31.1 | -2.4 [-3.3, -1.4] | +7.0% | 97% |
| imbalanced | Fixed (Webster) | Fixed (equal split) | 39.9 | 15.5 | -24.4 [-28.2, -20.6] | +61.2% | 100% |
| imbalanced | Actuated | Fixed (equal split) | 39.9 | 13.3 | -26.6 [-30.4, -22.8] | +66.6% | 100% |
| imbalanced | Fuzzy only | Fixed (equal split) | 39.9 | 15.2 | -24.7 [-28.6, -20.9] | +62.0% | 100% |
| imbalanced | Optimisation only | Fixed (equal split) | 39.9 | 14.8 | -25.2 [-28.9, -21.4] | +63.0% | 100% |
| imbalanced | Fuzzy + Opt | Fixed (equal split) | 39.9 | 14.7 | -25.2 [-29.1, -21.4] | +63.2% | 100% |
| peak | Fixed (Webster) | Fixed (equal split) | 26.3 | 36.6 | +10.4 [+7.8, +12.9] | -39.4% | 0% |
| peak | Actuated | Fixed (equal split) | 26.3 | 15.8 | -10.5 [-11.5, -9.4] | +39.9% | 100% |
| peak | Fuzzy only | Fixed (equal split) | 26.3 | 19.6 | -6.7 [-7.6, -5.8] | +25.5% | 100% |
| peak | Optimisation only | Fixed (equal split) | 26.3 | 19.1 | -7.2 [-8.3, -6.1] | +27.4% | 100% |
| peak | Fuzzy + Opt | Fixed (equal split) | 26.3 | 18.6 | -7.7 [-8.7, -6.6] | +29.2% | 100% |
| low | Fixed (equal split) | Actuated | 10.5 | 18.1 | +7.6 [+7.3, +7.8] | -72.2% | 0% |
| low | Fixed (Webster) | Actuated | 10.5 | 11.1 | +0.6 [+0.5, +0.8] | -6.0% | 10% |
| low | Fuzzy only | Actuated | 10.5 | 12.1 | +1.6 [+1.3, +1.8] | -14.9% | 0% |
| low | Optimisation only | Actuated | 10.5 | 12.1 | +1.6 [+1.4, +1.9] | -15.5% | 0% |
| low | Fuzzy + Opt | Actuated | 10.5 | 12.1 | +1.6 [+1.4, +1.8] | -15.1% | 0% |
| balanced | Fixed (equal split) | Actuated | 14.6 | 21.8 | +7.1 [+7.0, +7.3] | -48.9% | 0% |
| balanced | Fixed (Webster) | Actuated | 14.6 | 18.7 | +4.1 [+3.8, +4.4] | -27.9% | 0% |
| balanced | Fuzzy only | Actuated | 14.6 | 17.6 | +2.9 [+2.8, +3.1] | -20.1% | 0% |
| balanced | Optimisation only | Actuated | 14.6 | 17.9 | +3.3 [+3.1, +3.5] | -22.4% | 0% |
| balanced | Fuzzy + Opt | Actuated | 14.6 | 17.4 | +2.8 [+2.6, +3.0] | -19.0% | 0% |
| heavy | Fixed (equal split) | Actuated | 26.5 | 33.5 | +7.0 [+5.9, +8.0] | -26.4% | 0% |
| heavy | Fixed (Webster) | Actuated | 26.5 | 33.5 | +7.0 [+6.1, +8.0] | -26.6% | 0% |
| heavy | Fuzzy only | Actuated | 26.5 | 34.6 | +8.1 [+7.3, +9.0] | -30.8% | 0% |
| heavy | Optimisation only | Actuated | 26.5 | 31.7 | +5.3 [+4.6, +5.9] | -19.9% | 0% |
| heavy | Fuzzy + Opt | Actuated | 26.5 | 31.1 | +4.6 [+4.1, +5.2] | -17.5% | 0% |
| imbalanced | Fixed (equal split) | Actuated | 13.3 | 39.9 | +26.6 [+22.8, +30.4] | -199.3% | 0% |
| imbalanced | Fixed (Webster) | Actuated | 13.3 | 15.5 | +2.2 [+1.6, +2.7] | -16.1% | 0% |
| imbalanced | Fuzzy only | Actuated | 13.3 | 15.2 | +1.8 [+1.6, +2.0] | -13.7% | 0% |
| imbalanced | Optimisation only | Actuated | 13.3 | 14.8 | +1.4 [+1.2, +1.6] | -10.6% | 0% |
| imbalanced | Fuzzy + Opt | Actuated | 13.3 | 14.7 | +1.3 [+1.1, +1.5] | -10.0% | 0% |
| peak | Fixed (equal split) | Actuated | 15.8 | 26.3 | +10.5 [+9.4, +11.5] | -66.4% | 0% |
| peak | Fixed (Webster) | Actuated | 15.8 | 36.6 | +20.8 [+17.5, +24.1] | -132.1% | 0% |
| peak | Fuzzy only | Actuated | 15.8 | 19.6 | +3.8 [+3.4, +4.2] | -23.9% | 0% |
| peak | Optimisation only | Actuated | 15.8 | 19.1 | +3.3 [+3.0, +3.5] | -20.8% | 0% |
| peak | Fuzzy + Opt | Actuated | 15.8 | 18.6 | +2.8 [+2.5, +3.2] | -17.9% | 0% |

## Ablation: Fuzzy + Opt vs its components (mean delay, paired)

| Scenario | Compared with | Other (s) | Fuzzy + Opt (s) | Δ (s) [95% CI] | Improvement |
|---|---|---:|---:|---:|---:|
| low | Optimisation only | 12.1 | 12.1 | -0.05 [-0.30, +0.20] | +0.4% (n.s.) |
| balanced | Optimisation only | 17.9 | 17.4 | -0.50 [-0.71, -0.29] | +2.8% |
| heavy | Optimisation only | 31.7 | 31.1 | -0.63 [-0.98, -0.27] | +2.0% |
| imbalanced | Optimisation only | 14.8 | 14.7 | -0.08 [-0.29, +0.12] | +0.6% (n.s.) |
| peak | Optimisation only | 19.1 | 18.6 | -0.46 [-0.69, -0.24] | +2.4% |
| low | Fuzzy only | 12.1 | 12.1 | +0.02 [-0.22, +0.26] | -0.2% (n.s.) |
| balanced | Fuzzy only | 17.6 | 17.4 | -0.16 [-0.36, +0.03] | +0.9% (n.s.) |
| heavy | Fuzzy only | 34.6 | 31.1 | -3.50 [-4.15, -2.86] | +10.1% |
| imbalanced | Fuzzy only | 15.2 | 14.7 | -0.49 [-0.71, -0.28] | +3.3% |
| peak | Fuzzy only | 19.6 | 18.6 | -0.95 [-1.31, -0.60] | +4.9% |
