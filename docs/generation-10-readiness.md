# Generation 10 readiness from real LeafGreen ROM/SAV pairs

## Decision

Form-change mechanics remain deferred.

Generation expansion is based on the seven supplied LeafGreen ROM/SAV pairs, not on capacity guesses. The project keeps the retail 128 KiB FLASH1M save layout and expands the ROM only to the maximum standard GBA/LeafGreen directly addressable size: **32 MiB**.

Evidence is recorded in:

- `manifests/rom_save_audit.json`
- `manifests/generation_capacity.json`
- `manifests/rom_size_limit_probe.json`

## ROM hard limit

The seven clean ROMs are exactly 16 MiB.

The pinned `pret/pokefirered` linker script defines:

- ROM origin: `0x08000000`
- ROM length: `32M`

mGBA's current GBA memory model defines each Game Pak ROM window as `0x02000000` bytes (32 MiB). ROM0, ROM1 and ROM2 are three waitstate views of the same ROM data:

- ROM0: `0x08000000..0x09FFFFFF`
- ROM1: `0x0A000000..0x0BFFFFFF`
- ROM2: `0x0C000000..0x0DFFFFFF`

They are **not 96 MiB of independent storage**. Cartridge reads mask the address into the same 32 MiB ROM buffer.

For ordinary non-Matrix ROMs such as LeafGreen `BPG*`, mGBA also clamps ROM files larger than 32 MiB to the first 32 MiB when loading.

Therefore:

**32 MiB is the hard limit for a standard LeafGreen ROM image.**

The usable unique address range is:

- file offsets: `0x0000000..0x1FFFFFF`
- CPU ROM addresses: `0x08000000..0x09FFFFFF`

The original 16 MiB occupies the lower half. The new 16 MiB occupies:

- file offsets: `0x1000000..0x1FFFFFF`
- CPU addresses: `0x09000000..0x09FFFFFF`

The seven-ROM comparison also found common all-`0xFF` regions inside the original 16 MiB, but the external-event patch already uses part of that space at `0x800000`.

## Oversize probe

A real Japanese LeafGreen ROM was padded and hashed at four file sizes:

- 32 MiB
- 64 MiB
- 96 MiB
- 128 MiB

All four files can physically exist on disk. However, only the first 32 MiB are uniquely addressable with standard LeafGreen/GBA mapping.

The 64/96/128 MiB files therefore prove only that a host filesystem can hold a larger file. Their extra bytes do not create additional standard GBA ROM addresses.

Using more than 32 MiB would require a deliberate **custom mapper or bank-switching design**, plus matching emulator/flashcart support. That is a different architecture and is not treated as ordinary LeafGreen compatibility.

Reproduce the file-size probe with:

```sh
python tools/probe_rom_size_limit.py \
  "Pocket Monsters - Leaf Green (Japan).gba" \
  --out-dir probes \
  --report rom-size-probe.json
```

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

The 2212 bytes are not phase-1 extension space because retail checksums use the original per-section sizes.

## Safe phase-1 save extension

The source contains already-checksummed unused fields, and the seven active saves were checked byte-for-byte.

`SaveBlock2 + 0xB20` is exactly 1024 bytes (`filler_B20[0x400]`) and was all-zero in every supplied active save.

It is reserved for:

- 4096 seen bits = 512 bytes
- 4096 owned bits = 512 bytes

This provides a 4096-species Pokédex envelope while keeping the physical save at 128 KiB.

Additional verified-zero fields remain reserved:

- `SaveBlock1 + 0x348C`: 400 bytes
- `SaveBlock1 + 0x3A94`: 64 bytes
- `SaveBlock1 + 0x3D24`: 16 bytes
- `SaveBlock1 + 0x0632`: 6 bytes

## Pokémon entity widths

Retail saved Pokémon already store:

- species as `u16`
- held item as `u16`
- four moves as `u16`

The principal blockers are instead:

- one-bit boxed ability selector;
- `SpeciesInfo.abilities[2]` using `u8`;
- `BattlePokemon.ability` using `u8`;
- 9-bit `LevelUpMove.move`;
- `BattleMove.effect` using `u8`.

326 populated Pokémon from the supplied saves were decrypted during the audit. Their retail unused-ribbon nibble was zero in all checked cases, but those bits are not repurposed yet.

## Tool policy

`tools/expand_rom_capacity.py` requires a ROM and its SAV, verifies the save structure, leaves the SAV byte-for-byte unchanged, and expands only the ROM to **32 MiB**.

```sh
python tools/validate_generation_capacity.py

python tools/expand_rom_capacity.py \
  "Pocket Monsters - Leaf Green (Japan).gba" \
  "Pocket Monsters - Leaf Green (Japan).sav" \
  --report leafgreen-rom-save-expansion.json
```

## Next binary work

1. implement the 4096-species extended Pokédex block in the existing 0x400-byte SaveBlock2 filler;
2. inventory every species/move/item/ability/type/evolution table and every pointer in each regional ROM;
3. pack and relocate large append-only tables inside the **32 MiB hard limit**;
4. replace the 9-bit level-up move encoding;
5. widen ability/effect runtime paths where needed;
6. preserve the 128 KiB save and both rotating slots;
7. only then resume form-change mechanics.
