#!/usr/bin/env python3
"""Pokémon LeafGreen: permanent external-event availability patcher.

Policy:
- Add a permanent Mystery Gift Deliveryman NPC to Pallet Town.
- The NPC gives the real MysticTicket and AuroraTicket only when missing.
- Successful/owned tickets get the same ship-enable and received flags as the original distributions.
- The original Vermilion ferry ticket checks and normal Sevii/Rainbow Pass story progression remain unchanged.
- Altering Cave no longer depends on the unreleased Wonder Spot rotation: all nine programmed
  selector values use the same merged encounter table containing every event species.

The tool only accepts verified clean ROM hashes. ROM binaries are never bundled.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path

SPECIES = {
    "ZUBAT": 41, "MAREEP": 179, "AIPOM": 190, "PINECO": 204,
    "SHUCKLE": 213, "TEDDIURSA": 216, "HOUNDOUR": 228,
    "STANTLER": 234, "SMEARGLE": 235,
}
LEVELS = {
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
MERGED = [
    ("MAREEP",7), ("PINECO",25), ("HOUNDOUR",14), ("TEDDIURSA",26),
    ("AIPOM",22), ("SHUCKLE",24), ("STANTLER",28), ("SMEARGLE",18),
    ("ZUBAT",8), ("ZUBAT",14), ("ZUBAT",8), ("ZUBAT",14),
]
SUPPORTED_SHA256 = {
    "2957b392dc09fc8df45a660af5493368d7bd378d299862f4cc115998e9da0bf2": "Japan BPGJ Rev 0",
    "78d310d557ceebc593bd393acc52d1b19a8f023fec40bc200e6063880d8531fc": "USA BPGE Rev 0",
    "2f978f635b9593f6ca26ec42481c53a6b39f6cddd894ad5c062c1419fac58825": "Europe BPGE Rev 1",
    "6ab7183caf8bf093f42351cf7c891722ecef85f2ded922f6d2491c6062fa3fc2": "Germany BPGD Rev 0",
    "cc0fa93f4631d0814afcd5a273edf28f2876e126e8ef0df4dd39dd6f36e53ed3": "France BPGF Rev 0",
    "c71599a482c43df2104ce6be903393333d3ebacbf392ea5fcd8792dada8a5076": "Italy BPGI Rev 0",
    "f8908e0bd32cf27077a26b557e1eea0ff06ce8059bee5dc7d799aab44a070d48": "Spain BPGS Rev 0",
}

INJECTION_OFFSET = 0x800000
PALLET_NPC_LOCAL_ID = 4
OBJ_EVENT_GFX_MG_DELIVERYMAN = 69
MOVEMENT_TYPE_FACE_DOWN = 0x08
VAR_RESULT = 0x800D
ITEM_MYSTIC_TICKET = 370
ITEM_AURORA_TICKET = 371
FLAG_ENABLE_SHIP_NAVEL_ROCK = 0x084A
FLAG_ENABLE_SHIP_BIRTH_ISLAND = 0x084B
FLAG_RECEIVED_AURORA_TICKET = 0x02A7
FLAG_RECEIVED_MYSTIC_TICKET = 0x02A8

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def mon_table(name: str) -> bytes:
    sid = SPECIES[name]
    return b"".join(bytes((lv, lv)) + struct.pack("<H", sid) for lv in LEVELS[name])

def merged_table() -> bytes:
    return b"".join(bytes((lv, lv)) + struct.pack("<H", SPECIES[name]) for name, lv in MERGED)

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
        raise RuntimeError(f"{label}: expected exactly one signature, got {len(hits)}")
    return hits[0]

def object_prefix(local_id: int, gfx: int, x: int, y: int, elevation: int,
                  movement: int, range_x: int, range_y: int) -> bytes:
    return (
        bytes((local_id, gfx, 0, 0))
        + struct.pack("<hh", x, y)
        + bytes((elevation, movement, (range_y << 4) | range_x, 0))
        + struct.pack("<HH", 0, 0)
    )

def find_pallet_events(data: bytes) -> tuple[int, int]:
    woman = object_prefix(1, 23, 3, 10, 3, 2, 1, 4)
    fat_man = object_prefix(2, 27, 13, 17, 3, 2, 6, 2)
    oak = object_prefix(3, 71, 10, 8, 3, 7, 1, 1)

    hits = []
    start = 0
    while True:
        i = data.find(woman, start)
        if i < 0:
            break
        if (
            data[i + 24:i + 40] == fat_man
            and data[i + 48:i + 64] == oak
            and data[i + 64:i + 68] == b"\x00" * 4
            and data[i + 68:i + 70] == struct.pack("<H", 0x02C)
        ):
            hits.append(i)
        start = i + 1
    if len(hits) != 1:
        raise RuntimeError(f"Pallet Town object array: expected one hit, got {len(hits)}")

    object_offset = hits[0]
    map_events_sig = bytes((3, 3, 3, 5)) + struct.pack("<I", 0x08000000 + object_offset)
    map_events_offset = find_unique(data, map_events_sig, "Pallet Town MapEvents")
    return object_offset, map_events_offset

def make_object(local_id: int, gfx: int, x: int, y: int, elevation: int,
                movement: int, script_ptr: int, flag: int = 0) -> bytes:
    out = bytearray()
    out += bytes((local_id, gfx, 0, 0))
    out += struct.pack("<hh", x, y)
    out += bytes((elevation, movement, 0, 0))
    out += struct.pack("<HH", 0, 0)
    out += struct.pack("<I", script_ptr)
    out += struct.pack("<H", flag)
    out += b"\x00\x00"
    assert len(out) == 24
    return bytes(out)

def assemble_ticket_script(base_offset: int) -> bytes:
    out = bytearray()
    labels: dict[str, int] = {}
    fixups: list[tuple[int, str]] = []

    def label(name: str) -> None:
        labels[name] = len(out)

    def jump_if(condition: int, target: str) -> None:
        out.extend((0x06, condition))
        fixups.append((len(out), target))
        out.extend(b"\x00" * 4)

    def checkitem(item: int) -> None:
        out.extend((0x47,))
        out.extend(struct.pack("<HH", item, 1))

    def compare_true() -> None:
        out.extend((0x21,))
        out.extend(struct.pack("<HH", VAR_RESULT, 1))

    def giveitem(item: int) -> None:
        out.extend((0x1A,))
        out.extend(struct.pack("<HH", 0x8000, item))
        out.extend((0x1A,))
        out.extend(struct.pack("<HH", 0x8001, 1))
        out.extend((0x09, 0x00))  # callstd STD_OBTAIN_ITEM

    def setflag(flag: int) -> None:
        out.extend((0x29,))
        out.extend(struct.pack("<H", flag))

    out.extend((0x6A, 0x5A))  # lock, faceplayer

    checkitem(ITEM_MYSTIC_TICKET)
    compare_true()
    jump_if(1, "mystic_flags")  # EQUAL
    giveitem(ITEM_MYSTIC_TICKET)
    compare_true()
    jump_if(5, "aurora_start")  # NOT EQUAL: bag full / give failed
    label("mystic_flags")
    setflag(FLAG_ENABLE_SHIP_NAVEL_ROCK)
    setflag(FLAG_RECEIVED_MYSTIC_TICKET)

    label("aurora_start")
    checkitem(ITEM_AURORA_TICKET)
    compare_true()
    jump_if(1, "aurora_flags")
    giveitem(ITEM_AURORA_TICKET)
    compare_true()
    jump_if(5, "done")
    label("aurora_flags")
    setflag(FLAG_ENABLE_SHIP_BIRTH_ISLAND)
    setflag(FLAG_RECEIVED_AURORA_TICKET)

    label("done")
    out.extend((0x6C, 0x02))  # release, end

    for pos, name in fixups:
        out[pos:pos + 4] = struct.pack("<I", 0x08000000 + base_offset + labels[name])
    return bytes(out)

def patch(data: bytes) -> tuple[bytes, dict]:
    digest = sha256(data)
    if digest not in SUPPORTED_SHA256:
        raise RuntimeError(f"unsupported or already modified ROM SHA-256: {digest}")
    if len(data) != 16 * 1024 * 1024 or data[0xAC:0xAF] != b"BPG":
        raise RuntimeError("not a supported 16 MiB Pokémon LeafGreen ROM")

    out = bytearray(data)
    pallet_objects, pallet_events = find_pallet_events(data)

    script_offset = INJECTION_OFFSET + 4 * 24
    script = assemble_ticket_script(script_offset)
    injection_size = 4 * 24 + len(script)
    if data[INJECTION_OFFSET:INJECTION_OFFSET + injection_size] != b"\xFF" * injection_size:
        raise RuntimeError("expected unused 0xFF injection area at ROM offset 0x800000")

    out[INJECTION_OFFSET:INJECTION_OFFSET + 3 * 24] = data[pallet_objects:pallet_objects + 3 * 24]
    deliveryman = make_object(
        PALLET_NPC_LOCAL_ID,
        OBJ_EVENT_GFX_MG_DELIVERYMAN,
        14, 12, 3,
        MOVEMENT_TYPE_FACE_DOWN,
        0x08000000 + script_offset,
    )
    out[INJECTION_OFFSET + 3 * 24:INJECTION_OFFSET + 4 * 24] = deliveryman
    out[script_offset:script_offset + len(script)] = script

    out[pallet_events] = 4
    out[pallet_events + 4:pallet_events + 8] = struct.pack("<I", 0x08000000 + INJECTION_OFFSET)

    offsets = {}
    order = ["ZUBAT","MAREEP","PINECO","HOUNDOUR","TEDDIURSA","AIPOM","SHUCKLE","STANTLER","SMEARGLE"]
    for name in order:
        offsets[name.lower()] = find_unique(data, mon_table(name), f"Altering Cave {name}")
    ordered = [offsets[name.lower()] for name in order]
    if any(ordered[i + 1] - ordered[i] != 0x38 for i in range(8)):
        raise RuntimeError("Altering Cave table block is not the expected contiguous 0x38-stride layout")

    merged = merged_table()
    for off in ordered:
        out[off:off + len(merged)] = merged

    report = {
        "input_sha256": digest,
        "input_variant": SUPPORTED_SHA256[digest],
        "output_sha256": sha256(out),
        "ticket_policy": "Pallet Town Mystery Gift Deliveryman gives the real missing tickets; vanilla ferry checks remain unchanged",
        "pallet_town": {
            "original_object_array": hex(pallet_objects),
            "map_events": hex(pallet_events),
            "injected_object_array": hex(INJECTION_OFFSET),
            "deliveryman_script": hex(script_offset),
            "deliveryman_local_id": PALLET_NPC_LOCAL_ID,
            "deliveryman_xy": [14, 12],
        },
        "altering_cave_table_offsets": {k: hex(v) for k, v in offsets.items()},
    }
    return bytes(out), report

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("rom", type=Path)
    ap.add_argument("-o", "--output", type=Path)
    ap.add_argument("--report", type=Path)
    args = ap.parse_args()

    patched, report = patch(args.rom.read_bytes())
    output = args.output or args.rom.with_name(args.rom.stem + " - Always On External Events.gba")
    output.write_bytes(patched)
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"wrote: {output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
