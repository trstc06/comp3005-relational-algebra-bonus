"""Run the Section 8 measurements; writes one JSON record after each query."""

import argparse
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
import platform
import tempfile

from .engine import Statistics, execute, load_relations
from .generator import generate

SIZES = (1000, 2000, 4000, 8000, 16000, 32000, 64000)


def measure(stream, data, query, n, matches, group, trial):
    stats = Statistics()
    result = execute(query, data, stats)
    record = dict(group=group, n=n, m=n, matches=matches, query=query,
                  trial=trial, **asdict(stats))
    if group in ('join', 'match-rate'):
        assert stats.join_pairs == n * n
        assert stats.selection_rows == 0
        assert stats.output_rows == n * matches
    elif group == 'select':
        assert stats.selection_rows == n and len(result.rows) == n // 2
    else:
        assert len(result.rows) == 1
    stream.write(json.dumps(record) + '\n')
    stream.flush()
    print(f'{group}: n={n}, matches={matches}, trial={trial}, '
          f'{stats.wall_seconds:.6f}s, pairs={stats.join_pairs}, '
          f'output={stats.output_rows}', flush=True)


def inputs(n, matches):
    # Exercise the actual generator, file reader, parser and duplicate checks.
    with tempfile.TemporaryFile(mode='w+', encoding='utf-8', newline='') as file:
        generate(file, n, n, matches)
        file.seek(0)
        return load_relations(file.read())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='measurements.jsonl')
    args = parser.parse_args()
    with Path(args.output).open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(dict(group='environment', date=datetime.now().isoformat(),
                                    python=platform.python_version(),
                                    platform=platform.platform())) + '\n')
        stream.flush()
        for n in SIZES:
            print(f'Generating and loading n={n} (outside query timing)', flush=True)
            data = inputs(n, 1)
            measure(stream, data, 'R join[R.b=S.b] S', n, 1, 'join', 1)
            for trial in range(1, 8):
                measure(stream, data, f'select[a<{n // 2}](R)', n, 1, 'select', trial)
                measure(stream, data, 'project[b](R)', n, 1, 'project', trial)
            del data
        for matches in (0, 1, 1000):
            data = inputs(1000, matches)
            for trial in range(1, 4):
                measure(stream, data, 'R join[R.b=S.b] S', 1000, matches, 'match-rate', trial)


if __name__ == '__main__':
    main()
