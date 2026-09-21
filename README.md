# LEAFGREEN

Pokémon LeafGreen ROM research and reproducible patch tooling. ROM binaries and save binaries are not stored in this repository.

## Generation 10 readiness — ROM + SAV first

**Form-change mechanics are deferred.** Expansion work is based on the actual seven LeafGreen ROM/SAV pairs.

Current verified foundation:

- seven clean ROMs: 16 MiB each;
- seven saves: 128 KiB each;
- every ROM contains `FLASH1M_V103`;
- save sectors 0..27 are the two rotating main slots;
- sectors 28..29 are Hall of Fame;
- sectors 30..31 are Trainer Tower/e-Reader;
- there are no spare physical save sectors;
- ROM expansion target: 32 MiB;
- save physical size: remains 128 KiB.

See `manifests/rom_save_audit.json` and `docs/generation-10-readiness.md`.

### Extended Pokédex space

The seven active saves were reconstructed and checked. `SaveBlock2` field `filler_B20[0x400]` is 1024 bytes and is all-zero in every sample.

Phase 1 reserves this existing checksummed field for:

- 4096 seen bits = 512 bytes;
- 4096 owned bits = 512 bytes.

This gives a 4096-species Pokédex envelope **without enlarging the 128 KiB save file or stealing Hall of Fame / Trainer Tower sectors**.

Species, held-item and move IDs inside stored Pokémon are already `u16`. The immediate blockers are the 9-bit level-up move encoding, 8-bit ability/effect runtime paths, and the one-bit boxed ability selector.

## ROM expansion tool

`tools/expand_rom_capacity.py` now requires a ROM **and its SAV**. It validates the save-sector/checksum structure before expanding the ROM.

The SAV is never modified by this tool.

```bash
python tools/validate_generation_capacity.py

python tools/expand_rom_capacity.py \
  "Pocket Monsters - Leaf Green (Japan).gba" \
  "Pocket Monsters - Leaf Green (Japan).sav" \
  --report leafgreen-rom-save-expansion.json
```

The 16 MiB ROM prefix is preserved byte-for-byte and the new upper 16 MiB starts as `0xFF`.

## Emerald item-parameter baseline

All item gameplay parameters are standardized against **Pokémon Emerald** across the full canonical item range **0..376**. This applies to every item, not only event tickets.

See `manifests/emerald_item_parameters.json` and `docs/emerald-item-parameters.md`. LeafGreen-specific bag containers and code addresses are engine adapters; Emerald semantics are preserved without copying invalid raw pointers or enum values.

## Always-on external event content

Current ROM patch policy:

- **MysticTicket / Navel Rock** — a permanent Mystery Gift Deliveryman NPC is added to Pallet Town and gives the real ticket when missing.
- **AuroraTicket / Birth Island** — the same NPC gives the real ticket when missing.
- **Original story logic stays intact** — normal Sevii / Rainbow Pass progression still controls ferry access.
- **Altering Cave** — all nine programmed selector tables are replaced by one permanent merged encounter table.
- **Save compatibility** — no save-format enlargement.

Supported clean ROMs: Japanese, USA, Europe Rev 1, German, French, Italian and Spanish LeafGreen.

## Trainer Tower / e-Reader

Trainer Tower e-Reader data remains a separate external-data workstream:

- `manifests/trainer_tower_cards.json`
- `tools/extract_trainer_tower_cards.py`
- `docs/trainer-tower-ereader.md`

Save sectors 30 and 31 remain reserved for this system.

## Key files

- `manifests/rom_save_audit.json` — seven real ROM/SAV pair audit.
- `manifests/generation_capacity.json` — evidence-based expansion constraints.
- `tools/validate_generation_capacity.py` — validates the ROM/save expansion policy.
- `tools/expand_rom_capacity.py` — validates ROM + SAV, then expands only the ROM to 32 MiB.
- `docs/generation-10-readiness.md` — save-compatible expansion design.
- `tools/patch_external_events.py` — external-event ROM patcher.
- `manifests/leafgreen_roms.json` — original/patched ROM SHA-256 and offsets.
- `patches/` — generated IPS patches.

The next implementation target is the extended Pokédex block and table/pointer relocation. Form-change mechanics remain on hold.
