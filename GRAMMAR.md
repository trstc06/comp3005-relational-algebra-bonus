# Grammar

This grammar describes the allowed way to write tables, queries and conditions for Section 4 of the assignment. A relation is a table, an attribute is a column, and a tuple is a row.

## How to read the EBNF

EBNF is a short way to write language rules: `=` means “is made of”, commas mean “followed by”, `|` means “or”, `{ ... }` means repeat zero or more times, and `[ ... ]` means optional. Quoted text must appear literally; `? ... ?` describes allowed characters. `EOF` means the input ends.

## Queries and conditions

```ebnf
query          = expression, EOF ;
expression     = set-expression ;
set-expression = intersection, { ("union" | "minus"), intersection } ;
intersection   = product, { "intersect", product } ;
product        = primary, { ("times", primary)
                         | ("join", "[", condition, "]", primary) } ;
primary        = name
               | "(", expression, ")"
               | "select", "[", condition, "]", "(", expression, ")"
               | "project", "[", attribute-list, "]", "(", expression, ")"
               | "rename", "[", name, "]", "(", expression, ")" ;
attribute-list = attribute, { ",", attribute } ;
attribute      = name, [ ".", name ] ;

condition      = disjunction ;
disjunction    = conjunction, { "or", conjunction } ;
conjunction    = negation, { "and", negation } ;
negation       = "not", negation | boolean-atom ;
boolean-atom   = "(", condition, ")" | comparison ;
comparison     = operand, comparison-op, operand ;
comparison-op  = "=" | "!=" | "<" | "<=" | ">" | ">=" ;
operand        = attribute | number | quoted-string ;
```

In queries, quote text values: `A=B` compares two columns, while `A='B'` compares a column with text. Write `a<b and b<c`, not `a<b<c`. A projection needs at least one column; repeating the same column, even through different references, is a schema error.

## Tables, names and values

```ebnf
relation-file  = { NEWLINE },
                 [ relation, { NEWLINE, relation }, [ NEWLINE ] ], EOF ;
relation       = name, "(", name-list, ")", "=", "{",
                 NEWLINE, { row, NEWLINE }, "}" ;
name-list      = name, { ",", name } ;
row            = value, { ",", value } ;
value          = number | quoted-string | bare-string ;

name           = letter-or-underscore, { letter-or-underscore | digit } ;
letter-or-underscore = ? ASCII A-Z, a-z, or underscore ? ;
digit          = "0" | "1" | "2" | "3" | "4"
               | "5" | "6" | "7" | "8" | "9" ;
number         = [ "-" ], digit, { digit }, [ ".", digit, { digit } ] ;
quoted-string  = "'", { string-character | "''" }, "'" ;
string-character = ? any character except a single quote, CR, or LF ? ;
bare-string    = bare-character, { bare-character } ;
bare-character = ? any character except whitespace, comma,
                    parentheses, braces, or single quote ? ;
NEWLINE        = "\n" | "\r\n" | "\r" ;
```

Each table row goes on its own line, with the closing brace on a separate line. Empty tables have no rows. Ignore blank lines and lines beginning with `//` after indentation, keeping other line boundaries. `NEWLINE` means an actual line break.

Read each whole unquoted field: if it matches `number`, it is numeric; otherwise it is text. For example, `32` is a number, but `E1` and `'32'` are text. Ignore spaces around fields. Quote values containing spaces, commas, parentheses, braces or quotes, and values starting with `//`. Empty text is `''`; a missing value is invalid.

Each row must have the declared number of values. Column names must be unique. Duplicate rows count only once. These checks happen separately from recognizing the grammar.

## Rules for reading tokens

A token is one piece of input, such as a name, number or operator.

- **Names:** case-sensitive, using the character rules above. Read the whole name, so `unionize` stays one token. Operator spellings are lowercase.
- **Keyword names:** scan all words as `NAME`. Their position decides their meaning: `union` is a column in `select[union=3](R)`, but an operator in `R union S`. At the start of an expression, `select`, `project` or `rename` followed by `[` starts an operation; otherwise it names a table. In conditions, `not` followed by a comparison operator or `.` names a column; otherwise it means negation.
- **Numbers and comparisons:** recognize `>=`, `<=` and `!=` as whole operators. A minus sign belongs to a number only immediately before a digit: `Age>-30` contains `>` and `-30`. Numbers allow integers and decimals, but no leading `+` or exponent notation.
- **Strings:** single quotes surround text. Inside them, `''` means one quote, so `'O''Brien'` means `O'Brien`. Punctuation inside strings is ordinary text. Backslash escapes and multiline strings are unsupported. Report an unclosed string at its opening quote.
- **Spacing:** ignore query spaces, tabs and line breaks, and whole-line `//` comments outside strings. Spaces between tokens are optional where their boundaries are clear: `select[x1=3](R)` works. Keep each token's offset, line and column for error messages.

