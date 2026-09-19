#!/usr/bin/env python3
"""Pokémon LeafGreen: permanent external-event availability patcher.

Policy:
- MysticTicket and AuroraTicket remain real Key Items.
- When the late-game Vermilion ferry checks either ticket, it silently adds the missing ticket
  (if the Key Items pocket has space) and then performs the normal item check.
- Altering Cave no longer depends on the unreleased Wonder Spot rotation: all nine programmed
  selector values use the same merged encounter table containing every event species.
- Story/Rainbow Pass progression and legendary one-time encounter state remain unchanged.

The tool only accepts verified clean ROM hashes.
"""
from __future__ import annotations
import argparse, hashlib, json, struct
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

def find_ticket_gate(data: bytes, flag: int, item: int) -> int:
    # Vanilla script:
    # checkflag flag; goto_if FALSE ...; checkitem item,1; compare VAR_RESULT,FALSE; ...
    sig = bytes((0x2B,)) + struct.pack("<H", flag) + bytes((0x06, 0x00))
    hits = []
    start = 0
    while True:
        i = data.find(sig, start)
        if i < 0:
            break
        if (
            i + 14 <= len(data)
            and data[i+9] == 0x47
            and data[i+10:i+12] == struct.pack("<H", item)
            and data[i+12:i+14] == b"\x01\x00"
        ):
            hits.append(i)
        start = i + 1
    if len(hits) != 1:
        raise RuntimeError(f"ticket gate flag={flag:#x} item={item}: expected one hit, got {len(hits)}")
    return hits[0]

def ticket_item_only_routine(start: int, item: int) -> bytes:
    # If already owned, return with VAR_RESULT=TRUE.
    # Otherwise AddBagItem(item,1), re-check, and return with the real result.
    ret_addr = 0x08000000 + start + 27
    out = bytearray()
    out += bytes((0x47,)) + struct.pack("<H", item) + b"\x01\x00"          # checkitem
    out += bytes((0x21,)) + struct.pack("<H", 0x800D) + b"\x01\x00"       # compare VAR_RESULT, TRUE
    out += bytes((0x06, 0x01)) + struct.pack("<I", ret_addr)              # goto_if_eq return
    out += bytes((0x44,)) + struct.pack("<H", item) + b"\x01\x00"          # additem
    out += bytes((0x47,)) + struct.pack("<H", item) + b"\x01\x00"          # checkitem
    out += b"\x03\x03\x02\x02\x02"                                        # return / return / padding
    assert len(out) == 31
    return bytes(out)

def patch(data: bytes) -> tuple[bytes, dict]:
    digest = sha256(data)
    if digest not in SUPPORTED_SHA256:
        raise RuntimeError(f"unsupported or already modified ROM SHA-256: {digest}")
    if len(data) != 16 * 1024 * 1024 or data[0xAC:0xAF] != b"BPG":
        raise RuntimeError("not a supported 16 MiB Pokémon LeafGreen ROM")

    out = bytearray(data)
    mystic = find_ticket_gate(data, 0x084A, 370)
    aurora = find_ticket_gate(data, 0x084B, 371)
    out[mystic:mystic+31] = ticket_item_only_routine(mystic, 370)
    out[aurora:aurora+31] = ticket_item_only_routine(aurora, 371)

    offsets = {}
    for name in ["ZUBAT","MAREEP","PINECO","HOUNDOUR","TEDDIURSA","AIPOM","SHUCKLE","STANTLER","SMEARGLE"]:
        offsets[name.lower()] = find_unique(data, mon_table(name), f"Altering Cave {name}")
    ordered = [offsets[n.lower()] for n in ["ZUBAT","MAREEP","PINECO","HOUNDOUR","TEDDIURSA","AIPOM","SHUCKLE","STANTLER","SMEARGLE"]]
    if any(ordered[i+1] - ordered[i] != 0x38 for i in range(8)):
        raise RuntimeError("Altering Cave tables are not in the expected contiguous 0x38-stride block")

    merged = merged_table()
    for off in ordered:
        out[off:off+len(merged)] = merged

    report = {
        "input_sha256": digest,
        "input_variant": SUPPORTED_SHA256[digest],
        "output_sha256": sha256(out),
        "ticket_policy": "real items; missing tickets are inserted when the normal late-game ferry check runs",
        "ticket_offsets": {"mystic": hex(mystic), "aurora": hex(aurora)},
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
