"""In-memory relational algebra, using explicit loops and tuple equality."""

from dataclasses import dataclass, replace
from decimal import Decimal
from time import perf_counter
from parser import ParseError, parse


class ExecutionError(Exception):
    def __init__(self, category, message):
        super().__init__(f'{category} error: {message}')


@dataclass
class Statistics:
    join_pairs: int = 0
    selection_rows: int = 0
    wall_seconds: float = 0.0
    output_rows: int = 0


@dataclass(frozen=True)
class Column:
    name: str
    qualifier: str
    type: str = None
    qualified: bool = False

    @property
    def label(self):
        return f'{self.qualifier}.{self.name}' if self.qualified else self.name


@dataclass(frozen=True)
class Relation:
    columns: tuple
    rows: tuple


def tuple_equal(left, right):
    if len(left) != len(right):
        return False
    for a, b in zip(left, right):
        if type(a) is not type(b) or a != b:
            return False
    return True


def contains(rows, row):
    for candidate in rows:
        if tuple_equal(candidate, row):
            return True
    return False


def unique(rows):
    result = []
    for row in rows:
        if not contains(result, row):
            result.append(row)
    return tuple(result)


def check_columns(columns):
    names = []
    for column in columns:
        if column.label in names:
            raise ExecutionError('Schema', f'duplicate column {column.label}; use distinct names or rename the inputs')
        names.append(column.label)


def literal(node):
    return Decimal(node.value) if node.kind == 'Num' else node.value


def load_relations(source):
    tables = {}
    for definition in parse(source, relations=True).children:
        name, names = definition.value
        if name in tables:
            raise ExecutionError('Schema', f'duplicate relation {name}')
        columns = tuple(Column(n, name) for n in names)
        check_columns(columns)
        types = [None] * len(columns)
        rows = []
        for row in definition.children:
            if len(row.children) != len(columns):
                raise ExecutionError('Schema', f'{name}, line {row.token.line}: expected {len(columns)} values, got {len(row.children)}')
            values = []
            for index, node in enumerate(row.children):
                value_type = 'number' if node.kind == 'Num' else 'string'
                if types[index] is not None and types[index] != value_type:
                    raise ExecutionError('Type', f'{name}.{names[index]} mixes numbers and strings at line {node.token.line}')
                types[index] = value_type
                values.append(literal(node))
            rows.append(tuple(values))
        columns = tuple(replace(c, type=t) for c, t in zip(columns, types))
        tables[name] = Relation(columns, unique(rows))
    return tables


def resolve(name, columns):
    matches = []
    for index, column in enumerate(columns):
        match = (name == f'{column.qualifier}.{column.name}' if '.' in name
                 else name == column.name)
        if match:
            matches.append(index)
    if not matches:
        raise ExecutionError('Name', f'unknown attribute {name}')
    if len(matches) != 1:
        raise ExecutionError('Name', f'ambiguous attribute {name}; qualify it with a relation name')
    return matches[0]


def bind_operand(node, columns):
    if node.kind == 'Attr':
        index = resolve(node.value, columns)
        return columns[index].type, lambda row: row[index]
    value = literal(node)
    return ('number' if node.kind == 'Num' else 'string'), lambda row: value


def bind_condition(node, columns):
    """Resolve and type-check every branch, even when there are no input rows."""
    if node.kind == 'Not':
        child = bind_condition(node.children[0], columns)
        return lambda row: not child(row)
    if node.kind in ('And', 'Or'):
        left = bind_condition(node.children[0], columns)
        right = bind_condition(node.children[1], columns)
        if node.kind == 'And':
            return lambda row: left(row) and right(row)
        return lambda row: left(row) or right(row)
    left_type, left = bind_operand(node.children[0], columns)
    right_type, right = bind_operand(node.children[1], columns)
    if left_type is not None and right_type is not None and left_type != right_type:
        raise ExecutionError('Type', f'cannot compare {left_type} with {right_type}')

    def compare(row):
        a, b = left(row), right(row)
        if node.kind == 'Eq':
            return a == b
        if node.kind == 'Ne':
            return a != b
        if node.kind == 'Lt':
            return a < b
        if node.kind == 'Le':
            return a <= b
        if node.kind == 'Gt':
            return a > b
        return a >= b
    return compare


