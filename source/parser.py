"""Recursive descent parser and tree printer. No query execution."""

from dataclasses import dataclass, field
from .tokenizer import Token, tokenize


@dataclass(frozen=True)
class Node:
    kind: str
    value: object = None
    children: tuple = ()
    token: Token = field(default=None, compare=False, repr=False)


class ParseError(Exception):
    def __init__(self, message, token):
        self.offset = token.offset
        self.line = token.line
        self.column = token.column
        super().__init__(f'Syntax error at line {self.line}, column {self.column}: {message}')


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.index = 0

    @property
    def current(self):
        return self.tokens[self.index]

    def peek(self):
        return self.tokens[min(self.index + 1, len(self.tokens) - 1)]

    def take(self):
        token = self.current
        if token.kind != 'EOF':
            self.index += 1
        return token

    def accept(self, kind, value=None):
        if self.current.kind == kind and (value is None or self.current.value == value):
            return self.take()
        return None

    def expect(self, kind, description, value=None):
        token = self.accept(kind, value)
        if token is None:
            found = 'end of input' if self.current.kind == 'EOF' else repr(self.current.text)
            raise ParseError(f'expected {description}; found {found}', self.current)
        return token

    def binary_sequence(self, operand, operators):
        left = operand()
        while self.current.kind == 'NAME' and self.current.value in operators:
            operator = self.take()
            right = operand()
            left = Node(operators[operator.value], children=(left, right), token=operator)
        return left

    def expression(self):
        return self.binary_sequence(self.intersection, {'union': 'Union', 'minus': 'Minus'})

    def intersection(self):
        return self.binary_sequence(self.product, {'intersect': 'Intersect'})

    def product(self):
        left = self.primary()
        while self.current.kind == 'NAME' and self.current.value in ('times', 'join'):
            operator = self.take()
            if operator.value == 'join':
                self.expect('LBRACKET', "'[' after join")
                condition = self.condition()
                self.expect('RBRACKET', "']' after join condition")
                right = self.primary()
                left = Node('Join', children=(condition, left, right), token=operator)
            else:
                left = Node('Times', children=(left, self.primary()), token=operator)
        return left

    def primary(self):
        if self.accept('LPAREN'):
            result = self.expression()
            self.expect('RPAREN', "closing ')' for expression")
            return result
        name = self.expect('NAME', 'a relation name or an expression')
        if name.value not in ('select', 'project', 'rename') or self.current.kind != 'LBRACKET':
            return Node('Relation', name.value, token=name)
        self.take()
        if name.value == 'select':
            parameter = self.condition()
        elif name.value == 'project':
            attributes = [self.attribute()]
            while self.accept('COMMA'):
                attributes.append(self.attribute())
            parameter = Node('Attributes', children=tuple(attributes))
        else:
            alias = self.expect('NAME', 'a new relation name')
            parameter = Node('Alias', alias.value, token=alias)
        self.expect('RBRACKET', "closing ']' after parameter")
        self.expect('LPAREN', "'(' before input expression")
        child = self.expression()
        self.expect('RPAREN', "closing ')' after input expression")
        return Node(name.value.capitalize(), children=(parameter, child), token=name)

    def condition(self):
        return self.binary_sequence(self.conjunction, {'or': 'Or'})

    def conjunction(self):
        return self.binary_sequence(self.negation, {'and': 'And'})

    def negation(self):
        if (self.current.kind == 'NAME' and self.current.value == 'not'
                and self.peek().kind not in ('COMPARE', 'DOT')):
            operator = self.take()
            return Node('Not', children=(self.negation(),), token=operator)
        if self.accept('LPAREN'):
            result = self.condition()
            self.expect('RPAREN', "closing ')' in condition")
            return result
        left = self.operand()
        operator = self.expect('COMPARE', 'a comparison operator')
        right = self.operand()
        kinds = {'=': 'Eq', '!=': 'Ne', '<': 'Lt', '<=': 'Le', '>': 'Gt', '>=': 'Ge'}
        return Node(kinds[operator.value], children=(left, right), token=operator)

    def attribute(self):
        name = self.expect('NAME', 'an attribute name (the list cannot be empty)')
        value = name.value
        if self.accept('DOT'):
            value += '.' + self.expect('NAME', 'an attribute name after the dot').value
        return Node('Attr', value, token=name)

    def literal(self):
        token = self.current
        if token.kind not in ('NUMBER', 'STRING'):
            raise ParseError('expected a number or string value', token)
        self.take()
        return Node('Num' if token.kind == 'NUMBER' else 'Str', token.value, token=token)

    def operand(self):
        if self.current.kind == 'NAME':
            return self.attribute()
        return self.literal()

    def relation_file(self):
        definitions = []
        while self.accept('NEWLINE'):
            pass
        while self.current.kind != 'EOF':
            name = self.expect('NAME', 'a relation name')
            self.expect('LPAREN', "'(' before column names")
            columns = [self.expect('NAME', 'a column name').value]
            while self.accept('COMMA'):
                columns.append(self.expect('NAME', 'a column name').value)
            self.expect('RPAREN', "')' after column names")
            self.expect('COMPARE', "'=' before table body", '=')
            self.expect('LBRACE', "'{' before table body")
            self.expect('NEWLINE', 'a line break before table rows')
            rows = []
            while self.current.kind not in ('RBRACE', 'EOF'):
                values = [self.literal()]
                while self.accept('COMMA'):
                    values.append(self.literal())
                self.expect('NEWLINE', 'a line break after the row')
                rows.append(Node('Row', children=tuple(values), token=values[0].token))
            self.expect('RBRACE', "closing '}' for table")
            # The closing brace must occupy its own line.
            if self.current.kind not in ('NEWLINE', 'EOF'):
                raise ParseError("expected a line break after '}'", self.current)
            while self.accept('NEWLINE'):
                pass
            definitions.append(Node('Definition', (name.value, tuple(columns)), tuple(rows), name))
        return Node('RelationFile', children=tuple(definitions))


def parse(source, *, relations=False):
    parser = Parser(tokenize(source, relations=relations))
    try:
        result = parser.relation_file() if relations else parser.expression()
        parser.expect('EOF', 'end of input')
        return result
    except RecursionError:
        raise ParseError('input nesting is too deep', parser.current) from None


def format_tree(tree):
    """Print every node without evaluating it; iterative to handle long chains."""
    lines = []
    pending = [(tree, '', '', '')]
    while pending:
        node, prefix, connector, role = pending.pop()
        label = node.kind
        if node.kind == 'Definition':
            name, columns = node.value
            label += f'({name}, columns=[{", ".join(columns)}])'
        elif node.value is not None:
            value = repr(node.value) if node.kind == 'Str' else str(node.value)
            label += f'({value})'
        lines.append(prefix + connector + role + label)
        child_prefix = prefix + ('    ' if connector == '`-- ' else '|   ' if connector else '')
        roles = {'Select': ('condition: ', 'input: '),
                 'Project': ('columns: ', 'input: '),
                 'Rename': ('name: ', 'input: '),
                 'Join': ('condition: ', 'left: ', 'right: ')}
        for index in range(len(node.children) - 1, -1, -1):
            last = index == len(node.children) - 1
            child_role = roles[node.kind][index] if node.kind in roles else ''
            pending.append((node.children[index], child_prefix, '`-- ' if last else '|-- ', child_role))
    return '\n'.join(lines)
