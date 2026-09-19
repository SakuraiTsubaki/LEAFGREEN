#!/usr/bin/env python3
"""Pokémon LeafGreen: always-on external event content patcher.

Supported policy:
- MysticTicket / Navel Rock ship gate always passes after normal Sevii ferry progression.
- AuroraTicket / Birth Island ship gate always passes after normal Sevii ferry progression.
- Altering Cave uses one permanent merged table containing every programmed set species,
  copied over all nine selectors so old saves with any selector value behave identically.

This tool never contains or downloads a ROM. It patches a user-supplied clean ROM.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path

SPECIES = {
    "ZUBAT": 41,
    "MAREEP": 179,
    "AIPOM": 190,
    "PINECO": 204,
    "SHUCKLE": 213,
    "TEDDIURSA": 216,
    "HOUNDOUR": 228,
    "STANTLER": 234,
    "SMEARGLE": 235,
}

VANILLA_LEVELS = {
    "ZUBAT":     [10,12,8,14,10,12,16,6,8,14,8,14],
    "MAREEP":    [7,9,5,11,7,9,13,3,5,11,5,11],
    "PINECO":    [23,25,22,27,23,25,29,19,21,27,21,27],
    "HOUNDOUR":  [16,18,14,20,16,18,22,12,14,20,14,20],
    "TEDDIURSA": [22,24,20,26,22,24,28,18,20,26,20,26],
    "AIPOM":     [22,24,20,26,22,24,28,18,20,26,20,26],
    "SHUCKLE":   [22,24,20,26,22,24,28,18,20,26,20,26],
    "STANTLER":  [22,24,20,26,22,24,28,18,20,26,20,26],
    "SMEARGLE":  [22,24,20,26,22,24,28,18,20,26,20,26],
}

# Vanilla land-slot weights are 20,20,10,10,10,10,5,5,4,4,1,1.
# All eight unreleased Wonder Spot species stay permanently available;
# Zubat remains as the baseline cave encounter at a combined 10%.
MERGED_SLOTS = [
    ("MAREEP", 7),       # 20%
    ("PINECO", 25),      # 20%
    ("HOUNDOUR", 14),    # 10%
    ("TEDDIURSA", 26),   # 10%
    ("AIPOM", 22),       # 10%
    ("SHUCKLE", 24),     # 10%
    ("STANTLER", 28),    # 5%
    ("SMEARGLE", 18),    # 5%
    ("ZUBAT", 8),        # 4%
    ("ZUBAT", 14),       # 4%
    ("ZUBAT", 8),        # 1%
    ("ZUBAT", 14),       # 1%
]

ALWAYS_TRUE_SCRIPT = bytes.fromhex("160d80010003")  # setvar VAR_RESULT, TRUE; return
SUPPORTED_SHA256 = {
    "2957b392dc09fc8df45a660af5493368d7bd378d299862f4cc115998e9da0bf2": "Japan BPGJ Rev 0",
    "78d310d557ceebc593bd393acc52d1b19a8f023fec40bc200e6063880d8531fc": "USA BPGE Rev 0",
    "2f978f635b9593f6ca26ec42481c53a6b39f6cddd894ad5c062c1419fac58825": "Europe BPGE Rev 1",
    "6ab7183caf8bf093f42351cf7c891722ecef85f2ded922f6d2491c6062fa3fc2": "Germany BPGD Rev 0",
    "cc0fa93f4631d0814afcd5a273edf28f2876e126e8ef0df4dd39dd6f36e53ed3": "France BPGF Rev 0",
    "c71599a482c43df2104ce6be903393333d3ebacbf392ea5fcd8792dada8a5076": "Italy BPGI Rev 0",
    "f8908e0bd32cf27077a26b557e1eea0ff06ce8059bee5dc7d799aab44a070d48": "Spain BPGS Rev 0",
}

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def mon_table(species_name: str) -> bytes:
    sid = SPECIES[species_name]
    return b"".join(bytes((lv, lv)) + struct.pack("<H", sid) for lv in VANILLA_LEVELS[species_name])

def merged_table() -> bytes:
    return b"".join(bytes((lv, lv)) + struct.pack("<H", SPECIES[name]) for name, lv in MERGED_SLOTS)

def find_ticket_gate(data: bytes, flag: int, item: int) -> int:
    hits = []
    for i in range(len(data) - 14):
        if (
            data[i] == 0x2B
            and data[i+1:i+3] == flag.to_bytes(2, "little")
            and data[i+3] == 0x06
            and data[i+4] == 0x00
            and data[i+9] == 0x47
            and data[i+10:i+12] == item.to_bytes(2, "little")
            and data[i+12:i+14] == b"\x01\x00"
        ):
            hits.append(i)
    if len(hits) != 1:
        raise RuntimeError(f"ticket gate signature count={len(hits)} for flag {flag:#x}, item {item:#x}")
    return hits[0]

def find_unique(data: bytes, pattern: bytes, label: str) -> int:
    hits = []
    start = 0
    while True:
        i = data.find(pattern, start)
        if i < 0:
            break
        hits.append(i)
        start = i + 1
    if len(hits) != 1:
        raise RuntimeError(f"{label} signature count={len(hits)}")
    return hits[0]

def patch(data: bytes) -> tuple[bytes, dict]:
    digest = sha256(data)
    if digest not in SUPPORTED_SHA256:
        raise RuntimeError(f"unsupported or already modified ROM SHA-256: {digest}")
    if len(data) != 16 * 1024 * 1024 or data[0xAC:0xAF] != b"BPG":
        raise RuntimeError("not a supported 16 MiB Pokémon LeafGreen ROM")

    out = bytearray(data)
    mystic = find_ticket_gate(data, 0x084A, 370)
    aurora = find_ticket_gate(data, 0x084B, 371)
    out[mystic:mystic+len(ALWAYS_TRUE_SCRIPT)] = ALWAYS_TRUE_SCRIPT
    out[aurora:aurora+len(ALWAYS_TRUE_SCRIPT)] = ALWAYS_TRUE_SCRIPT

    table_offsets = {}
    for name in ["ZUBAT", "MAREEP", "PINECO", "HOUNDOUR", "TEDDIURSA", "AIPOM", "SHUCKLE", "STANTLER", "SMEARGLE"]:
        off = find_unique(data, mon_table(name), f"Altering Cave {name}")
        table_offsets[name.lower()] = off
    ordered = list(table_offsets.values())
    if any(ordered[i+1] - ordered[i] != 0x38 for i in range(8)):
        raise RuntimeError("Altering Cave table block is not the expected contiguous 0x38-stride layout")

    merged = merged_table()
    for off in ordered:
        out[off:off+len(merged)] = merged

    report = {
        "input_sha256": digest,
        "input_variant": SUPPORTED_SHA256[digest],
        "output_sha256": sha256(out),
        "ticket_offsets": {"mystic": hex(mystic), "aurora": hex(aurora)},
        "altering_cave_table_offsets": {k: hex(v) for k, v in table_offsets.items()},
    }
    return bytes(out), report

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("rom", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    ap.add_argument("--report", type=Path)
    args = ap.parse_args()
    src = args.rom.read_bytes()
    patched, report = patch(src)
    output = args.output or args.rom.with_name(args.rom.stem + " - Always On External Events.gba")
    output.write_bytes(patched)
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"wrote: {output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
