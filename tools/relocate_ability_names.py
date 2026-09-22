#!/usr/bin/env python3
"""Relocate the retail ability-name table into LeafGreen's upper 16 MiB.

This is the first conservative binary relocation step for the Generation 10
capacity layer. The original table is deliberately preserved as a compatibility
fallback. Only four verified base-pointer sites are rewritten:

- the GFRomHeader pointer at file offset 0x1C0;
- three literal-pool words, each proven to have exactly one Thumb LDR-literal
  consumer in every supported retail profile.

The table has no aligned interior reference candidates in any of the seven
audited ROMs. Runtime emulator validation is still a separate requirement.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

from expand_rom_capacity import (
    EXPANDED_ROM_SIZE,
    GF_HEADER_OFFSET,
    ROM_SIZE,
    SAVE_SIZE,
    choose_active_slot,
    load_supported_rom_hashes,
    u32,
    validate_save_slot,
)
from extract_leafgreen_core_tables import extract

ROOT = Path(__file__).resolve().parents[1]
RELOCATION_PLAN = ROOT / "manifests" / "retail_core_relocation_plan.json"

ROM_BASE = 0x08000000
ABILITY_NAMES_SIZE = 78 * 13


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def find_all(data: bytes, needle: bytes) -> list[int]:
    hits: list[int] = []
    start = 0
    while True:
        hit = data.find(needle, start)
        if hit < 0:
            return hits
        hits.append(hit)
        start = hit + 1


def thumb_ldr_users(data: bytes, literal_offset: int) -> list[dict]:
    users = []
    for offset in range(max(0, literal_offset - 1024), literal_offset, 2):
        opcode = struct.unpack_from("<H", data, offset)[0]
        if opcode & 0xF800 != 0x4800:
            continue

        immediate = (opcode & 0xFF) * 4
        pc = (ROM_BASE + offset + 4) & ~3
        if pc + immediate == ROM_BASE + literal_offset:
            users.append({
                "instruction_offset": f"0x{offset:08X}",
                "opcode": f"0x{opcode:04X}",
                "register": (opcode >> 8) & 7,
            })
    return users


def target_offset_from_plan() -> int:
    plan = json.loads(RELOCATION_PLAN.read_text(encoding="utf-8"))
    row = next(
        allocation
        for allocation in plan["allocations"]
        if allocation["name"] == "abilityNames"
    )
    return int(row["file_offset"], 16)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("rom", type=Path)
    ap.add_argument("save", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    ap.add_argument("--report", type=Path)
    args = ap.parse_args()

    raw = args.rom.read_bytes()
    save = args.save.read_bytes()

    if len(save) != SAVE_SIZE:
        raise SystemExit("save must be 128 KiB")
    if len(raw) not in (ROM_SIZE, EXPANDED_ROM_SIZE):
        raise SystemExit("ROM must be 16 or 32 MiB")

    lower = raw[:ROM_SIZE]
    supported = load_supported_rom_hashes()
    base_digest = sha256(lower)
    if base_digest not in supported:
        raise SystemExit(f"unsupported ROM base SHA-256: {base_digest}")

    save_block_2_size = u32(lower, GF_HEADER_OFFSET + 0x88)
    save_block_1_header_size = u32(lower, GF_HEADER_OFFSET + 0x8C)
    candidates: list[int] = []
    for size in (save_block_1_header_size, 0x3D68):
        if size not in candidates:
            candidates.append(size)
    slots = [
        validate_save_slot(save, slot, save_block_2_size, candidates)
        for slot in range(2)
    ]
    active = choose_active_slot(slots)

    extracted = extract(args.rom)
    old_offset = int(extracted["tables"]["abilityNames"]["offset"], 16)
    old_pointer = ROM_BASE + old_offset
    old_table = lower[old_offset:old_offset + ABILITY_NAMES_SIZE]

    refs = find_all(lower, struct.pack("<I", old_pointer))
    if len(refs) != 4 or 0x1C0 not in refs:
        raise SystemExit(
            "unexpected abilityNames pointer sites: "
            + ", ".join(f"0x{x:X}" for x in refs)
        )

    literal_users: dict[str, list[dict]] = {}
    for ref in refs:
        if ref == 0x1C0:
            continue
        users = thumb_ldr_users(lower, ref)
        if len(users) != 1:
            raise SystemExit(
                f"literal 0x{ref:X} has {len(users)} Thumb LDR-literal consumers"
            )
        literal_users[f"0x{ref:08X}"] = users

    target_offset = target_offset_from_plan()
    target_pointer = ROM_BASE + target_offset

    expanded = bytearray(
        raw if len(raw) == EXPANDED_ROM_SIZE else raw + b"\xFF" * ROM_SIZE
    )
    target = expanded[target_offset:target_offset + ABILITY_NAMES_SIZE]
    if any(byte != 0xFF for byte in target):
        raise SystemExit("target relocation range is not blank")

    expanded[target_offset:target_offset + ABILITY_NAMES_SIZE] = old_table

    new_pointer_bytes = struct.pack("<I", target_pointer)
    for ref in refs:
        expanded[ref:ref + 4] = new_pointer_bytes

    if expanded[target_offset:target_offset + ABILITY_NAMES_SIZE] != old_table:
        raise SystemExit("relocated table differs from source table")
    if find_all(expanded[:ROM_SIZE], struct.pack("<I", old_pointer)):
        raise SystemExit("old abilityNames pointer remains in lower ROM")

    new_refs = find_all(expanded, new_pointer_bytes)
    if sorted(new_refs) != sorted(refs):
        raise SystemExit(
            "new abilityNames pointer sites differ from the verified four sites"
        )

    output = args.output or args.rom.with_name(
        args.rom.stem + " - Gen10 AbilityNames Relocated.gba"
    )
    output.write_bytes(expanded)

    report = {
        "input": str(args.rom),
        "variant": supported[base_digest],
        "base_16m_sha256": base_digest,
        "save_sha256": sha256(save),
        "active_save_slot": active["slot"],
        "active_save_counter": active["counter"],
        "source": {
            "offset": f"0x{old_offset:08X}",
            "address": f"0x{old_pointer:08X}",
            "size": ABILITY_NAMES_SIZE,
        },
        "target": {
            "offset": f"0x{target_offset:08X}",
            "address": f"0x{target_pointer:08X}",
            "size": ABILITY_NAMES_SIZE,
        },
        "rewritten_pointer_offsets": [f"0x{x:08X}" for x in refs],
        "thumb_literal_users": literal_users,
        "original_table_preserved": (
            expanded[old_offset:old_offset + ABILITY_NAMES_SIZE] == old_table
        ),
        "relocated_table_identical": True,
        "old_pointer_occurrences_after_patch": 0,
        "new_pointer_occurrences_after_patch": len(new_refs),
        "output": str(output),
        "output_size": len(expanded),
        "output_sha256": sha256(expanded),
        "runtime_emulator_tested": False,
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
