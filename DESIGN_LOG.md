# Design log

Dates are approximate, based on the order of my working sessions.

## 2026-09-20: grammar and first tokenizer

I started by writing the EBNF and choosing how operators group. I then worked on a handwritten Python tokenizer for query text. Compact input such as `select[x1=3](R)` was a useful check, but relation-file input was not handled yet.

## 2026-09-20: clearer grammar notes

I shortened the grammar explanations and checked the rules for precedence, names, strings and numbers against the examples. This was a writing pass, so I did not change the parser or claim that the full grammar was finished.

## 2026-09-21: relation-file tokens

The first AI-assisted tokenizer covered queries but missed part of the relation-file format. I found this by comparing it with the assignment's example: it could not scan braces or bare row values. I added those tokens and checked that the sample table could be read.

## 2026-09-21: parser and tree printer

I added a recursive descent parser and a printer for its parse tree. I used cases 10 and 11 to check left grouping, then tried nested conditions and malformed queries to check that the parser reported useful errors. I also wrote down a case 11 data example where right grouping would give a different result.

## 2026-09-22: operators and schemas

I added relation loading and the operations that evaluate the parse tree. I checked duplicate removal, column names and types, ambiguous attributes and the renamed self-join. Empty tables took extra care because there are no values from which to infer column types.

## 2026-09-23: error messages

I tested the five error categories through the command line. The AI-assisted execution-depth error lacked a source position, and a schema error about column order did not say which columns differed. I found both by running the error cases, fixed the messages and reran the tests.

## 2026-09-23: generator and counters

I added the R and S data generator and counters inside the selection and join loops. Small runs with zero, one and many matches showed that the comparison count stayed the same while the number of output rows changed. Before the large experiment, I noticed that the join still built the whole product in memory, so that needed a separate fix.

## 2026-09-24: large experiment and grammar check

The earlier AI-assisted join materialized the product before selecting matches. Planning the 64,000 by 64,000 run exposed the problem: it would create 4,096,000,000 intermediate rows. I changed the join to pass pairs to selection as they are generated, checked that results and counters stayed correct, corrected the grammar's line-break rules and ran the measurements.

## 2026-09-25: report and submission check

I used the measurements to write `REPORT.md` and make its log-log plot. The largest join took 1,408.401873 seconds and checked 4,096,000,000 pairs. During the submission check, I found the test files in the project root instead of the required `tests/` folder, moved them, fixed their paths and confirmed that all 89 tests passed.

## 2026-09-27: documentation check

I reviewed `README.md`, `GRAMMAR.md` and `REPORT.md` to make the explanations easier to follow while keeping the required DBMS terms. The README still did not clearly explain why the self-join needs `rename`, so I added that explanation and checked the tests again.

## 2026-09-28: submission files and log

I checked the submitted files against the assignment list and found an optional plotting script and raw results export that were not required. I removed those files, fixed their references in the README and report, and tested a fresh GitHub checkout; all 89 tests passed. I also revised this log so its entries describe the work and problems more plainly.
