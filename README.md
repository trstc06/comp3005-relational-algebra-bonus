# Relational algebra engine

The Python program reads tables, parses queries, prints trees and executes all required operators in memory. The engine uses only the standard library; the report plot uses matplotlib.

## Running it

From the `Bonus Assignment` folder:

```sh
python3 ra.py --tree "project[Name](select[Age>30](Employees))"
python3 ra.py --relations relations.txt --query "project[DID](Employees)"
python3 ra.py --relations relations.txt --query "Emp join[Emp.DID=Dept.DID] Dept"
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

`relations.txt` contains the assignment's Employees example and small tables for joins. The projection command returns:

```text
(DID) = {
  'D1'
  'D2'
}
```

`--tree` prints the tree without loading or executing anything. `--query` requires a relation file. Errors print a message and return a nonzero exit code.

## How it works

`tokenizer.py` scans characters, `parser.py` builds the tree, `engine.py` runs it, and `ra.py` supplies the commands. Execution follows the tree without reordering operations. Products use nested loops; a theta join passes each product pair straight to selection instead of storing the entire product first. It keeps both join columns, unlike a natural join.

Each column stores its name, relation qualifier and type. Selection keeps the schema. Projection keeps the listed order and removes duplicate rows. Set operations require matching column names, order and types, and keep the left schema. Our own column-by-column tuple equality removes duplicates; no built-in set conversion is used. Numbers use `Decimal`, so `1` and `1.0` are equal. Strings compare case-sensitively, and comparing a number with a string is a type error.

Types are inferred from input values, and mixing numbers and strings in one column is an error. An initially empty table has unknown column types because the file syntax has no type declarations. Those types can match either type in a set operation and become known from the other input. Results that become empty after an operation retain their column types. Empty results print the column header and braces with no rows.

## Column names and self-joins

A column can be unqualified if its name identifies exactly one column. Otherwise, write its relation qualifier, such as `Emp.DID`. Products qualify every column and reject name collisions. Nested products keep the original qualifiers. Selection and projection retain qualifiers; rename replaces them with the new relation name. Renaming a combined table with repeated base column names is a schema error because the new qualifier would make those names collide.

Case 20 works with:

```sh
python3 ra.py --relations relations.txt --query "rename[E2](Emp) join[Emp.MgrID=E2.EID] Emp"
```

The left copy represents managers under the name `E2`; the right copy keeps the name `Emp`. The condition matches each employee's `MgrID` to a manager's `EID`. Without rename, both copies would have columns such as `Emp.EID`, so names would collide and the condition could not distinguish the copies. Both copies retain all their columns in the result.

For case 24, `project[Name,Name](R)` is a schema error. Referring to the same column twice through different spellings, such as `Name` and `R.Name`, is also an error.

## Error handling

The program reports five categories: lexical (invalid characters or strings), syntax (invalid structure), name (unknown or ambiguous names), schema (incompatible columns) and type (incompatible values). Lexical and syntax errors include a line and column. A query too deep to execute reports the position of its root operation. Set-operation errors identify differing column counts or the first mismatched column.

Errors go to standard error with exit code 1 and no result on standard output. Invalid command-line usage returns code 2. The command-line layer catches expected input errors so they do not print Python tracebacks. Names and types are checked even on empty tables and in condition branches that could be skipped. A valid empty result is successful and still prints its schema.

`test_errors.py` runs the actual command-line program against invalid queries and temporary relation files. It checks all five categories, error positions, missing and unreadable files, excessive nesting, exit codes and absence of tracebacks.

## Data generator and measurements

`generator.py` writes `R(a,b)` and `S(b,c)`. Choose each table's row count and `--matches`, the exact number of S rows that each R row matches on `R.b=S.b`. It accepts integer match counts from zero to the S row count. The default is one; for an empty S, specify zero.

```sh
python3 generator.py --r-rows 3 --s-rows 4 --matches 2 --output generated.txt
python3 ra.py --relations generated.txt --query "R join[R.b=S.b] S" --stats
python3 ra.py --relations generated.txt --query "select[a<2](R)" --stats
python3 ra.py --relations generated.txt --query "project[b](R)" --stats
```

Use a new output filename when generating another file; the generator refuses to overwrite an existing file. It creates no folders. Generation is deterministic: R has unique `a` values and always has `b=0`; the first `--matches` rows of S have `b=0`, and the rest have `b=1`. S has unique `c` values. This preserves the requested row counts under set semantics and gives exactly `r_rows * matches` join results. This is a controlled, skewed dataset, not a random sample.

`--stats` keeps the normal table on standard output and writes a JSON measurement record to standard error:

| Field | What is measured |
| --- | --- |
| `join_pairs` | Increments once for each tuple pair tested by a join, whether or not it matches. |
| `selection_rows` | Increments once for each row tested by selection, including the selection inside a join. |
| `wall_seconds` | Elapsed evaluation time measured with `perf_counter()`, excluding input loading, query parsing and result printing. |
| `output_rows` | Number of rows in the final result. |

Counters accumulate across operators within one query and reset for each `execute()` call. A compound condition still counts once per input row, not once per individual comparison. A plain product does not compare pairs against a predicate, so it does not increment `join_pairs`. Projection has timing and output size but no selection or join count. Counts are incremented inside the execution loop, not calculated from table sizes.

For the 3-by-4 example above, the measured join count is 12, the selection count is 12, and the output count is 6. A join's selection count describes the same 12 pair tests, so do not add the two counters together. The selection example examines 3 rows and returns 2; projection returns one distinct `b` value.

`test_measurements.py` verifies these counts, filtered inputs, multiple joins, empty tables, zero/full match rates, repeatable generation and counter reset. A join still checks every pair, but only matching rows are kept. A standalone `times` still stores the full product, and a high match rate can also make a join result very large. Input duplicate removal and projection with many distinct results can take quadratic time because duplicate checks use linear searches.

## Performance study

`REPORT.md` contains the required join table, log-log plot, selection and projection comparison, million-row prediction and match-rate experiment. Raw measurements are in `measurements.jsonl`.

```sh
python3 experiment.py --output new-measurements.jsonl
python3 plot_results.py
```

The experiment generates temporary input files and runs all required sizes up to 64,000 rows per table. It can take a long time and refuses to overwrite an existing measurement file. The plotting command reads the saved `measurements.jsonl` and needs matplotlib; the engine and experiment runner use only Python's standard library. The million-row case is predicted in the report, not executed.

## Progress

All 89 tests pass, covering required cases 1-25, day 10 error handling and generation, measurements, streamed join equivalence and both results in the grammar ambiguity example. The tests also check input validation, schema preservation, numeric equality and conditions on empty tables. `GRAMMAR.md` contains the grammar and grouping decisions.

The day 12 experiment is recorded in `REPORT.md` and `measurements.jsonl`. `GRAMMAR.md` includes the ambiguity trees and final rules. The personal RelaX practice, reading, video explanation and Brightspace submission are still to be done by the student.
