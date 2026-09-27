# Relational algebra engine

This Python program reads relation files, parses relational algebra queries, prints parse trees and runs the queries in memory. It uses the Python standard library. Only the performance plot needs matplotlib.

## Run it

From this folder:

```sh
python3 ra.py --tree "A union B minus C"
python3 ra.py --relations relations.txt --query "project[DID](Employees)"
python3 ra.py --relations relations.txt --query "Emp join[Emp.DID=Dept.DID] Dept"
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

`--tree` shows how a query groups without running it. `--query` runs it against the named relation file. `relations.txt` contains small example tables. The test suite has 89 tests, including the assignment's 25 cases.

## What the files do

`tokenizer.py` splits text into tokens. `parser.py` turns query tokens into a parse tree. `engine.py` follows that tree to run the operators. `ra.py` handles the command line and prints results or errors. `generator.py` makes relation files for the performance study. `experiment.py` runs the measurements, and `plot_results.py` draws the plot from the saved results.

The engine supports `select`, `project`, `rename`, `times`, `join`, `union`, `intersect` and `minus`. Selection keeps rows that meet a condition. Projection keeps chosen columns and removes duplicate rows. Set operations require the same column names, order and types on both sides. A join checks pairs with nested loops and keeps both join columns. It passes each pair to selection without storing the whole product first.

A schema is the list of columns and their types. Types come from the input values. Numbers use Python's `Decimal`, so `1` and `1.0` compare equal. Strings are case-sensitive. Comparing a number with a string is a type error. An empty input table has unknown column types because the file format does not declare them. Even an empty result keeps its column names and known types.

Use a relation name when a column name is ambiguous, as in `Emp.DID`. To join a table with itself, rename one copy so the two sets of columns have different names:

```sh
python3 ra.py --relations relations.txt --query "rename[E2](Emp) join[Emp.MgrID=E2.EID] Emp"
```

Without `rename`, both copies would have columns such as `Emp.EID`. Their names would collide, so the join condition could not say which copy of `Emp` it means. `rename[E2](Emp)` makes the left copy's columns start with `E2` and leaves the right copy as `Emp`.

The program reports lexical, syntax, name, schema and type errors. Lexical and syntax errors include a line and column. Invalid queries exit with an error message instead of a Python traceback.

## Generate data and measure queries

`generator.py` writes `R(a,b)` and `S(b,c)`. Set the row counts separately and use `--matches` to choose how many S rows match each R row. For example:

```sh
python3 generator.py --r-rows 3 --s-rows 4 --matches 2 --output generated.txt
python3 ra.py --relations generated.txt --query "R join[R.b=S.b] S" --stats
```

The generator refuses to overwrite an existing file. In this example, each R row matches two S rows, so the join returns six rows. `--stats` prints the result normally and writes these measurements to standard error:

| Field | Meaning |
| --- | --- |
| `join_pairs` | Pairs checked by joins. |
| `selection_rows` | Rows checked by selections, including the selection inside a join. |
| `wall_seconds` | Time spent running the query, excluding loading, parsing and printing. |
| `output_rows` | Rows in the final result. |

For the example, both `join_pairs` and `selection_rows` are 12 because they count the same 3 by 4 pair checks. The counters increase during execution, not from a size formula.

[REPORT.md](REPORT.md) explains the full performance study. `measurements.jsonl` holds its raw results, and `performance.png` is the log-log plot. To repeat the study, run `python3 experiment.py --output new-measurements.jsonl`. It takes a long time and will not overwrite an existing file. Run `python3 plot_results.py` to redraw the plot from `measurements.jsonl`.

## Limits

The engine runs in memory and does not optimize query order. A plain `times` operation stores its full product, and a join with many matches can still create a large result. Removing duplicates from input tables or projections can be slow when many rows are distinct because the engine checks saved rows one by one. The report predicts the million-row join; it was not run.
