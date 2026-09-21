#!/usr/bin/env python3
"""Expand a supported Pokémon LeafGreen ROM from 16 MiB to 32 MiB.

This is the physical-space foundation for later generation-table relocation.
It does not alter gameplay tables, IDs, save data, or form-change mechanics.
The original 16 MiB is preserved byte-for-byte and the new half is filled with
0xFF.

Both verified clean ROMs and this repository's verified 16 MiB
Always-On-External-Events outputs are accepted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROM_MANIFEST = ROOT / "manifests" / "leafgreen_roms.json"
CAPACITY_MANIFEST = ROOT / "manifests" / "generation_capacity.json"

MIB = 1024 * 1024


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_supported_hashes() -> dict[str, str]:
    data = json.loads(ROM_MANIFEST.read_text(encoding="utf-8"))
    supported: dict[str, str] = {}
    for rom in data["roms"]:
        supported[rom["sha256_original"]] = f'{rom["file"]} clean'
        supported[rom["sha256_patched"]] = f'{rom["file"]} external-events patched'
    return supported


def load_sizes() -> tuple[int, int, int]:
    data = json.loads(CAPACITY_MANIFEST.read_text(encoding="utf-8"))
    policy = data["policy"]
    current = int(policy["current_rom_size_bytes"])
    expanded = int(policy["expanded_rom_size_bytes"])
    fill = int(policy["expansion_fill_byte"], 16)
    return current, expanded, fill


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("rom", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    ap.add_argument("--report", type=Path)
    args = ap.parse_args()

    current_size, expanded_size, fill_byte = load_sizes()
    supported = load_supported_hashes()
    data = args.rom.read_bytes()

    if data[0xAC:0xAF] != b"BPG":
        raise SystemExit("not a Pokémon LeafGreen BPG* ROM")

    if len(data) == current_size:
        lower = data
        upper = b""
    elif len(data) == expanded_size:
        lower = data[:current_size]
        upper = data[current_size:]
        if upper != bytes((fill_byte,)) * (expanded_size - current_size):
            raise SystemExit(
                "32 MiB input already contains data in the expansion region; "
                "refusing to overwrite it"
            )
    else:
        raise SystemExit(
            f"unsupported ROM size: {len(data)} bytes "
            f"(expected {current_size} or {expanded_size})"
        )

    base_digest = sha256(lower)
    if base_digest not in supported:
        raise SystemExit(f"unsupported 16 MiB base SHA-256: {base_digest}")

    if len(data) == expanded_size:
        expanded = data
        already_expanded = True
    else:
        expanded = lower + bytes((fill_byte,)) * (expanded_size - current_size)
        already_expanded = False

    output = args.output or args.rom.with_name(args.rom.stem + " - 32MiB.gba")
    output.write_bytes(expanded)

    report = {
        "input": str(args.rom),
        "input_size": len(data),
        "base_variant": supported[base_digest],
        "base_16m_sha256": base_digest,
        "output": str(output),
        "output_size": len(expanded),
        "output_sha256": sha256(expanded),
        "already_expanded": already_expanded,
        "preserved_prefix_bytes": current_size,
        "new_region": {
            "file_offset_start": "0x1000000",
            "file_offset_end_exclusive": "0x2000000",
            "gba_rom_address_start": "0x09000000",
            "gba_rom_address_end_exclusive": "0x0A000000",
            "fill_byte": f"0x{fill_byte:02X}",
        },
        "gameplay_tables_relocated": False,
        "form_change_mechanics": "deferred",
    }

    if args.report:
        args.report.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