## Which operation groups first?

Precedence decides which operators bind more tightly. Higher levels group first; parentheses override the defaults. Associativity decides grouping at the same level: “left” means work from left to right, and “right” means group from the right.

| Table-query level | Operators | Grouping | Grammar rule |
| --- | --- | --- | --- |
| 4 | Parentheses; `select`, `project`, `rename` | Explicit nesting | `primary` |
| 3 | `times`, `join[condition]` | Left | `product` |
| 2 | `intersect` | Left | `intersection` |
| 1 | `union`, `minus` | Left | `set-expression` |

| Condition level | Operators | Grouping | Grammar rule |
| --- | --- | --- | --- |
| 5 | Parentheses | Explicit nesting | `boolean-atom` |
| 4 | `=`, `!=`, `<`, `<=`, `>`, `>=` | No chaining | `comparison` |
| 3 | `not` | Right | `negation` |
| 2 | `and` | Left | `conjunction` |
| 1 | `or` | Left | `disjunction` |

For every repeated binary sequence in the grammar, combine the result so far with the next operand. This makes the repetition left-associative. For example:

- `A union B minus C` means `(A union B) minus C`.
- `A minus B minus C` means `(A minus B) minus C`.
- `A union B intersect C` means `A union (B intersect C)`.
- `a=1 and b=2 or c=3` means `((a=1) and (b=2)) or (c=3)`.

I put union and difference at the same level so mixed sequences follow their written order.

For case 11, let all three tables have one numeric column `x`: `A = {1, 2}`, `B = {2}`, and `C = {2}`. My grouping, `(A minus B) minus C`, gives `{1}`. The other grouping, `A minus (B minus C)`, gives `{1, 2}`, because `B minus C` is empty. The engine tests now verify both results.

## Why grouping matters

The assignment's deliberately naive grammar is:

```text
Expr ::= Expr "union" Expr
       | Expr "minus" Expr
       | "(" Expr ")"
       | IDENT
```

It allows two parse trees for the same input, `A union B minus C`:

```text
Tree 1: (A union B) minus C       Tree 2: A union (B minus C)

Expr                            Expr
|-- Expr                        |-- Expr
|   |-- Expr                    |   `-- IDENT(A)
|   |   `-- IDENT(A)             |-- "union"
|   |-- "union"                 `-- Expr
|   `-- Expr                        |-- Expr
|       `-- IDENT(B)                 |   `-- IDENT(B)
|-- "minus"                         |-- "minus"
`-- Expr                            `-- Expr
    `-- IDENT(C)                         `-- IDENT(C)
```

Use three tables with one numeric column `x`: `A={1,2}`, `B={2}` and `C={2}`. Tree 1 gives `{1}`: the union is `{1,2}`, then minus removes `2`. Tree 2 gives `{1,2}`: `B minus C` is empty, so its union with A is A. The same input can therefore mean different answers under the naive grammar.

The levels in my grammar remove this ambiguity:

```ebnf
set-expression = intersection, { ("union" | "minus"), intersection } ;
intersection   = product, { "intersect", product } ;
product        = primary, { ("times", primary)
                         | ("join", "[", condition, "]", primary) } ;
```

Each repetition combines the existing left tree with the next operand. This forces Tree 1 for `A union B minus C`. The right operand at this level is an `intersection`, so it cannot absorb an unparenthesized `minus`. To get Tree 2, the user must write `A union (B minus C)`. The engine tests check both results.

## Parser and sources

I use handwritten recursive descent in `parser.py` because each grammar level maps to a short method that is easy to trace and gives useful errors. Methods read each grammar level, and loops handle repeated binary operators. The resulting tree records the grouping without running the query. A rule starting with itself, such as `expression = expression, "minus", primary`, would repeatedly call itself without reading input. This is left recursion. My `set-expression` avoids it by reading `intersection` first, then repeating operator-operand pairs.

Sources: assignment Sections 4, 5, 7 and 11; Robert Nystrom's [Representing Code](https://craftinginterpreters.com/representing-code.html) and [Parsing Expressions](https://craftinginterpreters.com/parsing-expressions.html).

AI helped draft and review this grammar and code. Its first tokenizer missed relation-file syntax; tests later found missing source positions for execution-depth errors and unhelpful schema mismatch messages. The final grammar review also caught a missing line break between table definitions and missing support for CR line endings in the written rules. These were corrected to match the parser and scanner; see `DESIGN_LOG.md`. The linked chapters are references used for this draft, not a claim that I have completed my own days 1-2 reading or RelaX practice.
