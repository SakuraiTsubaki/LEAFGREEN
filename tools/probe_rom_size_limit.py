#!/usr/bin/env python3
"""Probe LeafGreen ROM file sizes against the standard 32 MiB GBA ROM window.

This tool can build oversized test files for evidence, but it clearly marks
anything above 32 MiB as not uniquely addressable by standard LeafGreen/GBA
mapping. It never treats a large file as usable ROM capacity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

MIB = 1024 * 1024
STANDARD_MAX_MIB = 32
PROBE_SIZES_MIB = (32, 64, 96, 128)


def sha256_file(path: Path, limit: int | None = None) -> str:
    h = hashlib.sha256()
    remaining = limit
    with path.open("rb") as f:
        while True:
            size = 1024 * 1024 if remaining is None else min(1024 * 1024, remaining)
            if size <= 0:
                break
            chunk = f.read(size)
            if not chunk:
                break
            h.update(chunk)
            if remaining is not None:
                remaining -= len(chunk)
    return h.hexdigest()


def build_probe(source: Path, output: Path, target_mib: int) -> None:
    target = target_mib * MIB
    source_size = source.stat().st_size
    if source_size > target:
        raise SystemExit(f"source is larger than {target_mib} MiB")
    with source.open("rb") as src, output.open("wb") as dst:
        while True:
            chunk = src.read(MIB)
            if not chunk:
                break
            dst.write(chunk)
        remaining = target - source_size
        fill = b"\xFF" * MIB
        while remaining:
            n = min(remaining, len(fill))
            dst.write(fill[:n])
            remaining -= n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("rom", type=Path)
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--report", type=Path)
    args = ap.parse_args()

    source_size = args.rom.stat().st_size
    if source_size != 16 * MIB:
        raise SystemExit(f"expected a 16 MiB LeafGreen source ROM, got {source_size} bytes")
    header = args.rom.read_bytes()[:0xC0]
    if header[0xAC:0xAF] != b"BPG":
        raise SystemExit("not a BPG* LeafGreen ROM")

    out_dir = args.out_dir
    results = []
    for mib in PROBE_SIZES_MIB:
        row = {
            "size_mib": mib,
            "size_bytes": mib * MIB,
            "uniquely_addressable_standard_gba": mib <= STANDARD_MAX_MIB,
        }
        if out_dir is not None:
            out_dir.mkdir(parents=True, exist_ok=True)
            output = out_dir / f"{args.rom.stem} - {mib}MiB probe.gba"
            build_probe(args.rom, output, mib)
            row["output"] = str(output)
            row["sha256"] = sha256_file(output)
            row["first_32m_sha256"] = sha256_file(output, STANDARD_MAX_MIB * MIB)
        results.append(row)

    report = {
        "source": str(args.rom),
        "source_sha256": sha256_file(args.rom),
        "standard_gba_rom_max_mib": STANDARD_MAX_MIB,
        "standard_unique_cpu_range": ["0x08000000", "0x09FFFFFF"],
        "oversize_semantics": (
            "64/96/128 MiB files are probe artifacts only. Standard GBA ROM accesses "
            "fold through a 32 MiB window; extra file bytes require a nonstandard mapper."
        ),
        "results": results,
    }

    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
