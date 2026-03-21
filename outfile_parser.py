#!/usr/bin/env python3
"""
parse_zsim.py
Parses zsim .out files from outputs/hw4/<REPL>/<bench>/ directories
and extracts cycles, IPC, and MPKI for L1i, L1d, and L3 caches.

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
        'l1i_mpki':    mpki(stats['l1i_misses']),
        'l1d_mpki':    mpki(stats['l1d_misses']),
        'l3_mpki':     mpki(stats['l3_misses']),
        'l1i_misses':  stats['l1i_misses'],
        'l1d_misses':  stats['l1d_misses'],
        'l3_misses':   stats['l3_misses'],
    }


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    base_dir = sys.argv[1] if len(sys.argv) > 1 else 'zsim/outputs/hw4'

    if not os.path.isdir(base_dir):
        print(f"ERROR: directory not found: {base_dir}")
        sys.exit(1)

    rows = []

    for repl in sorted(os.listdir(base_dir)):
        repl_dir = os.path.join(base_dir, repl)
        if not os.path.isdir(repl_dir):
            continue

        for bench_dir_name in sorted(os.listdir(repl_dir)):
            bench_path = os.path.join(repl_dir, bench_dir_name)
            if not os.path.isdir(bench_path):
                continue

            # Find the .out file (zsim.out or <bench>.out)
            out_file = None
            for fname in os.listdir(bench_path):
                if fname.endswith('.out'):
                    out_file = os.path.join(bench_path, fname)
                    break

            if out_file is None:
                print(f"  WARNING: no .out file in {bench_path}, skipping")
                continue

            # Strip _8c_simlarge suffix to get a clean benchmark name
            bench_name = bench_dir_name.replace('_8c_simlarge', '')

            try:
                raw   = parse_out_file(out_file)
                metrics = compute_metrics(raw)
                rows.append({
                    'repl':       repl,
                    'bench':      bench_name,
                    **metrics
                })
                print(f"  OK  {repl:8s}  {bench_name:30s}  "
                      f"cycles={metrics['cycles']:>14,}  "
                      f"IPC={metrics['ipc']:.4f}  "
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
        'l3_misses',  'l3_mpki',
    ]
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nResults written to {csv_path}  ({len(rows)} rows)")


if __name__ == '__main__':
    main()