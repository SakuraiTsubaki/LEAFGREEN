# Generation 10 readiness: expansion before form changes

## Decision

Form-change mechanics are deferred.

The first priority is to make LeafGreen structurally capable of accepting later-generation data without having to redesign the identifier space again when Generation 10 data arrives. This phase does **not** claim that modern species, moves, abilities, items, or forms are already playable.

The work is split into two layers:

1. **physical ROM capacity** — expand a verified 16 MiB LeafGreen image to 32 MiB while preserving the original 16 MiB byte-for-byte;
2. **engine/data capacity** — reserve stable append-only ID spaces and audit every native table/field that must be relocated or widened.

## Reference ceiling

The capacity contract is pinned in `manifests/generation_capacity.json`.

The current normalized PKHeX reference already reaches:

- species ID 1025 — Pecharunt;
- move ID 920 — Nihil Light;
- ability ID 310 — Poison Puppeteer;
- item ID 2684 in the currently pinned Z-A / Mega Dimension reference ceiling.

These are reference maxima, not LeafGreen-native limits and not predictions for Generation 10.

## Reserved capacity

The project reserves deliberately larger power-of-two spaces:

| Domain | Reserved IDs | Entries | Required ID width |
| --- | ---: | ---: | ---: |
| Species | 0..4095 | 4096 | 16-bit |
| Moves | 0..2047 | 2048 | 16-bit |
| Abilities | 0..1023 | 1024 | 16-bit |
| Items | 0..8191 | 8192 | 16-bit |
| Types | 0..31 | 32 | 8-bit |
| Move effects | 0..1023 | 1024 | 16-bit |
| Evolution methods | 0..511 | 512 | 16-bit |
| Local form index | 0..255 | 256 | 8-bit, reserved only |

Existing FRLG/Emerald-compatible IDs remain stable. New IDs are append-only.

## Native LeafGreen blockers

The pinned `pret/pokefirered` reference shows that several important identifiers already use 16-bit storage:

- boxed Pokémon species: `u16`;
- held item: `u16`;
- moves: `u16`;
- battle species/item/moves: `u16`;
- evolution method/parameter/target species: `u16`.

Those paths do not need a new fundamental ID type merely to exceed the Generation III counts.

The first hard blockers are narrower fields and packed encodings:

- `BattlePokemon.ability` is `u8`;
- `SpeciesInfo.abilities[2]` stores ability IDs as `u8`;
- boxed Pokémon stores only a one-bit `abilityNum`, which selects two native ability slots;
- `BattleMove.effect` is `u8`;
- `LevelUpMove.move` is a 9-bit field, so it cannot represent move IDs above 511;
- Pokédex seen/caught bitfields scale from `NUM_SPECIES` and therefore require a save-layout strategy once the species table is expanded.

These must be solved before importing modern data at the reserved ceilings.

## Physical ROM expansion

`tools/expand_rom_capacity.py` expands any verified clean LeafGreen ROM, or a verified 16 MiB output from `tools/patch_external_events.py`, to 32 MiB.

The tool:

- verifies the lower 16 MiB by SHA-256;
- preserves those bytes exactly;
- fills file offsets `0x1000000..0x1FFFFFF` with `0xFF`;
- refuses a 32 MiB input if the expansion region already contains data;
- records the new ROM-address range as `0x09000000..0x09FFFFFF`.

This is only space reservation. No gameplay table is relocated by this step.

Recommended order for the current tools:

1. start from a verified clean 16 MiB ROM;
2. apply `tools/patch_external_events.py` if the external-event patch is wanted;
3. run `tools/expand_rom_capacity.py`;
4. later generation-table relocation patches may use the new upper 16 MiB.

## Expansion order

The next implementation work should proceed in this order:

1. inventory all species-, move-, ability-, item-, type-, evolution-, learnset-, graphics-, cry-, Pokédex-, and save-related tables;
2. replace the 9-bit level-up move encoding;
3. widen ability IDs and move-effect IDs to 16-bit runtime paths;
4. relocate append-only tables into the upper 16 MiB;
5. expand species/move/item/ability name and description tables;
6. expand Pokédex/save bitfields with an explicit backward-compatibility plan;
7. import later-generation data;
8. only after this foundation is stable, resume form-change mechanics.

## Validation

Run:

```sh
python tools/validate_generation_capacity.py
python tools/expand_rom_capacity.py "Pokemon - Leaf Green Version (USA).gba" --report leafgreen-32m.json
```

`validate_generation_capacity.py` fails if a pinned observed maximum exceeds the reserved contract, if a capacity does not fit its declared bit width, or if this phase accidentally stops marking form-change mechanics as deferred.
