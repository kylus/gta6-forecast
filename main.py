"""Hour-by-hour forecast of a game launch's Twitch viewers for make.fun's gta6-twitch-ccu-forecast-01.

For each case in the input directory it reads hour 1's count and the past launches the case carries,
turns each launch's release day into ratios of its hours 2..24 to its own hour 1, and writes the five
quantiles of every hour as hour 1's count times a weighted mixture of those ratios. Launches that
unrolled like the target (consoles, midnight local, rolling) weigh most; the mixture is smoothed and
widened, and blended with a random walk so a thin analogue set cannot make it overconfident.
Standard library only; it reads no clock and no random source.
"""
import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.6448536269514722, -0.6744897501960817, 0.0, 0.6744897501960817, 1.6448536269514722]

# Tuned by leave-one-launch-out on the comparables (tools/loo.py); see README.
PARAMS = {
    'bandwidth': 0.30,   # log-scale smoothing of each analogue's ratio
    'widen': 1.0,        # spread of the analogue mixture around its median, as a multiple
    'walk': 0.15,        # random-walk sigma per sqrt(hour) of the fallback component
    'walk_share': 0.35,  # weight of the random walk in the final mixture
    'size_width': 1.0,   # kernel width on log(hour 1 count): big launches behave like big launches (0: off)
    'mom_width': 0.8,    # kernel width on the momentum feature (0: off)
}


def parse_time(text):
    return datetime.fromisoformat(text.replace('Z', '+00:00')).astimezone(timezone.utc)


def weight_of(c):
    """How much a past launch resembles a rolling, midnight-local console release."""
    text = (c.get('unlock') or '').lower()
    name = (c.get('name') or '').lower()
    if 'grand theft auto vi category' in name or 'target-history' in text:
        return 0.0
    w = 0.5
    if 'midnight local' in text or 'rolling' in text:
        w = 1.0
    elif 'simultaneous' in text or 'single global' in text or 'single time' in text or 'pc only' in text:
        w = 0.1
    if 'tier: weak' in text:
        w *= 0.2
    if 'early-access-contaminated' in text:
        w *= 0.4
    return w


def persistence(p, h):
    return [p * math.exp(z * 0.15 * math.sqrt(h - 1)) for z in Z]


def norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def mixture_quantile(points, tau):
    """Quantile of a weighted mixture of normals (centre, sigma, weight) by bisection."""
    lo = min(c - 8 * s for c, s, _ in points)
    hi = max(c + 8 * s for c, s, _ in points)
    total = sum(w for _, _, w in points)
    for _ in range(60):
        mid = (lo + hi) / 2
        cdf = sum(w * norm_cdf((mid - c) / s) for c, s, w in points) / total
        if cdf < tau:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def day_hours(c):
    ds = parse_time(c['day_start'])
    m = {parse_time(x['from']): x['viewers'] for x in c['hourly']}
    return [m.get(ds + timedelta(hours=h)) for h in range(24)]


def momentum(hourly_by_time, ds, p1):
    """log of hour 1 over the mean of the six hours before the day: how steeply the day starts rising."""
    prev = [hourly_by_time.get(ds - timedelta(hours=i)) for i in range(1, 7)]
    prev = [v for v in prev if v is not None and v > 0]
    if len(prev) < 3 or p1 <= 0:
        return None
    return math.log(p1 / (sum(prev) / len(prev)))


def forecast(p1, comparables, params=None, target_momentum=None):
    """Rows of five quantiles for hours 2..24 given hour 1's print and the comparable launches."""
    k = dict(PARAMS)
    if params:
        k.update(params)
    p1 = max(float(p1), 1.0)
    days = []
    for c in comparables:
        w = weight_of(c)
        ys = day_hours(c)
        if w > 0 and ys[0] is not None and ys[0] > 0:
            if target_momentum is not None and k['mom_width'] > 0:
                ds = parse_time(c['day_start'])
                m = momentum({parse_time(x['from']): x['viewers'] for x in c['hourly']}, ds, ys[0])
                if m is not None:
                    w *= math.exp(-((m - target_momentum) ** 2) / (2 * k['mom_width'] ** 2))
            if k['size_width'] > 0:
                w *= math.exp(-((math.log(ys[0]) - math.log(p1)) ** 2) / (2 * k['size_width'] ** 2))
            days.append((w, ys))
    out = []
    for h in range(2, 25):
        pts = []
        for w, ys in days:
            y = ys[h - 1]
            if y is not None and y > 0:
                pts.append((math.log(y / ys[0]), w))
        walk_sigma = k['walk'] * math.sqrt(h - 1)
        if len(pts) < 3:
            out.append(persistence(p1, h))
            continue
        wsum = sum(w for _, w in pts)
        centre = mixture_quantile([(x, k['bandwidth'], w) for x, w in pts], 0.5)
        comps = [(centre + (x - centre) * k['widen'], k['bandwidth'] * k['widen'], w * (1 - k['walk_share']) / wsum) for x, w in pts]
        comps.append((0.0 if k.get('walk_centre') is None else k['walk_centre'], walk_sigma, k['walk_share']))
        row = [p1 * math.exp(mixture_quantile(comps, tau)) for tau in LEVELS]
        for i in range(1, 5):
            row[i] = max(row[i], row[i - 1])
        out.append(row)
    return out


def main():
    in_dir = os.environ.get('MAKEFUN_INPUT_DIR', '/input')
    out_dir = os.environ.get('MAKEFUN_OUTPUT_DIR', '/output')
    os.makedirs(out_dir, exist_ok=True)
    for name in sorted(os.listdir(in_dir)):
        if not name.endswith('.in'):
            continue
        case = json.load(open(os.path.join(in_dir, name), encoding='utf-8'))
        known = next(k for k in case['known'] if k['hour'] == 1)
        ds = parse_time(case['day_start'])
        hist = {parse_time(x['from']): x['viewers'] for x in case['history_hourly']}
        rows = forecast(known['viewers'], case['comparables'], None, momentum(hist, ds, known['viewers']))
        hours = [{'hour': h, 'q': [round(min(max(q, 0.01), 1e9), 2) for q in row]} for h, row in zip(range(2, 25), rows)]
        with open(os.path.join(out_dir, name[:-3] + '.out'), 'w', encoding='utf-8') as f:
            json.dump({'hours': hours}, f, separators=(',', ':'))


if __name__ == '__main__':
    main()
