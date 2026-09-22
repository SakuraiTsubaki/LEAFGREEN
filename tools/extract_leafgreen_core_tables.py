#!/usr/bin/env python3
"""Extract LeafGreen core table locations from the retail GFRomHeader.

The tool is read-only. It accepts a BPG* LeafGreen ROM, parses the Game Freak
ROM header at 0x100, records core table pointers and absolute-pointer reference
sites, and locates the retail evolution table by a source-derived prefix.

ROM binaries are never written to the repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

ROM_BASE = 0x08000000
GF_HEADER_OFFSET = 0x100

PTR_FIELDS = {
    "monFrontPics": 0x28,
    "monBackPics": 0x2C,
    "monNormalPalettes": 0x30,
    "monShinyPalettes": 0x34,
    "monIcons": 0x38,
    "monIconPaletteIds": 0x3C,
    "monIconPalettes": 0x40,
    "monSpeciesNames": 0x44,
    "moveNames": 0x48,
    "decorations": 0x4C,
    "speciesInfo": 0xBC,
    "abilityNames": 0xC0,
    "abilityDescriptions": 0xC4,
    "items": 0xC8,
    "moves": 0xCC,
    "ballGfx": 0xD0,
    "ballPalettes": 0xD4,
}

SAVE_U32_FIELDS = {
    "flagsOffset": 0x50,
    "varsOffset": 0x54,
    "pokedexOffset": 0x58,
    "seen1Offset": 0x5C,
    "seen2Offset": 0x60,
    "partyCountOffset": 0x90,
    "partyOffset": 0x94,
    "externalEventFlagsOffset": 0xB0,
    "externalEventDataOffset": 0xB4,
    "gcnLinkFlagsOffset": 0xD8,
    "pcItemsOffset": 0xEC,
    "giftRibbonsOffset": 0xF0,
    "enigmaBerryOffset": 0xF4,
    "enigmaBerrySize": 0xF8,
}


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def find_all(data: bytes, needle: bytes) -> list[int]:
    hits: list[int] = []
    start = 0
    while True:
        hit = data.find(needle, start)
        if hit < 0:
            return hits
        hits.append(hit)
        start = hit + 1


def evolution_species_record(method: int, param: int, target: int) -> bytes:
    # Retail agbcc ABI rounds struct Evolution {u16,u16,u16} to an 8-byte stride.
    first = struct.pack("<HHH", method, param, target) + b"\x00\x00"
    return first + b"\x00" * (4 * 8)


def evolution_prefix() -> bytes:
    # Source-derived prefix:
    # Bulbasaur -> Ivysaur at 16
    # Ivysaur -> Venusaur at 32
    # Venusaur has no evolution
    # Charmander -> Charmeleon at 16
    # Charmeleon -> Charizard at 36
    return b"".join(
        (
            evolution_species_record(4, 16, 2),
            evolution_species_record(4, 32, 3),
            b"\x00" * 40,
            evolution_species_record(4, 16, 5),
            evolution_species_record(4, 36, 6),
        )
    )


def ptr_record(data: bytes, pointer: int) -> dict:
    if not (ROM_BASE <= pointer < ROM_BASE + 0x02000000):
        raise SystemExit(f"pointer outside 32 MiB GBA ROM window: 0x{pointer:08X}")
    offset = pointer - ROM_BASE
    refs = find_all(data, struct.pack("<I", pointer))
    return {
        "address": f"0x{pointer:08X}",
        "offset": f"0x{offset:08X}",
        "absolute_pointer_reference_count": len(refs),
        "absolute_pointer_reference_offsets": [f"0x{x:08X}" for x in refs],
    }


def extract(path: Path) -> dict:
    data = path.read_bytes()
    if len(data) not in (0x01000000, 0x02000000):
        raise SystemExit(f"{path}: expected 16 or 32 MiB, got {len(data)} bytes")
    if data[0xAC:0xAF] != b"BPG":
        raise SystemExit(f"{path}: not a BPG* LeafGreen ROM")

    base = GF_HEADER_OFFSET
    game_name = data[base + 0x08:base + 0x28].split(b"\0", 1)[0]
    if game_name != b"pokemon green version":
        raise SystemExit(
            f"{path}: unexpected GFRomHeader game name {game_name!r} at 0x108"
        )

    result = {
        "file": path.name,
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data),
        "game_code": data[0xAC:0xB0].decode("ascii", errors="replace"),
        "revision": data[0xBC],
        "gf_rom_header_offset": "0x00000100",
        "gf_rom_header_address": "0x08000100",
        "version": u32(data, base + 0x00),
        "language": u32(data, base + 0x04),
        "game_name": game_name.decode("ascii"),
        "pokedex_count": u32(data, base + 0x70),
        "save_block_2_size": u32(data, base + 0x88),
        "save_block_1_size": u32(data, base + 0x8C),
        "tables": {},
        "save_offsets": {},
    }

    for name, field_offset in PTR_FIELDS.items():
        result["tables"][name] = ptr_record(data, u32(data, base + field_offset))

    hits = find_all(data, evolution_prefix())
    if len(hits) != 1:
        raise SystemExit(
            f"{path}: expected exactly one evolution-table prefix, got {len(hits)}"
        )
    evo_offset = hits[0]
    evo = ptr_record(data, ROM_BASE + evo_offset)
    evo["detection"] = (
        "Bulbasaur/Ivysaur/Venusaur/Charmander/Charmeleon source-derived "
        "evolution prefix; retail Evolution ABI stride 8 bytes; 5 entries/species"
    )
    result["tables"]["evolutionTable"] = evo

    for name, field_offset in SAVE_U32_FIELDS.items():
        result["save_offsets"][name] = u32(data, base + field_offset)

    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("rom", nargs="+", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()

    report = {
        "schema_version": 1,
        "source_reference": {
            "repository": "pret/pokefirered",
            "commit": "c75f352304d529f6ba92d4f74b9cf8b5c3810788",
            "gf_header_source": "src/rom_header_gf.c",
            "evolution_source": "src/data/pokemon/evolution.h",
        },
        "profiles": [extract(path) for path in args.rom],
    }

    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
