#!/usr/bin/env python3
"""Analyze a Saleae digital edge CSV of SCLK_0 against the H6 calibration spec.

Usage:  python3 h6_sclk_analyze.py <file.csv> [--channel "Channel 1"]

Handles both transition-style exports (one row per edge) and sampled exports
(consecutive identical rows are collapsed).

For every long command pulse (high width in 80..200 us by default) it reports:
  - high width in us
  - low wait: fall of the long pulse -> next rising edge (first short clock)
  - number of short clocks after the pulse, and byte-group boundaries
  - short clock period statistics

Acceptance (GTRY164 V1.9 section 7.8):
  td10 = 128 us +/-5%  -> 121.6 .. 134.4 us
  td12 > 50 us
  32 short clocks per transaction (2 chips x 16 bits)
"""

import argparse
import csv
import statistics
import sys

LONG_MIN_US = 80.0
LONG_MAX_US = 200.0
TD10_MIN_US = 121.6
TD10_MAX_US = 134.4
TD12_MIN_US = 50.0
EXPECTED_CLOCKS = 32
CLOCK_PERIOD_NOMINAL_US = 0.5  # 2 MHz


def load_edges(path, channel=None):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.reader(fh))
    if not rows:
        raise SystemExit("empty csv")
    header = [c.strip() for c in rows[0]]
    if len(header) < 2:
        raise SystemExit(f"unexpected header: {header}")
    # Pick the requested channel, else the first non-time column.
    if channel is None:
        ch_idx = 1
    else:
        try:
            ch_idx = header.index(channel)
        except ValueError:
            raise SystemExit(f"channel {channel!r} not in header {header}")

    edges = []
    for row in rows[1:]:
        if len(row) <= ch_idx:
            continue
        try:
            t = float(row[0])
            v = int(float(row[ch_idx]))
        except ValueError:
            continue
        edges.append((t, v))

    # Collapse sampled exports to true transitions.
    out = []
    for t, v in edges:
        if out and out[-1][1] == v:
            continue
        out.append((t, v))
    return header[ch_idx], out


