# Performance report

Machine: MacBook Air (Mac15,13), Apple M3, 8 CPU cores, 16 GB memory. OS: macOS 26.6, arm64. Language: Python 3.13.1 (CPython). Measurements: 2026-09-23.

## Setup

I used `experiment.py` to generate temporary relation files, load them with the engine and run the queries. R has columns `(a,b)` and S has `(b,c)`. All R rows have `b=0`; in the main experiment exactly one S row has `b=0`. Unique `a` and `c` values keep the input rows distinct. Each R row therefore matches one S row. This is controlled, skewed data rather than random data.

The engine's `perf_counter()` timer covers query evaluation, including condition binding, tuple construction, counting and result collection. File generation, loading, input duplicate removal, query parsing and printing are outside that timer. The join uses nested loops and passes every product pair to selection, keeping only matches. It does not build an intermediate table of all pairs. This changes storage, not the query tree or the pairs examined. No index or hash join is used.

The join counter increases inside the selection loop once per product pair. The selection counter also increases for that pair, so these are two views of the same work and must not be added. `measurements.jsonl` contains the actual counts and unrounded times, saved immediately after each query. Assertions check counts and result sizes after timing; the expected formulas do not supply the measured counters.

## Join measurements

Query: `R join[R.b=S.b] S`. One timed run per size, in increasing order, with one match per R row.

| n | m | Comparisons | Wall time (s) | Output tuples |
| ---: | ---: | ---: | ---: | ---: |
| 1,000 | 1,000 | 1,000,000 | 0.304460 | 1,000 |
| 2,000 | 2,000 | 4,000,000 | 1.217272 | 2,000 |
| 4,000 | 4,000 | 16,000,000 | 4.899501 | 4,000 |
| 8,000 | 8,000 | 64,000,000 | 19.670189 | 8,000 |
| 16,000 | 16,000 | 256,000,000 | 80.549386 | 16,000 |
| 32,000 | 32,000 | 1,024,000,000 | 347.868669 | 32,000 |
| 64,000 | 64,000 | 4,096,000,000 | 1408.401873 | 64,000 |

### 1. Comparison count

The measured count is exactly `n * m` at every size. For each R row, the inner loop checks all m S rows, even after a match. At 64,000 rows per side, the actual counter is `64,000 * 64,000 = 4,096,000,000`. With n=m this is n². There is no discrepancy.

### 2. Time and slope

![Log-log plot of measured query times](performance.png)

I fitted a straight line to `log10(n)` and `log10(seconds)` using all seven sizes. The join slope is **2.032**. A slope near 2 means time grows roughly as n²: doubling both inputs gives roughly four times as many comparisons. The fitted slope describes these measurements, not an exact timing guarantee. Background work, CPU temperature and allocation costs can affect the times. The join has one run per size, so the plot does not provide confidence intervals.

### 3. Selection and projection

At each size I ran `select[a<n/2](R)`, replacing `n/2` with the actual integer, and `project[b](R)`. For example, at n=1,000 the selection is `select[a<500](R)`. I used the median of seven evaluation times because these queries finish quickly. Each run used the same already-loaded tables.

| n | Select seconds | Rows examined | Select output | Project seconds | Project output |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1,000 | 0.000306 | 1,000 | 500 | 0.000654 | 1 |
| 2,000 | 0.000592 | 2,000 | 1,000 | 0.001275 | 1 |
| 4,000 | 0.001188 | 4,000 | 2,000 | 0.002557 | 1 |
| 8,000 | 0.002392 | 8,000 | 4,000 | 0.005467 | 1 |
| 16,000 | 0.004695 | 16,000 | 8,000 | 0.013489 | 1 |
| 32,000 | 0.009283 | 32,000 | 16,000 | 0.020305 | 1 |
| 64,000 | 0.018236 | 64,000 | 32,000 | 0.041021 | 1 |

Selection has slope **0.986** and projection has slope **1.011**. Selection examines exactly n rows and returns half. Projection visits n rows but produces just one distinct `b` value, so each duplicate check has at most one saved row to compare with. Both are approximately linear for this dataset, while the join checks n² pairs. Projection's result does not mean it is always linear: with many distinct output rows, this implementation's linear duplicate searches can take quadratic time. Input duplicate removal also uses linear searches, so loading can be slow even though it is excluded from query timing.

### 4. Prediction for one million rows per side

Using the largest measured join and quadratic scaling:

```text
scale = (1,000,000 / 64,000)^2 = 244.140625
predicted time = 1408.401873 seconds * 244.140625
               = 343,848.11 seconds
               = 95.51 hours
comparisons = 1,000,000 * 1,000,000 = 1,000,000,000,000
```

This predicts evaluation time with the same implementation and one match per R row. It excludes loading and printing and assumes similar time per pair. I did **not** run the million-row join.

### 5. Changing the match rate

I held n=m=1,000 fixed, regenerated the inputs with different match counts and ran each setting three times. Times below are medians.

| S matches per R row | Comparisons per run | Wall time (s) | Output tuples |
| ---: | ---: | ---: | ---: |
| 0 | 1,000,000 | 0.316162 | 0 |
| 1 | 1,000,000 | 0.302644 | 1,000 |
| 1,000 | 1,000,000 | 0.482768 | 1,000,000 |

Every run still makes 1,000,000 comparisons because the nested loops visit every pair regardless of the result. Wall time can change: matching pairs must be retained and added to the result, while rejected pairs can be discarded. The all-match case stores one million rows; the zero-match case stores none. These allocation and storage costs explain why equal comparison counts need not give equal wall times. Small timing differences also include measurement noise.

### 6. Making a million-row join feasible

For this equality join, I would replace the all-pairs search with a hash join: group one input by its join key, then look up only matching groups for each row of the other input. With suitable keys, expected work would be near n+m plus the number of output rows, instead of n*m. I would also improve duplicate checking during loading and stream large results to avoid keeping everything in memory. If the data did not fit in memory, I would partition it. A high match rate can still create an enormous output, so no join algorithm removes that cost. These changes are proposals only; the measured engine keeps the required nested-loop algorithm.

## Reproducing the study

From this folder, run `python3 experiment.py --output new-measurements.jsonl` for a fresh experiment. It refuses to overwrite an existing results file and can take a long time. The generator's temporary input file is closed after loading. The saved report uses `measurements.jsonl`; `python3 plot_results.py` reads that file and regenerates `performance.png` with matplotlib 3.10.8. The engine itself needs no third-party package.
