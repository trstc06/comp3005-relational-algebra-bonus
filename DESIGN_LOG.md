# Design log

## 2026-09-20: day 3 grammar and start of days 4-5

I drafted the EBNF with AI assistance, chose precedence levels and left associativity for binary operators, and used Python for a handwritten query tokenizer. I checked the lexical parts of assignment cases 1-9 and six additional scanner checks; all 15 tests passed, but the required parse-tree equivalence check cannot be completed until the parser exists. The tokenizer does not yet scan relation-file fields, and my days 1-2 reading and RelaX practice are still pending; no parser, evaluator or performance results are claimed for this session.

## 2026-09-21: simplify the grammar document

I shortened the explanations and replaced technical wording with plain English while keeping both EBNF blocks unchanged. I checked that the precedence tables, keyword rules, string and number rules, and planned parsing approach remained; the day 13 requirements are still marked as unfinished.

## 2026-09-21: complete days 4-5 tokenization

I added relation-file scanning and checked the assignment's example table, whole-field number recognition, quoted values, comments, row boundaries and original token positions. The earlier AI-assisted tokenizer was incomplete because it only accepted queries; comparing it with the relation-definition grammar showed that it could not read braces or distinguish bare table values from names, so I added a separate relation mode without adding a parser. All 24 tests now pass, including the lexical checks for cases 1-9 and command-line error handling; full parsing and the identical-tree check for cases 1-2 remain for days 6-7.

## 2026-09-21: days 6-7 parser and tree printer

I implemented handwritten recursive descent, tree nodes and a `--tree` command, then checked precedence, left associativity, nested conditions, contextual keywords and relation-definition syntax. All 46 tests passed, including identical trees for cases 1-2, the parser checks for cases 10-17, and positioned errors for missing parentheses and empty projections; case 14's execution check still needs the days 8-9 operators. I also documented a concrete case 11 example where right grouping gives a different result; no test failures occurred in this session, and I have not claimed engine results or invented AI mistakes.

## 2026-09-21: days 8-9 operators and schemas

I added table loading, the six core operators, rename and theta join with AI assistance, using nested loops and my own tuple equality for duplicate removal. I kept column types and qualifiers in the schema, rejected repeated projection columns, and documented self-joins and unknown types for initially empty tables. All 69 tests passed, including cases 18-25, case 14's nested execution and the case 11 grouping example; no test failures occurred, and the day 10 error review and later tasks remain unfinished.

## 2026-09-22: day 10 error handling

I tested all five error categories through the real command-line program, including invalid table files, empty inputs, skipped condition branches and excessive query depth. Two new diagnostic checks initially failed: the earlier AI-assisted execution-depth handler omitted a source position, and the column-order error did not identify the conflicting columns; I added the root operation's position and specific schema mismatch details. All 78 tests now pass, with the error tests checking nonzero exit codes, clear messages and no Python tracebacks; day 11 and later work remain pending.

## 2026-09-22: day 11 data generator and instrumentation

I added a deterministic generator with separate R and S sizes and an exact number of S matches per R row, using unique a and c values so duplicate removal does not shrink the inputs. I added loop-based join and selection counters, evaluation timing and output size through `--stats`, then checked small inputs, filtered and repeated joins, zero/full match rates and counter reset; all 87 tests passed with no test failures this session. The join still materializes its product, which is a memory limitation for the larger experiment; the day 12 measurements and report have not been completed.

## 2026-09-23: days 12-13 performance study and final grammar

The earlier AI-assisted join stored the whole product, which would require billions of intermediate rows at the required sizes; reviewing the largest experiment exposed this memory problem, so I changed the product to feed pairs directly to selection while still comparing every pair with nested loops. I added a reproducible experiment runner, checked streamed joins against materialized product-plus-selection, and finished the grammar's two-tree example; the grammar review also found and corrected missing line-break rules between definitions and CR line endings. All 89 tests passed. The full experiment finished on September 23: all seven join sizes reached the expected comparison counts, and the match-rate trials were saved in `measurements.jsonl`.

## 2026-09-25: report and final hand-in review

I checked all 115 saved records against the required sizes and output counts, made the log-log plot, and wrote `REPORT.md` from the actual timings. The 64,000-by-64,000 join took 1,408.401873 seconds and counted 4,096,000,000 pairs; the measured join slope is 2.032. During the hand-in review I found that my tests were still in the project root although Section 9 asks for `tests/`, so I moved them there, fixed the two command-line test paths and reran all 89 tests successfully. The repository link, my own RelaX practice and reading, and the personal video explanation still require my participation.
