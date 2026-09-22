#!/usr/bin/env python3
"""Audit aligned ROM references into known LeafGreen core-table ranges.

This is a relocation-preparation tool, not a binary patcher. It combines the
per-ROM GFRomHeader table bases with source-derived retail table sizes and scans
4-byte-aligned ROM words for values that point to a table base or interior.

The hits are relocation candidates. They still need instruction/data/literal
classification before rewriting.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import json
import struct
from pathlib import Path

from extract_leafgreen_core_tables import extract

ROM_BASE = 0x08000000

# Source-derived retail shapes at pret/pokefirered
# c75f352304d529f6ba92d4f74b9cf8b5c3810788.
#
# SpeciesInfo: 412 entries, 26-byte struct
# Ability names: 78 * 13 bytes
# Ability descriptions: 78 pointers
# Items: 375 entries, 44-byte GBA ABI struct
# Battle moves: 355 entries, 9-byte struct
# Species names: 412 * 11 bytes
# Move names: 355 * 13 bytes
# Evolutions: 412 species * 5 entries * 8-byte retail ABI stride
TABLE_SHAPES = {
    "speciesInfo": (412, 26),
    "abilityNames": (78, 13),
    "abilityDescriptions": (78, 4),
    "items": (375, 44),
    "moves": (355, 9),
    "monSpeciesNames": (412, 11),
    "moveNames": (355, 13),
    "evolutionTable": (412, 40),
}


def audit(path: Path) -> dict:
    data = path.read_bytes()
    extracted = extract(path)

    ranges = []
    for name, (count, stride) in TABLE_SHAPES.items():
        start = int(extracted["tables"][name]["offset"], 16)
        size = count * stride
        ranges.append((start, start + size, name, count, stride))
    ranges.sort()
    starts = [row[0] for row in ranges]

    refs: dict[str, list[tuple[int, int]]] = {
        name: [] for name in TABLE_SHAPES
    }

    for location in range(0, len(data) - 3, 4):
        value = struct.unpack_from("<I", data, location)[0]
        if not (ROM_BASE <= value < ROM_BASE + len(data)):
            continue

        target = value - ROM_BASE
        idx = bisect.bisect_right(starts, target) - 1
        if idx < 0:
            continue

        start, end, name, _count, _stride = ranges[idx]
        if target < end:
            refs[name].append((location, target - start))

    result = {
        "file": path.name,
        "sha256": extracted["sha256"],
        "game_code": extracted["game_code"],
        "revision": extracted["revision"],
        "tables": {},
    }

    for start, end, name, count, stride in ranges:
        hits = refs[name]
        result["tables"][name] = {
            "offset": f"0x{start:08X}",
            "size": end - start,
            "count": count,
            "stride": stride,
            "aligned_candidate_reference_count": len(hits),
            "base_reference_count": sum(1 for _, rel in hits if rel == 0),
            "interior_reference_count": sum(1 for _, rel in hits if rel != 0),
            "unique_target_offsets": len({rel for _, rel in hits}),
            "candidate_reference_offsets": [
                {
                    "location": f"0x{location:08X}",
                    "target_relative": f"0x{relative:08X}",
                }
                for location, relative in hits
            ],
        }

    return result


def write_csv(report: dict, output: Path) -> None:
    fields = [
        "file", "game_code", "revision", "table", "offset", "size",
        "count", "stride", "aligned_candidate_reference_count",
        "base_reference_count", "interior_reference_count",
        "unique_target_offsets",
    ]
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for profile in report["profiles"]:
            for table, info in profile["tables"].items():
                writer.writerow({
                    "file": profile["file"],
                    "game_code": profile["game_code"],
                    "revision": profile["revision"],
                    "table": table,
                    "offset": info["offset"],
                    "size": info["size"],
                    "count": info["count"],
                    "stride": info["stride"],
                    "aligned_candidate_reference_count":
                        info["aligned_candidate_reference_count"],
                    "base_reference_count": info["base_reference_count"],
                    "interior_reference_count": info["interior_reference_count"],
                    "unique_target_offsets": info["unique_target_offsets"],
                })


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("rom", nargs="+", type=Path)
    ap.add_argument("--output", type=Path, help="full JSON report")
    ap.add_argument("--csv", type=Path, help="compact CSV summary")
    args = ap.parse_args()

    report = {
        "schema_version": 1,
        "classification": (
            "4-byte-aligned address-range hits are relocation candidates, "
            "not automatically safe rewrite sites"
        ),
        "source_reference": {
            "repository": "pret/pokefirered",
            "commit": "c75f352304d529f6ba92d4f74b9cf8b5c3810788",
        },
        "profiles": [audit(path) for path in args.rom],
    }

    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    if args.csv:
        write_csv(report, args.csv)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
