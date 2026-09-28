"""Handwritten tokenizer for queries and relation files, without regex.

From the project folder:
    python3 -m source.tokenizer 'select[x1=3](R)'
    python3 -m source.tokenizer --relations relations.txt
    python3 -m unittest discover -s tests -p 'test_tokenizer.py' -v

Output shows line:column, token kind, and value. This reads tokens only;
the parser, table validation, and execution are later project stages.
"""

from dataclasses import dataclass
import sys
from pathlib import Path


@dataclass(frozen=True)
class Token:
    kind: str
    text: str
    value: str
    offset: int
    line: int
    column: int


class LexicalError(Exception):
    def __init__(self, message, offset, line, column):
        self.offset = offset
        self.line = line
        self.column = column
        super().__init__(f"Lexical error at line {line}, column {column}: {message}")


def is_digit(char):
    return '0' <= char <= '9'


def is_name_start(char):
    return 'a' <= char <= 'z' or 'A' <= char <= 'Z' or char == '_'


def is_number(text):
    """Check a complete relation field against the grammar's number rule."""
    i = 1 if text.startswith('-') else 0
    start = i
    while i < len(text) and is_digit(text[i]):
        i += 1
    if i == start:
        return False
    if i < len(text) and text[i] == '.':
        i += 1
        start = i
        while i < len(text) and is_digit(text[i]):
            i += 1
        if i == start:
            return False
    return i == len(text)


def tokenize(source, *, relations=False):
    """Return query tokens with 0-based offsets and 1-based lines/columns.

    Numeric values retain their spelling so evaluation can choose a numeric
    representation later. NAME tokens include contextual operator words.
    In relations mode, braces switch between headers and row values.
    NEWLINE tokens preserve nonblank line boundaries. Syntax and schema
    checks belong to the later parser, not this scanner.
    """
    tokens = []
    i, line, column = 0, 1, 1
    line_has_content = False
    in_body = False
    punctuation = {
        '[': 'LBRACKET', ']': 'RBRACKET', '(': 'LPAREN', ')': 'RPAREN',
        ',': 'COMMA', '.': 'DOT',
    }
    if relations:
        punctuation.update({'{': 'LBRACE', '}': 'RBRACE'})
    while i < len(source):
        char = source[i]
        if char in ' \t':
            i += 1
            column += 1
            continue
        if char in '\r\n':
            start = i
            if char == '\r' and i + 1 < len(source) and source[i + 1] == '\n':
                i += 1
            i += 1
            if relations and line_has_content:
                tokens.append(Token('NEWLINE', source[start:i], '\n', start, line, column))
            line += 1
            column = 1
            line_has_content = False
            continue
        if not line_has_content and source.startswith('//', i):
            while i < len(source) and source[i] not in '\r\n':
                i += 1
                column += 1
            continue

        start, start_line, start_column = i, line, column
        line_has_content = True
        if relations and in_body and char not in ",}'":
            # Bare fields can contain punctuation, e.g. E-1 or a.b.
            while i < len(source) and source[i] not in ',}\r\n':
                i += 1
            value = source[start:i].rstrip(' \t')
            for index, character in enumerate(value):
                if character.isspace() or character in "(){}'":
                    raise LexicalError('quote this text value', start + index, start_line, start_column + index)
            if value.startswith('//'):
                raise LexicalError('quote values starting with //', start, start_line, start_column)
            # Leave padding for the normal whitespace handler.
            i = start + len(value)
            kind = 'NUMBER' if is_number(value) else 'STRING'
        elif is_name_start(char):
            i += 1
            while i < len(source) and (is_name_start(source[i]) or is_digit(source[i])):
                i += 1
            kind, value = 'NAME', source[start:i]
        elif is_digit(char) or (char == '-' and i + 1 < len(source) and is_digit(source[i + 1])):
            if char == '-':
                i += 1
            while i < len(source) and is_digit(source[i]):
                i += 1
            if i < len(source) and source[i] == '.' and i + 1 < len(source) and is_digit(source[i + 1]):
                i += 1
                while i < len(source) and is_digit(source[i]):
                    i += 1
            kind, value = 'NUMBER', source[start:i]
        elif char == "'":
            i += 1
            characters = []
            while True:
                if i == len(source) or source[i] in '\r\n':
                    raise LexicalError('unterminated string', start, start_line, start_column)
                if source[i] == "'":
                    if i + 1 < len(source) and source[i + 1] == "'":
                        characters.append("'")
                        i += 2
                        continue
                    i += 1
                    break
                characters.append(source[i])
                i += 1
            kind, value = 'STRING', ''.join(characters)
            if relations and in_body:
                following = i
                while following < len(source) and source[following] in ' \t':
                    following += 1
                if following < len(source) and source[following] not in ',}\r\n':
                    raise LexicalError('expected a delimiter after quoted value', following, line, column + following - start)
        elif source[i:i + 2] in ('>=', '<=', '!='):
            i += 2
            kind, value = 'COMPARE', source[start:i]
        elif char in '=<>':
            i += 1
            kind, value = 'COMPARE', char
        elif char in punctuation:
            i += 1
            kind, value = punctuation[char], char
            if relations and char in '{}':
                in_body = char == '{'
        else:
            raise LexicalError(f'unexpected character {char!r}', start, start_line, start_column)
        column += i - start
        tokens.append(Token(kind, source[start:i], value, start, start_line, start_column))
    tokens.append(Token('EOF', '', '', i, line, column))
    return tokens


def main():
    relations = len(sys.argv) == 3 and sys.argv[1] == '--relations'
    if not relations and len(sys.argv) != 2:
        print('Usage: python3 -m source.tokenizer "QUERY"\n'
              '       python3 -m source.tokenizer --relations FILE', file=sys.stderr)
        return 2
    try:
        # Preserve CRLF so token offsets still match the original file.
        if relations:
            with Path(sys.argv[2]).open(encoding='utf-8', newline='') as stream:
                source = stream.read()
        else:
            source = sys.argv[1]
        tokens = tokenize(source, relations=relations)
    except (LexicalError, OSError, UnicodeError) as error:
        print(error, file=sys.stderr)
        return 1
    for token in tokens:
        print(f'{token.line}:{token.column} {token.kind} {token.value!r}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
