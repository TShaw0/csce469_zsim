#!/usr/bin/env python3
"""
parse_zsim.py
Recursively searches a directory for zsim .out files and extracts
cycles, IPC, and MPKI for L1i, L1d, L2, and L3 caches.

The directory structure is expected to be:
    <base_dir>/<repl>/<bench>/<bench>.out

Usage:
    python3 parse_zsim.py <path_to_hw4_outputs>

Example:
    python3 parse_zsim.py zsim/outputs/hw4
    python3 parse_zsim.py hw4_results/outputs/hw4
"""

import os
import re
import csv
import sys

# ── helpers ──────────────────────────────────────────────────────────────────

def extract_int(text, key):
    """Return the first integer value associated with 'key: <int>' in text."""
    m = re.search(rf'^\s*{re.escape(key)}:\s*(\d+)', text, re.MULTILINE)
    return int(m.group(1)) if m else 0


def parse_out_file(filepath):
    """
    Parse a single zsim .out file.
    Returns a dict with cycles, instrs, and cache miss counts.
    """
    with open(filepath, 'r') as f:
        text = f.read()

    stats = {}

    # ── Core stats (sum across all westmere-N cores) ──────────────────────
    total_cycles  = 0
    total_ccycles = 0
    total_instrs  = 0

    core_blocks = re.findall(
        r'westmere-\d+:.*?(?=westmere-\d+:|l1i:|$)', text, re.DOTALL
    )
    for block in core_blocks:
        total_cycles  += extract_int(block, 'cycles')
        total_ccycles += extract_int(block, 'cCycles')
        total_instrs  += extract_int(block, 'instrs')

    stats['total_cycles'] = total_cycles + total_ccycles
    stats['total_instrs'] = total_instrs

    # ── L1i cache (sum across all l1i-N instances) ────────────────────────
    l1i_mGETS = l1i_mGETXIM = l1i_mGETXSM = 0
    l1i_blocks = re.findall(r'l1i-\d+:.*?(?=l1i-\d+:|l1d:|$)', text, re.DOTALL)
    for block in l1i_blocks:
        l1i_mGETS   += extract_int(block, 'mGETS')
        l1i_mGETXIM += extract_int(block, 'mGETXIM')
        l1i_mGETXSM += extract_int(block, 'mGETXSM')

    stats['l1i_misses'] = l1i_mGETS + l1i_mGETXIM + l1i_mGETXSM

    # ── L1d cache (sum across all l1d-N instances) ────────────────────────
    l1d_mGETS = l1d_mGETXIM = l1d_mGETXSM = 0
    l1d_blocks = re.findall(r'l1d-\d+:.*?(?=l1d-\d+:|l2:|$)', text, re.DOTALL)
    for block in l1d_blocks:
        l1d_mGETS   += extract_int(block, 'mGETS')
        l1d_mGETXIM += extract_int(block, 'mGETXIM')
        l1d_mGETXSM += extract_int(block, 'mGETXSM')

    stats['l1d_misses'] = l1d_mGETS + l1d_mGETXIM + l1d_mGETXSM

    # ── L2 cache (sum across all l2-N instances) ──────────────────────────
    l2_mGETS = l2_mGETXIM = l2_mGETXSM = 0
    l2_blocks = re.findall(r'l2-\d+:.*?(?=l2-\d+:|l3:|$)', text, re.DOTALL)
    for block in l2_blocks:
        l2_mGETS   += extract_int(block, 'mGETS')
        l2_mGETXIM += extract_int(block, 'mGETXIM')
        l2_mGETXSM += extract_int(block, 'mGETXSM')

    stats['l2_misses'] = l2_mGETS + l2_mGETXIM + l2_mGETXSM

    # ── L3 cache: two formats ─────────────────────────────────────────────
    #   PARSEC: l3-0b0 .. l3-0b7  (8 banks)
    #   SPEC:   l3-0              (single bank, no 'b')
    l3_mGETS = l3_mGETXIM = l3_mGETXSM = 0

    # Try banked format first
    l3_blocks = re.findall(r'l3-0b\d+:.*?(?=l3-0b\d+:|mem:|$)', text, re.DOTALL)
    if not l3_blocks:
        # Fall back to single-bank format
        l3_blocks = re.findall(r'l3-\d+:.*?(?=l3-\d+:|mem:|$)', text, re.DOTALL)

    for block in l3_blocks:
        l3_mGETS   += extract_int(block, 'mGETS')
        l3_mGETXIM += extract_int(block, 'mGETXIM')
        l3_mGETXSM += extract_int(block, 'mGETXSM')

    stats['l3_misses'] = l3_mGETS + l3_mGETXIM + l3_mGETXSM

    return stats


