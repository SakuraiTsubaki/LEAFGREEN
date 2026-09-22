#!/usr/bin/env python3
"""Pack build-time relocation blocks into LeafGreen's upper 16 MiB ROM arena.

This planner never modifies a ROM. It prevents static/speculative partitioning:
callers provide the real built block sizes and alignments, and the tool returns
file offsets and GBA ROM addresses while enforcing the 32 MiB hard limit.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROM_BASE = 0x08000000
DEFAULT_START = 0x01000000
DEFAULT_END = 0x02000000


def parse_int(value: int | str) -> int:
    if isinstance(value, int):
        return value
    return int(value, 0)


def align_up(value: int, alignment: int) -> int:
    if alignment <= 0 or alignment & (alignment - 1):
        raise ValueError(f"alignment must be a power of two: {alignment}")
    return (value + alignment - 1) & ~(alignment - 1)


def plan(spec: dict) -> dict:
    arena = spec.get("arena", {})
    start = parse_int(arena.get("start", DEFAULT_START))
    end = parse_int(arena.get("end_exclusive", DEFAULT_END))
    if not (DEFAULT_START <= start < end <= DEFAULT_END):
        raise ValueError("allocation arena must stay inside file 0x1000000..0x1FFFFFF")

    blocks = spec.get("blocks", [])
    names: set[str] = set()
    cursor = start
    allocations = []

    for block in blocks:
        name = block["name"]
        if name in names:
            raise ValueError(f"duplicate block name: {name}")
        names.add(name)

        size = parse_int(block["size"])
        alignment = parse_int(block.get("alignment", 4))
        if size <= 0:
            raise ValueError(f"{name}: size must be positive")

        cursor = align_up(cursor, alignment)
        block_end = cursor + size
        if block_end > end:
            raise ValueError(
                f"{name}: allocation exceeds 32 MiB ROM limit "
                f"(end 0x{block_end:X} > 0x{end:X})"
            )

        allocations.append({
            "name": name,
            "kind": block.get("kind", "data"),
            "file_offset": f"0x{cursor:08X}",
            "file_end_exclusive": f"0x{block_end:08X}",
            "rom_address": f"0x{ROM_BASE + cursor:08X}",
            "rom_end_exclusive": f"0x{ROM_BASE + block_end:08X}",
            "size": size,
            "alignment": alignment,
            "source": block.get("source"),
        })
        cursor = block_end

    used = cursor - start
    return {
        "schema_version": 1,
        "arena": {
            "start": f"0x{start:08X}",
            "end_exclusive": f"0x{end:08X}",
            "bytes": end - start,
        },
        "allocations": allocations,
        "used_bytes": used,
        "remaining_bytes": end - cursor,
        "next_free_offset": f"0x{cursor:08X}",
        "policy": (
            "planning only; allocation does not imply that reference rewrite "
            "or runtime validation is complete"
        ),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    result = plan(json.loads(args.spec.read_text(encoding="utf-8")))
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
