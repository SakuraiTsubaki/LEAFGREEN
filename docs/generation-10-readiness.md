# Generation 10 readiness from real LeafGreen ROM/SAV pairs

## Decision

Form-change mechanics remain deferred.

Generation expansion is based on the seven supplied LeafGreen ROM/SAV pairs, not on capacity guesses. The project keeps the retail 128 KiB FLASH1M save layout and expands the ROM to the 32 MiB address window already declared by the pinned `pret/pokefirered` linker scripts.

Evidence is recorded in:

- `manifests/rom_save_audit.json`
- `manifests/generation_capacity.json`

## ROM evidence

All seven clean ROMs are exactly 16 MiB and contain `FLASH1M_V103`.

The seven-ROM byte comparison found these common all-`0xFF` ranges inside the original 16 MiB:

- `0x719B88..0xBFFFFF`
- `0xEB244C..0xEFFFFF`
- `0xFDFFFF..0xFFFFFF`

The current external-event patch already uses a small part of the first common region at `0x800000`, so future large tables should not assume the original free space is untouched.

The pinned linker scripts define:

- ROM origin: `0x08000000`
- ROM length: `32M`

Therefore the physical expansion target is 32 MiB. The new upper half is initially `0xFF`:

- file offsets: `0x1000000..0x1FFFFFF`
- ROM addresses: `0x09000000..0x09FFFFFF`

Relocated data tables and assets should prefer this upper half. Code placed there still requires ARM/Thumb branch-range review or veneers; 32 MiB space alone does not make every direct branch valid.

## Save evidence

Every supplied save is exactly 128 KiB.

Retail FRLG divides the 32 flash sectors as follows:

- sectors 0..13 — main save slot 1
- sectors 14..27 — main save slot 2
- sectors 28..29 — Hall of Fame
- sectors 30..31 — Trainer Tower / e-Reader

There are therefore **no spare physical save sectors**. Empty Trainer Tower sectors in a sample save are still reserved and must not be stolen for expansion.

The normal slot payload is:

- `SaveBlock2`: 0xF24 = 3876 bytes
- `SaveBlock1`: 0x3D68 = 15720 bytes
- `PokemonStorage`: 0x83D0 = 33744 bytes
- total payload per slot: 53340 bytes
- allocated section-data capacity per slot: 55552 bytes
- unused tail capacity: 2212 bytes

The 2212 bytes are **not** phase-1 extension space. Retail checksums use the original per-section sizes. Increasing those sizes would make an untouched old save fail checksum validation unless a legacy migration loader is added first.

## Safe phase-1 save extension

The source contains already-checksummed unused fields, and the seven active saves were checked byte-for-byte.

Most importantly:

- `SaveBlock2 + 0xB20`
- length `0x400` = 1024 bytes
- source field: `filler_B20[0x400]`
- all 1024 bytes are zero in all seven active saves

This gives an exact phase-1 extended Pokédex layout:

- 4096 seen bits = 512 bytes
- 4096 owned bits = 512 bytes
- total = 1024 bytes

The original Gen III seen/owned fields remain in place for compatibility. The extension block stores the expanded range and can mirror the native range where required.

Additional verified-zero source fields are reserved but not assigned yet:

- `SaveBlock1 + 0x348C`: 400 bytes
- `SaveBlock1 + 0x3A94`: 64 bytes
- `SaveBlock1 + 0x3D24`: 16 bytes
- `SaveBlock1 + 0x0632`: 6 bytes

## Pokémon entity widths

The retail Pokémon data already stores:

- species as `u16`
- held item as `u16`
- four moves as `u16`

So later species, item, and move IDs do not require a larger BoxPokemon structure merely because their IDs exceed Generation III counts.

The real blockers are narrower semantics:

- boxed ability selection is only one bit;
- `SpeciesInfo.abilities[2]` uses `u8` IDs;
- `BattlePokemon.ability` is `u8`;
- `LevelUpMove.move` is a 9-bit packed field;
- `BattleMove.effect` is `u8`.

326 populated party/storage Pokémon from the supplied saves were decrypted during the audit. Their four-bit retail `unusedRibbons` field was zero in every checked Pokémon, but those bits are **not being repurposed yet**. Ability-slot/form/interoperability migration must be designed separately.

## Tool policy

`tools/expand_rom_capacity.py` now requires both a ROM and a SAV.

It:

1. verifies the 16 MiB ROM hash;
2. validates the 128 KiB save size;
3. verifies the two 14-sector main save slots using retail section checksums;
4. records which slot is active;
5. records Hall of Fame and Trainer Tower sector occupancy;
6. leaves the SAV byte-for-byte unchanged;
7. expands only the ROM to 32 MiB.

Example:

```sh
python tools/expand_rom_capacity.py \
  "Pocket Monsters - Leaf Green (Japan).gba" \
  "Pocket Monsters - Leaf Green (Japan).sav" \
  --report leafgreen-rom-save-expansion.json
```

## Next binary work

The next phase is not form change.

1. implement the 4096-species extended Pokédex block in the existing 0x400-byte SaveBlock2 filler;
2. inventory every species/move/item/ability/type/evolution table and every pointer to those tables in each regional ROM;
3. relocate large append-only tables into the upper 16 MiB;
4. replace the 9-bit level-up move encoding before modern move IDs are imported;
5. widen ability/effect runtime paths where needed;
6. preserve 128 KiB save compatibility and both rotating main slots;
7. only after this layer is stable, return to form-change mechanics.
