"""Leave-one-launch-out scoring of the forecast model on the comparables of a case file.

Each comparable that has a full release day becomes a test case: its hour 1 is the known print, its hours
2..24 the answer, and the model sees every other comparable. The same pinball loss as the contest's.
usage: python3 tools/loo.py <case.in> [json params]
"""
import json
import math
import sys
from datetime import datetime, timedelta

sys.path.insert(0, '.')
import main as model  # noqa: E402

FLOOR = 0.15  # test only launches whose hour 1 is already a real share of the day's peak, as GTA VI's will be
LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]


def pinball(y, qs):
    total = 0.0
    for tau, q in zip(LEVELS, qs):
        d = math.log(max(y, 1)) - math.log(q)
        total += 2 * max(tau * d, (tau - 1) * d)
    return total / 5


def day(c):
    ds = model.parse_time(c['day_start'])
    m = {model.parse_time(x['from']): x['viewers'] for x in c['hourly']}
    return [m.get(ds + timedelta(hours=h)) for h in range(24)]


def run(path, params=None, verbose=False, only=None):
    case = json.load(open(path))
    comps = case['comparables']
    rows = []
    for i, c in enumerate(comps):
        ys = day(c)
        if ys[0] is None or sum(v is not None for v in ys) < 20 or 'Grand Theft' in c['name']:
            continue
        if only is not None and model.weight_of(c) < only:
            continue
        if min(1.0, ys[0] / max(v for v in ys if v)) < FLOOR:
            continue
        others = comps[:i] + comps[i + 1:]
        ds = model.parse_time(c['day_start'])
        tm = model.momentum({model.parse_time(x['from']): x['viewers'] for x in c['hourly']}, ds, ys[0])
        fc = model.forecast(ys[0], others, params, tm)
        losses = [pinball(ys[h], fc[h - 1]) for h in range(1, 24) if ys[h] is not None]
        base = [pinball(ys[h], model.persistence(ys[0], h + 1)) for h in range(1, 24) if ys[h] is not None]
        rows.append((c['name'][:30], sum(losses) / len(losses), sum(base) / len(base)))
    if verbose:
        for r in rows:
            print(f'{r[0]:32s} model {r[1]:.3f}  persist {r[2]:.3f}')
    n = len(rows)
    return sum(r[1] for r in rows) / n, sum(r[2] for r in rows) / n, n


if __name__ == '__main__':
    p = json.loads(sys.argv[2]) if len(sys.argv) > 2 else None
    print(run(sys.argv[1], p, verbose=True, only=0.5))
