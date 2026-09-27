# Design log

## 2026-09-20: first grammar and tokenizer

I drafted the EBNF and chose left grouping for binary operators, then started a handwritten tokenizer in Python with AI help. I checked the lexical parts of cases 1 to 9 and six extra scanner cases; 15 tests passed, but the tokenizer did not yet handle relation files.

## 2026-09-21: grammar wording

I made the grammar explanations shorter and checked that the EBNF, precedence table, keywords, strings and numbers still matched the draft. This was a wording change; the parser and later grammar examples were not finished yet.

## 2026-09-21: relation-file tokenizer

The first AI-assisted tokenizer handled queries but missed relation-file syntax. I found this by comparing it with the relation grammar: it could not scan braces or bare row values, so I added relation-file scanning and tested the assignment's sample table. All 24 tokenizer and command-line checks passed.

## 2026-09-21: parser and tree printer

I wrote a recursive descent parser and a tree printer, then tested grouping, nested conditions and errors for missing parentheses or empty projections. Cases 1 and 2 produced the same tree, and all 46 tests passed. I also wrote down a case 11 example where the other grouping gives a different answer.

## 2026-09-21: operators and schemas

I added table loading, the relational algebra operators, rename and theta join. I checked duplicate removal, column types, ambiguous names, self-joins and cases 18 to 25; all 69 tests passed. Empty tables needed special care because their columns have no values from which to infer types.

## 2026-09-22: error handling

I tested the five error categories through the command-line program. Two checks failed: the AI-assisted execution-depth handler did not report a source position, and a column-order error did not name the conflicting columns. I fixed both messages and reran the tests; all 78 passed.

## 2026-09-22: generator and counters

I wrote a generator with separate R and S sizes and a chosen number of matches per R row. I added counters inside the join and selection loops, timed query execution and tested zero, one and full match rates; all 87 tests passed. I then noticed that the join stored every product pair, which would use too much memory for the required large experiment.

## 2026-09-23: experiment and final grammar

The earlier AI-assisted join built the full product before filtering it. I found the problem while planning the 64,000 by 64,000 run: that would store 4,096,000,000 intermediate rows, so I changed the join to pass each pair straight to selection while still checking every pair. I tested that it gives the same results, corrected the written grammar's line-break rules, and ran the full experiment; all 89 tests passed and the measurements were saved.

## 2026-09-25: report and hand-in check

I used the saved measurements to write `REPORT.md` and draw the log-log plot. The largest join took 1,408.401873 seconds and counted 4,096,000,000 pairs. During the hand-in check I found the tests in the project root instead of the required `tests/` folder, moved them, fixed two test paths and reran all 89 tests successfully.
