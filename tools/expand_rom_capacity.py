#!/usr/bin/env python3
"""Validate a LeafGreen ROM/SAV pair, then expand the ROM to 32 MiB.

The save remains 128 KiB and is never rewritten by this tool. Expansion is
allowed only after the supplied save passes the vanilla FRLG 32-sector layout
checks. This keeps ROM growth and save-format decisions coupled to real data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROM_MANIFEST = ROOT / "manifests" / "leafgreen_roms.json"

SECTOR_SIZE = 0x1000
SECTOR_DATA_SIZE = 0xF80
SECTOR_SIGNATURE = 0x08012025
SAVE_SIZE = 0x20000
ROM_SIZE = 0x1000000
EXPANDED_ROM_SIZE = 0x2000000

# pret/pokefirered@c75f... sizes:
# SaveBlock2 0xF24; SaveBlock1 0x3D68; PokemonStorage 0x83D0.
SECTION_DATA_SIZES = [
    0xF24,
    0xF80, 0xF80, 0xF80, 0x3D68 - 3 * 0xF80,
    0xF80, 0xF80, 0xF80, 0xF80, 0xF80, 0xF80, 0xF80, 0xF80,
    0x83D0 - 8 * 0xF80,
]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def calc_checksum(data: bytes, size: int) -> int:
    total = 0
    for offset in range(0, size // 4 * 4, 4):
        total = (total + int.from_bytes(data[offset:offset + 4], "little")) & 0xFFFFFFFF
    return ((total >> 16) + total) & 0xFFFF


def load_supported_rom_hashes() -> dict[str, str]:
    data = json.loads(ROM_MANIFEST.read_text(encoding="utf-8"))
    supported: dict[str, str] = {}
    for rom in data["roms"]:
        supported[rom["sha256_original"]] = f'{rom["file"]} clean'
        supported[rom["sha256_patched"]] = f'{rom["file"]} external-events patched'
    return supported


def validate_save_slot(data: bytes, slot: int) -> dict:
    base_sector = slot * 14
    ids: set[int] = set()
    counters: list[int] = []
    sectors = []

    for physical in range(base_sector, base_sector + 14):
        sector = data[physical * SECTOR_SIZE:(physical + 1) * SECTOR_SIZE]
        section_id, checksum = struct.unpack_from("<HH", sector, 0xFF4)
        signature, counter = struct.unpack_from("<II", sector, 0xFF8)

        checksum_ok = False
        if 0 <= section_id < 14 and signature == SECTOR_SIGNATURE:
            expected = calc_checksum(sector[:SECTOR_DATA_SIZE], SECTION_DATA_SIZES[section_id])
            checksum_ok = checksum == expected
            if checksum_ok:
                ids.add(section_id)
                counters.append(counter)

        sectors.append({
            "physical_sector": physical,
            "section_id": section_id,
            "signature_ok": signature == SECTOR_SIGNATURE,
            "checksum_ok": checksum_ok,
            "counter": counter,
        })

    full = ids == set(range(14)) and len(counters) == 14 and len(set(counters)) == 1
    return {
        "slot": slot,
        "valid": full,
        "counter": counters[0] if full else None,
        "valid_section_ids": sorted(ids),
        "sectors": sectors,
    }


def choose_active_slot(slots: list[dict]) -> dict:
    valid = [slot for slot in slots if slot["valid"]]
    if not valid:
        raise SystemExit("save has no complete checksum-valid FRLG main slot")
    if len(valid) == 1:
        return valid[0]

    a, b = valid
    ca, cb = a["counter"], b["counter"]

    # Match the wraparound special case used by the retail loader.
    if (ca == 0xFFFFFFFF and cb == 0) or (ca == 0 and cb == 0xFFFFFFFF):
        return b if ((ca + 1) & 0xFFFFFFFF) < ((cb + 1) & 0xFFFFFFFF) else a
    return b if ca < cb else a


def inspect_special_sectors(save: bytes) -> dict:
    def nonzero(index: int) -> bool:
        sector = save[index * SECTOR_SIZE:(index + 1) * SECTOR_SIZE]
        return any(byte != 0 for byte in sector)

    return {
        "hall_of_fame": {
            "sectors": [28, 29],
            "nonzero": nonzero(28) or nonzero(29),
            "reserved": True,
        },
        "trainer_tower_ereader": {
            "sectors": [30, 31],
            "nonzero": nonzero(30) or nonzero(31),
            "reserved": True,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("rom", type=Path)
    ap.add_argument("save", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    ap.add_argument("--save-copy", type=Path,
                    help="optional byte-identical copy of the validated 128 KiB save")
    ap.add_argument("--report", type=Path)
    args = ap.parse_args()

    rom = args.rom.read_bytes()
    save = args.save.read_bytes()

    if len(save) != SAVE_SIZE:
        raise SystemExit(f"unsupported save size: {len(save)} bytes (expected {SAVE_SIZE})")

    if len(rom) not in (ROM_SIZE, EXPANDED_ROM_SIZE):
        raise SystemExit(
            f"unsupported ROM size: {len(rom)} bytes "
            f"(expected {ROM_SIZE} or {EXPANDED_ROM_SIZE})"
        )
    if rom[0xAC:0xAF] != b"BPG":
        raise SystemExit("not a Pokémon LeafGreen BPG* ROM")

    lower = rom[:ROM_SIZE]
    supported = load_supported_rom_hashes()
    base_digest = sha256(lower)
    if base_digest not in supported:
        raise SystemExit(f"unsupported 16 MiB ROM base SHA-256: {base_digest}")

    slots = [validate_save_slot(save, 0), validate_save_slot(save, 1)]
    active = choose_active_slot(slots)
    special = inspect_special_sectors(save)

    # 32 MiB is the ROM window used by the pinned pokefirered linker scripts.
    if len(rom) == ROM_SIZE:
        expanded = rom + b"\xFF" * ROM_SIZE
        already_expanded = False
    else:
        if rom[ROM_SIZE:] != b"\xFF" * ROM_SIZE:
            raise SystemExit(
                "32 MiB input already contains data in the expansion half; "
                "refusing to overwrite it"
            )
        expanded = rom
        already_expanded = True

    output = args.output or args.rom.with_name(args.rom.stem + " - 32MiB.gba")
    output.write_bytes(expanded)

    if args.save_copy:
        shutil.copyfile(args.save, args.save_copy)

    report = {
        "rom": {
            "input": str(args.rom),
            "variant": supported[base_digest],
            "game_code": lower[0xAC:0xB0].decode("ascii", errors="replace"),
            "revision": lower[0xBC],
            "input_size": len(rom),
            "base_16m_sha256": base_digest,
            "output": str(output),
            "output_size": len(expanded),
            "output_sha256": sha256(expanded),
            "already_expanded": already_expanded,
            "new_region": {
                "file_offset_start": "0x1000000",
                "file_offset_end_exclusive": "0x2000000",
                "rom_address_start": "0x09000000",
                "rom_address_end_exclusive": "0x0A000000",
                "initial_fill": "0xFF",
            },
        },
        "save": {
            "input": str(args.save),
            "size": len(save),
            "sha256": sha256(save),
            "modified": False,
            "slots": slots,
            "active_slot": active["slot"],
            "active_counter": active["counter"],
            "special_sectors": special,
            "policy": "keep physical save at 128 KiB; use audited in-struct unused fields before any checksum-layout migration",
        },
        "form_change_mechanics": "deferred",
        "gameplay_tables_relocated": False,
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
