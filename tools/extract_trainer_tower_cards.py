#!/usr/bin/env python3
"""Extract the 32 Battle-e-derived Trainer Tower floor records from a clean USA LeafGreen ROM.

This does not distribute ROM/card data. It requires a user-supplied clean ROM and emits the
32 fixed-size floor records plus a SHA-256 manifest. The declaration/order mapping is tracked
in manifests/trainer_tower_cards.json.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

EXPECTED_SHA256 = "78d310d557ceebc593bd393acc52d1b19a8f023fec40bc200e6063880d8531fc"
BLOCK_OFFSET = 0x47A488
FLOOR_SIZE = 0x3E0
COUNT = 32

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("rom", type=Path)
    ap.add_argument("-o", "--out-dir", type=Path, default=Path("trainer_tower_cards"))
    args = ap.parse_args()

    data = args.rom.read_bytes()
    digest = sha256(data)
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"unsupported ROM SHA-256: {digest}")

    block = data[BLOCK_OFFSET:BLOCK_OFFSET + FLOOR_SIZE * COUNT]
    if len(block) != FLOOR_SIZE * COUNT:
        raise SystemExit("ROM is too short for Trainer Tower block")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "input_sha256": digest,
        "block_offset": hex(BLOCK_OFFSET),
        "floor_size": FLOOR_SIZE,
        "count": COUNT,
        "floors": [],
    }
    for i in range(COUNT):
        card_id = f"15-A{i+1:03d}"
        floor = block[i*FLOOR_SIZE:(i+1)*FLOOR_SIZE]
        fn = f"{card_id}.bin"
        (args.out_dir / fn).write_bytes(floor)
        manifest["floors"].append({
            "card_id": card_id,
            "file": fn,
            "sha256": sha256(floor),
        })
    (args.out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
