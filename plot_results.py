"""Plot the saved measurements. Requires matplotlib only for this report."""

import json
from math import log10
from pathlib import Path
from statistics import mean, median

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from experiment import SIZES


def slope(xs, ys):
    x = [log10(value) for value in xs]
    y = [log10(value) for value in ys]
    xm, ym = mean(x), mean(y)
    return sum((a - xm) * (b - ym) for a, b in zip(x, y)) / sum((a - xm) ** 2 for a in x)


def main():
    records = [json.loads(line) for line in Path('measurements.jsonl').read_text().splitlines()]
    fig, ax = plt.subplots(figsize=(9, 5.5), layout='constrained')
    for group, label, color in [('join', 'Join (one run)', '#1764ab'),
                                ('select', 'Select (median of 7)', '#c45d12'),
                                ('project', 'Project b (median of 7)', '#208150')]:
        values = []
        for n in SIZES:
            runs = [r for r in records if r['group'] == group and r['n'] == n]
            assert len(runs) == (1 if group == 'join' else 7), f'Missing {group} runs at {n}'
            values.append(median(r['wall_seconds'] for r in runs))
        gradient = slope(SIZES, values)
        print(group, 'slope:', f'{gradient:.6f}', 'seconds:', values)
        ax.loglog(SIZES, values, 'o-', label=f'{label}; slope {gradient:.2f}', color=color)
    ax.set(title='Measured query time as input size grows',
           xlabel='Rows per input relation, n = m (log scale)',
           ylabel='Evaluation time in seconds (log scale)')
    ax.set_xticks(SIZES, [f'{n:,}' for n in SIZES])
    ax.tick_params(axis='x', labelsize=9)
    ax.grid(True, which='both', alpha=0.2)
    ax.legend(loc='upper left')
    fig.savefig('performance.png', dpi=180)
    plt.close(fig)


if __name__ == '__main__':
    main()