def compute_metrics(stats):
    """Derive cycles, IPC, and MPKI values from raw stats."""
    cycles = stats['total_cycles']
    instrs = stats['total_instrs']

    ipc = instrs / cycles if cycles > 0 else 0.0

    def mpki(misses):
        return (misses / instrs * 1000) if instrs > 0 else 0.0

    return {
        'cycles':      cycles,
        'instrs':      instrs,
        'ipc':         ipc,
        'l1i_misses':  stats['l1i_misses'],
        'l1i_mpki':    mpki(stats['l1i_misses']),
        'l1d_misses':  stats['l1d_misses'],
        'l1d_mpki':    mpki(stats['l1d_misses']),
        'l2_misses':   stats['l2_misses'],
        'l2_mpki':     mpki(stats['l2_misses']),
        'l3_misses':   stats['l3_misses'],
        'l3_mpki':     mpki(stats['l3_misses']),
    }


def find_out_files(base_dir):
    """
    Recursively walk base_dir and yield (repl, bench, filepath) tuples
    for every .out file found. Infers repl and bench from the path:
        <base_dir>/<repl>/<bench_dir>/<anything>.out
    """
    for dirpath, dirnames, filenames in os.walk(base_dir):
        dirnames.sort()  # walk in alphabetical order
        for fname in sorted(filenames):
            if not fname.endswith('.out'):
                continue

            filepath = os.path.join(dirpath, fname)

            # Compute path relative to base_dir and split into parts
            rel = os.path.relpath(dirpath, base_dir)
            parts = rel.split(os.sep)

            if len(parts) < 2:
                # .out file is too shallow — skip
                continue

            repl      = parts[0]
            bench_dir = parts[1]
            bench     = bench_dir.replace('_8c_simlarge', '')

            yield repl, bench, filepath


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    base_dir = sys.argv[1] if len(sys.argv) > 1 else 'zsim/outputs/hw4'

    if not os.path.isdir(base_dir):
        print(f"ERROR: directory not found: {base_dir}")
        sys.exit(1)

    rows = []

    for repl, bench, out_file in find_out_files(base_dir):
        try:
            raw     = parse_out_file(out_file)
            metrics = compute_metrics(raw)
            rows.append({
                'repl':  repl,
                'bench': bench,
                **metrics
            })
            print(f"  OK  {repl:8s}  {bench:30s}  "
                  f"cycles={metrics['cycles']:>14,}  "
                  f"IPC={metrics['ipc']:.4f}  "
                  f"L2_MPKI={metrics['l2_mpki']:.4f}  "
                  f"L3_MPKI={metrics['l3_mpki']:.4f}")
        except Exception as e:
            print(f"  ERROR parsing {out_file}: {e}")

    if not rows:
        print("No data collected — check the base directory path.")
        sys.exit(1)

    # ── Write CSV ─────────────────────────────────────────────────────────
    csv_path = 'zsim_results.csv'
    fieldnames = [
        'repl', 'bench',
        'cycles', 'instrs', 'ipc',
        'l1i_misses', 'l1i_mpki',
        'l1d_misses', 'l1d_mpki',
        'l2_misses',  'l2_mpki',
        'l3_misses',  'l3_mpki',
    ]
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nResults written to {csv_path}  ({len(rows)} rows)")


if __name__ == '__main__':
    main()