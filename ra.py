"""Print a query tree or execute a query against a relation file."""

import argparse
import json
from dataclasses import asdict
import sys
from parser import ParseError, format_tree, parse
from tokenizer import LexicalError
from engine import Statistics, ExecutionError, execute, format_relation, load_relations


def main():
    arguments = argparse.ArgumentParser(description='Run relational algebra queries or print their trees.')
    modes = arguments.add_mutually_exclusive_group(required=True)
    modes.add_argument('--tree', metavar='QUERY', help='print the tree without execution')
    modes.add_argument('--query', metavar='QUERY', help='execute against --relations FILE')
    arguments.add_argument('--relations', metavar='FILE')
    arguments.add_argument('--stats', action='store_true', help='write measured query statistics as JSON to standard error')
    args = arguments.parse_args()
    if args.stats and args.query is None:
        arguments.error('--stats requires --query')
    if args.query is not None and args.relations is None:
        arguments.error('--query requires --relations FILE')
    try:
        if args.tree is not None:
            output = format_tree(parse(args.tree))
        else:
            with open(args.relations, encoding='utf-8', newline='') as stream:
                tables = load_relations(stream.read())
            stats = Statistics() if args.stats else None
            output = format_relation(execute(args.query, tables, stats))
    except (LexicalError, ParseError, ExecutionError, OSError, UnicodeError) as error:
        print(error, file=sys.stderr)
        return 1
    print(output)
    if args.stats:
        print(json.dumps(asdict(stats)), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