def select(relation, condition, stats=None, *, joining=False):
    matches = bind_condition(condition, relation.columns)
    rows = []
    for row in relation.rows:
        if stats is not None:
            stats.selection_rows += 1
            if joining:
                stats.join_pairs += 1
        if matches(row):
            rows.append(row)
    return Relation(relation.columns, tuple(rows))


def project(relation, attributes):
    indices = []
    for attribute in attributes.children:
        index = resolve(attribute.value, relation.columns)
        if index in indices:
            raise ExecutionError('Schema', f'projection repeats column {attribute.value}')
        indices.append(index)
    columns = tuple(relation.columns[i] for i in indices)
    rows = (tuple(row[i] for i in indices) for row in relation.rows)
    return Relation(columns, unique(rows))


def rename(relation, name):
    columns = tuple(replace(c, qualifier=name, qualified=False) for c in relation.columns)
    check_columns(columns)
    return Relation(columns, relation.rows)


def times(left, right, *, materialize=True):
    columns = tuple(replace(c, qualified=True) for c in left.columns + right.columns)
    check_columns(columns)

    def pairs():
        for a in left.rows:
            for b in right.rows:
                yield a + b

    rows = pairs()
    return Relation(columns, tuple(rows) if materialize else rows)


def compatible(left, right):
    if len(left.columns) != len(right.columns):
        raise ExecutionError('Schema', f'set operation requires the same number of columns; left has {len(left.columns)}, right has {len(right.columns)}')
    for index, (a, b) in enumerate(zip(left.columns, right.columns), start=1):
        if a.label != b.label:
            raise ExecutionError('Schema', f'set operation requires the same column names in the same order; column {index} is {a.label} on the left and {b.label} on the right')
        if a.type is not None and b.type is not None and a.type != b.type:
            raise ExecutionError('Schema', f'incompatible types for column {a.label}: {a.type} and {b.type}')
    # An empty input definition has no values from which to infer a type.
    return tuple(replace(a, type=a.type or b.type) for a, b in zip(left.columns, right.columns))


def set_operation(kind, left, right):
    columns = compatible(left, right)
    if kind == 'Union':
        rows = unique(left.rows + right.rows)
    elif kind == 'Intersect':
        rows = tuple(row for row in left.rows if contains(right.rows, row))
    else:
        rows = tuple(row for row in left.rows if not contains(right.rows, row))
    return Relation(columns, rows)


def evaluate(tree, tables, stats=None):
    if tree.kind == 'Relation':
        if tree.value not in tables:
            raise ExecutionError('Name', f'unknown relation {tree.value}')
        return tables[tree.value]
    if tree.kind in ('Select', 'Project', 'Rename'):
        parameter, child = tree.children
        relation = evaluate(child, tables, stats)
        if tree.kind == 'Select':
            return select(relation, parameter, stats)
        if tree.kind == 'Project':
            return project(relation, parameter)
        return rename(relation, parameter.value)
    if tree.kind == 'Join':
        condition, left, right = tree.children
        # Feed every product pair to selection without storing rejected pairs.
        product = times(evaluate(left, tables, stats), evaluate(right, tables, stats),
                        materialize=False)
        return select(product, condition, stats, joining=True)
    left = evaluate(tree.children[0], tables, stats)
    right = evaluate(tree.children[1], tables, stats)
    if tree.kind == 'Times':
        return times(left, right)
    return set_operation(tree.kind, left, right)


def execute(query, tables, stats=None):
    if stats is not None:
        stats.join_pairs = stats.selection_rows = stats.output_rows = 0
        stats.wall_seconds = 0.0
    tree = parse(query)
    started = perf_counter() if stats is not None else None
    try:
        result = evaluate(tree, tables, stats)
        if stats is not None:
            stats.wall_seconds = perf_counter() - started
            stats.output_rows = len(result.rows)
        return result
    except RecursionError:
        # Point to the root operation of the tree that exceeded the limit.
        raise ParseError('query tree rooted here is too deep to execute', tree.token) from None


def format_relation(relation):
    def display(value):
        if isinstance(value, str):
            return "'" + value.replace("'", "''") + "'"
        return format(value, 'f')

    lines = ['(' + ', '.join(c.label for c in relation.columns) + ') = {']
    for row in relation.rows:
        lines.append('  ' + ', '.join(display(value) for value in row))
    lines.append('}')
    return '\n'.join(lines)
