#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAPACITY = ROOT / "manifests" / "generation_capacity.json"
AUDIT = ROOT / "manifests" / "rom_save_audit.json"


def main() -> int:
    cap = json.loads(CAPACITY.read_text(encoding="utf-8"))
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    errors: list[str] = []

    policy = cap["policy"]
    if policy["rom_input_size_bytes"] != 16 * 1024 * 1024:
        errors.append("clean LeafGreen ROM baseline is not 16 MiB")
    if policy["rom_expanded_size_bytes"] != 32 * 1024 * 1024:
        errors.append("expanded ROM target is not 32 MiB")
    if policy["save_size_bytes"] != 128 * 1024:
        errors.append("save policy must preserve 128 KiB FLASH1M")
    if policy["form_change_mechanics"] != "deferred":
        errors.append("form-change mechanics must remain deferred in this phase")

    if audit["basis"]["local_pairs"] != 7:
        errors.append("ROM/SAV audit does not contain all seven target pairs")
    if audit["save_layout"]["trainer_tower_ereader_sectors"] != [30, 31]:
        errors.append("Trainer Tower sectors must remain reserved")
    if audit["save_layout"]["hall_of_fame_sectors"] != [28, 29]:
        errors.append("Hall of Fame sectors must remain reserved")

    dex = cap["save_evidence"]["phase1_reclaimable_existing_fields"]["SaveBlock2_filler_B20"]
    needed = (
        dex["planned_layout"]["extended_seen_bits"] // 8
        + dex["planned_layout"]["extended_owned_bits"] // 8
    )
    if needed != dex["bytes"]:
        errors.append(
            f"extended Pokedex needs {needed} bytes but filler_B20 provides {dex['bytes']}"
        )
    if dex["bytes"] != 0x400:
        errors.append("SaveBlock2 filler_B20 must remain exactly 0x400 bytes")
    if not dex["zero_in_all_7_active_samples"]:
        errors.append("SaveBlock2 filler_B20 is not verified zero in all active samples")

    native = cap["native_identifier_storage"]
    if native["moves"]["pokemon_move_slots"] != "u16":
        errors.append("native Pokémon move slots must remain recorded as u16")
    if native["species"]["boxed_pokemon"] != "u16":
        errors.append("native boxed species field must remain recorded as u16")
    if cap["save_evidence"]["spare_physical_sectors"] != 0:
        errors.append("FRLG 128 KiB save must not claim spare physical sectors")

    if errors:
        print("generation/save capacity validation FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print("generation/save capacity validation OK")
    print("- ROM: 16 MiB source -> 32 MiB expansion window")
    print("- SAV: fixed 128 KiB / 32 sectors")
    print("- physical spare save sectors: 0")
    print("- extended Pokedex: 4096 seen + 4096 owned bits in existing 0x400-byte filler")
    print("- form-change mechanics: deferred")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