def analyze(edges, long_min_us=LONG_MIN_US, long_max_us=LONG_MAX_US):
    """Return list of dicts, one per long command pulse."""
    # Rising/falling indexes
    rises = [i for i, (_, v) in enumerate(edges) if v == 1]
    falls = [i for i, (_, v) in enumerate(edges) if v == 0]
    results = []

    for fi in falls:
        t_fall = edges[fi][0]
        # Find the most recent rising edge that started this high phase.
        prev_rises = [ri for ri in rises if ri < fi]
        if not prev_rises:
            continue
        ri = prev_rises[-1]
        t_rise = edges[ri][0]
        high_us = (t_fall - t_rise) * 1e6
        if not (long_min_us <= high_us <= long_max_us):
            continue

        # Low wait to the first following rising edge.
        next_rises = [x for x in rises if x > fi]
        low_wait_us = None
        if next_rises:
            low_wait_us = (edges[next_rises[0]][0] - t_fall) * 1e6

        # Collect short clocks until the next long high phase (>= LONG_MIN_US).
        clocks = []
        periods = []
        for idx in next_rises:
            t = edges[idx][0]
            # stop if this rising edge begins another long pulse
            nf = [x for x in falls if x > idx]
            if nf:
                nfi = nf[0]
                w = (edges[nfi][0] - t) * 1e6
                if w >= long_min_us:
                    break
            clocks.append(t)
            if len(clocks) >= 2:
                periods.append((clocks[-1] - clocks[-2]) * 1e6)

        # Separate within-byte clocks from between-byte gaps. The shortest
        # period is the true clock period (gaps are always longer).
        within = []
        gaps = []
        if periods:
            base = min(periods)
            for (a, b), gap in zip(zip(clocks[:-1], clocks[1:]), periods):
                if gap <= base * 1.6:
                    within.append(gap)
                else:
                    gaps.append((a, gap))

        results.append({
            "rise_us": t_rise * 1e6,
            "fall_us": t_fall * 1e6,
            "high_us": high_us,
            "low_wait_us": low_wait_us,
            "clocks": len(clocks),
            "periods": within,
            "gaps": gaps,
        })
    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--channel", default=None)
    ap.add_argument("--long-min", type=float, default=LONG_MIN_US,
                    help="min high width (us) treated as a command pulse")
    ap.add_argument("--long-max", type=float, default=LONG_MAX_US,
                    help="max high width (us) treated as a command pulse")
    ap.add_argument("--target-us", type=float, default=128.0,
                    help="nominal high width for the verdict (default 128)")
    ap.add_argument("--tol-pct", type=float, default=5.0,
                    help="allowed +/- percent around the target (default 5)")
    ap.add_argument("--low-min", type=float, default=50.0,
                    help="minimum low wait in us for the verdict (default 50)")
    args = ap.parse_args()

    name, edges = load_edges(args.csv, args.channel)
    if not edges:
        raise SystemExit("no edges parsed")

    results = analyze(edges, args.long_min, args.long_max)
    if not results:
        raise SystemExit(
            "no long command pulse found; check channel, trigger window and "
            f"that the file contains {LONG_MIN_US:.0f}-{LONG_MAX_US:.0f} us highs"
        )

    print(f"file      : {args.csv}")
    print(f"channel   : {name}")
    print(f"edges     : {len(edges)}   pulses: {len(results)}")
    print()

    hdr = f"{'#':>2} {'high_us':>9} {'low_us':>8} {'clocks':>7} {'period_us':>9}"
    print(hdr)
    print("-" * len(hdr))
    all_periods = []
    for i, r in enumerate(results, 1):
        per = f"{statistics.median(r['periods']):.4f}" if r["periods"] else "-"
        low = f"{r['low_wait_us']:.4f}" if r["low_wait_us"] is not None else "n/a"
        print(f"{i:>2} {r['high_us']:>9.4f} {low:>8} {r['clocks']:>7} {per:>9}")
        all_periods.extend(r["periods"])

    highs = [r["high_us"] for r in results]
    lows = [r["low_wait_us"] for r in results if r["low_wait_us"] is not None]
    print()
    print(f"high  : first={highs[0]:.4f}  mean={statistics.mean(highs):.4f}  "
          f"min={min(highs):.4f}  max={max(highs):.4f}  "
          f"spread={max(highs) - min(highs):.4f} us")
    if len(highs) > 1:
        rest = highs[1:]
        print(f"        first-vs-rest diff = {highs[0] - statistics.mean(rest):+.4f} us")
    lo_t = args.target_us * (1.0 - args.tol_pct / 100.0)
    hi_t = args.target_us * (1.0 + args.tol_pct / 100.0)
    print(f"target: {args.target_us:.2f} us   allowed {lo_t:.2f}-{hi_t:.2f} us   "
          f"dev_from_target mean={statistics.mean(highs) - args.target_us:+.4f} us")
    if lows:
        print(f"low   : first={lows[0]:.4f}  mean={statistics.mean(lows):.4f}  "
              f"min={min(lows):.4f}  max={max(lows):.4f}  (need > {args.low_min})")
    if all_periods:
        print(f"clock : mean period={statistics.mean(all_periods):.4f} us "
              f"({1.0 / statistics.mean(all_periods):.2f} MHz)  "
              f"min={min(all_periods):.4f}  max={max(all_periods):.4f}")
    counts = {r["clocks"] for r in results}
    print(f"clocks per pulse set: {sorted(counts)}  (expected {EXPECTED_CLOCKS})")

    ok_high = all(lo_t <= h <= hi_t for h in highs)
    ok_low = all(l > args.low_min for l in lows) if lows else False
    ok_clocks = all(r["clocks"] == EXPECTED_CLOCKS for r in results)
    print()
    print(f"VERDICT: width {'PASS' if ok_high else 'FAIL'}  "
          f"low_wait {'PASS' if ok_low else 'FAIL'}  "
          f"clock_count {'PASS' if ok_clocks else 'FAIL'}")
    return 0 if (ok_high and ok_low and ok_clocks) else 1


if __name__ == "__main__":
    sys.exit(main())
