#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAPACITY = ROOT / "manifests" / "generation_capacity.json"
AUDIT = ROOT / "manifests" / "rom_save_audit.json"
ROM_LIMIT = ROOT / "manifests" / "rom_size_limit_probe.json"


def main() -> int:
    cap = json.loads(CAPACITY.read_text(encoding="utf-8"))
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    limit = json.loads(ROM_LIMIT.read_text(encoding="utf-8"))
    errors: list[str] = []

    policy = cap["policy"]
    expected = {
        "current_content_generation": 9,
        "reserved_generation": 10,
        "current_behavior_generation": "GEN_9",
        "rom_input_size_bytes": 16 * 1024 * 1024,
        "rom_expanded_size_bytes": 32 * 1024 * 1024,
        "rom_hard_limit_bytes": 32 * 1024 * 1024,
        "save_size_bytes": 128 * 1024,
    }
    for key, value in expected.items():
        if policy.get(key) != value:
            errors.append(f"{key}: expected {value!r}, got {policy.get(key)!r}")

    if policy["form_change_mechanics"] != "deferred":
        errors.append("form-change mechanics must remain deferred")
    if policy["speculative_generation_10_content"]:
        errors.append("speculative Generation 10 content must remain disabled")

    if limit["result"]["maximum_directly_addressable_mib"] != 32:
        errors.append("ROM-size probe no longer reports a 32 MiB standard hard limit")

    if audit["basis"]["local_pairs"] != 7:
        errors.append("ROM/SAV audit must cover all seven supplied profiles")
    if audit["save_layout"]["spare_physical_sectors"] != 0:
        errors.append("retail 128 KiB Flash has no spare physical sectors")
    if audit["save_layout"]["hall_of_fame_sectors"] != [28, 29]:
        errors.append("Hall of Fame sectors must remain 28-29")
    if audit["save_layout"]["trainer_tower_ereader_sectors"] != [30, 31]:
        errors.append("Trainer Tower/e-Reader sectors must remain 30-31")

    japan = audit["observed_save_checksum_profiles"]["Japan_BPGJ_active_slot"]
    if japan["rom_header_save_block1_size"] != "0x3D40":
        errors.append("Japanese ROM-header SaveBlock1 evidence must remain 0x3D40")
    if japan["observed_checksum_save_block1_span"] != "0x3D68":
        errors.append("supplied Japanese active SAV checksum evidence must remain 0x3D68")

    candidate = audit["validated_saveblock2_extension_candidate"]
    if candidate["bytes"] != 1024:
        errors.append("SaveBlock2 extension candidate must remain exactly 0x400 bytes")
    if not candidate["all_zero_in_all_7_active_saves"]:
        errors.append("SaveBlock2 candidate is not zero in all seven active samples")
    if candidate["runtime_status"] != (
        "reserved candidate only; retail ROM read/write hooks are not yet implemented"
    ):
        errors.append("SaveBlock2 candidate runtime status changed without review")

    modern = cap["target_modern_core_storage"]
    if modern["species_bits"] != 11 or modern["move_bits"] != 11:
        errors.append("modern-core species/move serialized width changed unexpectedly")
    if modern["held_item_bits"] != 16:
        errors.append("modern-core held-item width must remain 16 bits")

    if errors:
        print("generation/save capacity validation FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print("generation/save capacity validation OK")
    print("- content generation: 9")
    print("- reserved generation: 10")
    print("- behavior generation: GEN_9")
    print("- ROM: 16 MiB source -> 32 MiB standard hard limit")
    print("- SAV: fixed 128 KiB / 32 sectors / no spare physical sectors")
    print("- Japanese evidence: ROM header 0x3D40; supplied active SAV checksum 0x3D68")
    print("- SaveBlock2 0x400 extension area: candidate only, runtime hook pending")
    print("- form-change mechanics: deferred")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
