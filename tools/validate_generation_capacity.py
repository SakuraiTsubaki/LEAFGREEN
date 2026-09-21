#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "manifests" / "generation_capacity.json"


def required_bits(max_id: int) -> int:
    if max_id < 0:
        raise ValueError("max_id must be non-negative")
    return max(1, math.ceil(math.log2(max_id + 1)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "manifest",
        nargs="?",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="capacity manifest (default: manifests/generation_capacity.json)",
    )
    args = ap.parse_args()

    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    observed = data["observed_reference_maxima"]
    contract = data["capacity_contract"]

    errors: list[str] = []
    checked = 0

    for domain in ("species", "moves", "abilities", "items"):
        obs = int(observed[domain]["max_id"])
        cfg = contract[domain]
        max_id = int(cfg["max_id"])
        entries = int(cfg["entries"])
        bits = int(cfg["id_bits"])

        if obs > max_id:
            errors.append(f"{domain}: observed max {obs} exceeds contract max {max_id}")
        if entries != max_id + 1:
            errors.append(f"{domain}: entries {entries} != max_id + 1 ({max_id + 1})")
        if entries & (entries - 1):
            errors.append(f"{domain}: entries {entries} is not a power of two")
        if bits < required_bits(max_id):
            errors.append(
                f"{domain}: {bits} bits cannot represent contract max {max_id} "
                f"(needs {required_bits(max_id)})"
            )
        checked += 1

    for domain, cfg in contract.items():
        max_id = int(cfg["max_id"])
        entries = int(cfg["entries"])
        bits = int(cfg["id_bits"])
        if entries != max_id + 1:
            errors.append(f"{domain}: entries {entries} != max_id + 1 ({max_id + 1})")
        if bits < required_bits(max_id):
            errors.append(
                f"{domain}: {bits} bits cannot represent contract max {max_id} "
                f"(needs {required_bits(max_id)})"
            )

    policy = data["policy"]
    if int(policy["current_rom_size_bytes"]) != 16 * 1024 * 1024:
        errors.append("current ROM size must remain 16 MiB for the clean-input baseline")
    if int(policy["expanded_rom_size_bytes"]) != 32 * 1024 * 1024:
        errors.append("expanded ROM target must be 32 MiB")
    if policy["form_change_mechanics"] != "deferred":
        errors.append("form-change mechanics must remain deferred in this phase")

    if errors:
        print("generation-capacity validation FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print("generation-capacity validation OK")
    print(f"- observed domains checked: {checked}")
    for domain in ("species", "moves", "abilities", "items"):
        obs = observed[domain]["max_id"]
        cap = contract[domain]["max_id"]
        print(f"- {domain}: observed {obs}, reserved through {cap}")
    print("- form-change mechanics: deferred")
    print("- ROM target: 16 MiB -> 32 MiB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
