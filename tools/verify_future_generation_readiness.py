#!/usr/bin/env python3
"""Verify LEAFGREEN Generation 10 readiness contracts without ROM binaries."""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "generation-superset.json"
READINESS = ROOT / "manifests" / "future-generation-readiness.json"
CAPACITY = ROOT / "manifests" / "generation_capacity.json"
AUDIT = ROOT / "manifests" / "rom_save_audit.json"
INVENTORY = ROOT / "manifests" / "core_table_inventory.csv"
REFERENCE_AUDIT = ROOT / "manifests" / "core_table_reference_audit.csv"
ROM_LIMIT = ROOT / "manifests" / "rom_size_limit_probe.json"

EXPECTED_EXPANSION_REF = "75b806a3ab57a81ff1eb6179288981f0b3cc3050"
EXPECTED_TABLES = {
    "speciesInfo",
    "abilityNames",
    "abilityDescriptions",
    "items",
    "moves",
    "monSpeciesNames",
    "moveNames",
    "evolutionTable",
}


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> int:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    ready = json.loads(READINESS.read_text(encoding="utf-8"))
    capacity = json.loads(CAPACITY.read_text(encoding="utf-8"))
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    rom_limit = json.loads(ROM_LIMIT.read_text(encoding="utf-8"))

    future = config["futureGeneration"]
    if future["currentContentGeneration"] != 9:
        fail("current content generation must remain 9")
    if future["reservedGeneration"] != 10:
        fail("Generation 10 slot is not reserved")
    if future["currentBehaviorGeneration"] != "GEN_9":
        fail("current behavior generation must remain GEN_9")
    if future["formChangeWork"] != "deferred":
        fail("form-change work must remain deferred in this phase")
    if future["speculativeGeneration10Content"]:
        fail("speculative Generation 10 content must remain disabled")
    if future["modernCore"]["upstreamRef"] != EXPECTED_EXPANSION_REF:
        fail("LeafGreen modern-core pin drifted from the Generation III superset")

    strategy = ready["strategy"]
    if (
        strategy["current_content_generation"],
        strategy["reserved_generation"],
        strategy["current_behavior_generation"],
    ) != (9, 10, "GEN_9"):
        fail("future-generation readiness strategy is inconsistent")
    if strategy["form_change_work"] != "deferred":
        fail("readiness manifest unexpectedly enables form changes")
    if ready["modern_core"]["ref"] != EXPECTED_EXPANSION_REF:
        fail("readiness manifest expansion pin mismatch")

    policy = capacity["policy"]
    if policy["rom_hard_limit_bytes"] != 32 * 1024 * 1024:
        fail("standard GBA ROM hard limit must stay 32 MiB")
    if policy["save_size_bytes"] != 128 * 1024:
        fail("LeafGreen save must stay 128 KiB")
    if policy["reserved_generation"] != 10:
        fail("capacity manifest lost the Generation 10 reservation")
    if policy["form_change_mechanics"] != "deferred":
        fail("capacity manifest unexpectedly enables form changes")
    if policy["speculative_generation_10_content"]:
        fail("capacity manifest must not invent Generation 10 content")

    if rom_limit["result"]["maximum_directly_addressable_mib"] != 32:
        fail("ROM-size probe no longer agrees with 32 MiB hard limit")

    if audit["basis"]["local_pairs"] != 7:
        fail("ROM/SAV audit must contain seven source profiles")
    if audit["save_layout"]["spare_physical_sectors"] != 0:
        fail("retail Flash layout must not claim spare sectors")
    japan_observed = audit["observed_save_checksum_profiles"]["Japan_BPGJ_active_slot"]
    if japan_observed["rom_header_save_block1_size"] != "0x3D40":
        fail("Japanese ROM-header SaveBlock1 size evidence changed")
    if japan_observed["observed_checksum_save_block1_span"] != "0x3D68":
        fail("Japanese supplied SAV checksum-span evidence changed")

    with INVENTORY.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 7:
        fail(f"expected seven core-table inventory rows, got {len(rows)}")
    if len({row["sha256"] for row in rows}) != 7:
        fail("core-table inventory ROM hashes are not unique")
    if any(row["gf_header_offset"] != "0x00000100" for row in rows):
        fail("GFRomHeader offset drifted from 0x100")
    if any(row["pokedex_count"] != "386" for row in rows):
        fail("retail National Dex count evidence changed")
    if any(row["saveblock2_header_size"] != "0xF24" for row in rows):
        fail("SaveBlock2 GFRomHeader size differs across inventory")

    japan = [row for row in rows if row["game_code"] == "BPGJ"]
    if len(japan) != 1 or japan[0]["saveblock1_header_size"] != "0x3D40":
        fail("Japanese core-table inventory must preserve SaveBlock1 0x3D40")
    international = [row for row in rows if row["game_code"] != "BPGJ"]
    if any(row["saveblock1_header_size"] != "0x3D68" for row in international):
        fail("international core-table inventory must use SaveBlock1 0x3D68")

    for field in (
        "species_info_offset",
        "ability_names_offset",
        "ability_descriptions_offset",
        "items_offset",
        "moves_offset",
        "species_names_offset",
        "move_names_offset",
        "evolution_offset",
    ):
        if len({row[field] for row in rows}) != 7:
            fail(f"{field}: per-profile relocation evidence unexpectedly collapsed")

    with REFERENCE_AUDIT.open(newline="", encoding="utf-8") as f:
        refs = list(csv.DictReader(f))
    if len(refs) != 7 * len(EXPECTED_TABLES):
        fail(f"expected 56 table-reference rows, got {len(refs)}")
    if {row["table"] for row in refs} != EXPECTED_TABLES:
        fail("reference audit table set changed")
    per_file = Counter(row["file"] for row in refs)
    if any(count != len(EXPECTED_TABLES) for count in per_file.values()) or len(per_file) != 7:
        fail("reference audit does not contain eight tables for every source ROM")

    evolution = [row for row in refs if row["table"] == "evolutionTable"]
    if any(int(row["base_reference_count"]) != 0 for row in evolution):
        fail("evolution table unexpectedly gained a simple base-pointer reference")
    if any(int(row["interior_reference_count"]) <= 0 for row in evolution):
        fail("evolution relocation risk evidence disappeared")

    ability_names = [row for row in refs if row["table"] == "abilityNames"]
    if any(int(row["base_reference_count"]) <= 0 for row in ability_names):
        fail("ability-name base references were not found")
    if any(int(row["interior_reference_count"]) != 0 for row in ability_names):
        fail("ability-name table gained interior reference candidates; review relocation policy")

    print("LEAFGREEN future-generation readiness verified")
    print("  source profiles       : 7")
    print("  content generation    : 9")
    print("  reserved generation   : 10")
    print("  behavior generation   : GEN_9")
    print("  form-change work      : deferred")
    print("  standard ROM ceiling  : 32 MiB")
    print("  save flash            : 128 KiB / 32 sectors")
    print("  modern-core pin       :", EXPECTED_EXPANSION_REF)
    print("  core table inventory  : region/revision-specific")
    print("  reference audit       : 56 table/profile rows")
    print("  evolution relocation  : instruction/literal review required")
    print("  Japanese save warning : header 0x3D40 / supplied active checksum 0x3D68")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
