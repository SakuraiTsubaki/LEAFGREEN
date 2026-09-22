# LEAFGREEN

Pokémon LeafGreen ROM research and reproducible patch tooling. ROM binaries and save binaries are not stored in this repository.

## Generation 10 readiness — source adapter + ROM/SAV first

**Form-change mechanics are deferred.** Expansion work is based on the actual seven LeafGreen ROM/SAV pairs.

LEAFGREEN is now connected to the Generation III superset coordinated by `SakuraiTsubaki/EMERALD`.
The pinned modern runtime is `rh-hideout/pokeemerald-expansion@75b806a3ab57a81ff1eb6179288981f0b3cc3050`.
Current content remains Gen 9, Generation 10 is reserved, behavior remains `GEN_9`, and speculative Gen 10 content is forbidden.

The retail source adapter is now reproducible:

- `tools/extract_leafgreen_core_tables.py` parses the Game Freak ROM header at file offset `0x100`;
- `manifests/core_table_inventory.csv` records seven separate regional/revision profiles;
- species/ability/item/move/name table addresses are taken from each ROM instead of copied across regions;
- the evolution table is located from a source-derived binary prefix and is marked for instruction/literal-pool relocation review.


### Verified maximum ROM size: 32 MiB

The standard LeafGreen/GBA ROM mapping has a **32 MiB hard limit**.

- clean LeafGreen ROM: 16 MiB;
- expanded LeafGreen ROM: **32 MiB maximum**;
- unique ROM addresses: `0x08000000..0x09FFFFFF`;
- `0x0A000000..` and `0x0C000000..` are other waitstate views of the same 32 MiB ROM, not extra storage;
- 64/96/128 MiB test files can be created, but their bytes after 32 MiB are not uniquely addressable without a custom mapper/banking system.

The Japanese ROM was actually padded and hashed at 32/64/96/128 MiB. Results are in `manifests/rom_size_limit_probe.json`.

Use `tools/probe_rom_size_limit.py` to reproduce the probe.

### Save boundary

All seven supplied saves are 128 KiB FLASH1M saves.

- sectors 0..27: two rotating main slots;
- sectors 28..29: Hall of Fame;
- sectors 30..31: Trainer Tower/e-Reader;
- spare physical sectors: **0**;
- physical save size remains **128 KiB**.

`SaveBlock2::filler_B20[0x400]` is zero in all seven active saves and is reserved for a 4096-species extended Pokédex:

- 4096 seen bits = 512 bytes;
- 4096 owned bits = 512 bytes.

See `manifests/rom_save_audit.json`, `manifests/generation_capacity.json`, and `docs/generation-10-readiness.md`.

### Japanese save evidence

The Japanese BPGJ ROM GFRomHeader reports `SaveBlock1 = 0x3D40`, while the supplied newest Japanese SAV slot (counter 356) validates its section-4 checksum only with a `0x3D68` span.
Both observations are preserved. `tools/expand_rom_capacity.py` tests the ROM-header size and the observed compatibility span instead of silently normalizing one into the other.

## Retail core-table source adapter

The seven-profile inventory is `manifests/core_table_inventory.csv`. Example offsets:

| Profile | Species info | Items | Moves | Evolution |
| --- | ---: | ---: | ---: | ---: |
| Japan BPGJ | `0x211168` | `0x3A0568` | `0x20D5E8` | `0x216164` |
| USA BPGE Rev 0 | `0x254760` | `0x3DAE64` | `0x250BE0` | `0x25975C` |
| Europe BPGE Rev 1 | `0x2547D0` | `0x3DAED4` | `0x250C50` | `0x2597CC` |

Absolute addresses are profile-specific and must never be reused across regions/revisions.

### First actual upper-ROM relocation

`abilityNames` is the first table moved by the binary expansion path. Across all seven supported profiles it has exactly four verified base-pointer sites and no aligned interior-reference candidates.

`tools/relocate_ability_names.py` copies the 1,014-byte table to file `0x010029D8` / ROM `0x090029D8`, preserves the original table, rewrites only the four verified pointer words, and verifies the relocated bytes and pointer counts.

Static validation is complete for all seven ROM/SAV pairs (`manifests/ability_names_relocation_validation.json`). Emulator runtime smoke testing is still pending.

## ROM expansion tools

`tools/expand_rom_capacity.py` requires both the ROM and its SAV. It validates the save-sector/checksum structure before expanding the ROM, and it never changes the SAV.

```bash
python tools/validate_generation_capacity.py

python tools/expand_rom_capacity.py \
  "Pocket Monsters - Leaf Green (Japan).gba" \
  "Pocket Monsters - Leaf Green (Japan).sav" \
  --report leafgreen-rom-save-expansion.json
```

The original 16 MiB is preserved byte-for-byte and the second 16 MiB starts as `0xFF`.

For maximum-size probing:

```bash
python tools/probe_rom_size_limit.py \
  "Pocket Monsters - Leaf Green (Japan).gba" \
  --out-dir probes \
  --report rom-size-probe.json
```

## Emerald item-parameter baseline

All item gameplay parameters are standardized against **Pokémon Emerald** across the canonical item range **0..376**.

See `manifests/emerald_item_parameters.json` and `docs/emerald-item-parameters.md`.

## Always-on external event content

- MysticTicket / Navel Rock — permanent Pallet Town delivery NPC.
- AuroraTicket / Birth Island — same NPC.
- Vanilla story progression remains intact.
- Altering Cave — nine selector tables replaced by one permanent merged table.
- No save-format enlargement.

Supported clean ROMs: Japanese, USA, Europe Rev 1, German, French, Italian and Spanish.

## Trainer Tower / e-Reader

Trainer Tower remains a separate workstream:

- `manifests/trainer_tower_cards.json`
- `tools/extract_trainer_tower_cards.py`
- `docs/trainer-tower-ereader.md`

Sectors 30 and 31 remain reserved.

## Key files

- `manifests/rom_size_limit_probe.json` — 32/64/96/128 MiB size-boundary probe.
- `tools/probe_rom_size_limit.py` — reproducible ROM-size probe.
- `manifests/rom_save_audit.json` — seven real ROM/SAV pair audit.
- `manifests/generation_capacity.json` — evidence-based expansion constraints.
- `tools/validate_generation_capacity.py` — validates the 32 MiB ROM / 128 KiB SAV policy.
- `tools/expand_rom_capacity.py` — validates ROM + SAV, then expands only the ROM to 32 MiB.
- `docs/generation-10-readiness.md` — expansion design and hard limits.

Next: fit the modernized data structures **inside the 32 MiB ceiling**, then resume form-change work later.
