# Trainer Tower / Battle-e external-data inventory

## What is external in Japanese FireRed/LeafGreen

The Japanese games support Pokémon Battle Card e+ data for Trainer Tower. Nintendo's official
product page describes 44 cards total: 32 Trainer cards and 12 target-time cards. The 32 Trainer
cards alter the Trainer Tower opponents; up to eight Trainer cards can be used for a run.

The international FireRed/LeafGreen implementation internalized card-derived Trainer Tower
content. In `pret/pokefirered`, `src/trainer_tower_sets.c` contains 32 distinct `TrainerTowerFloor`
records in the same declaration order as card IDs `15-A001` through `15-A032`.

## Binary inventory

For the clean USA LeafGreen ROM used by this project:

- SHA-256: `78d310d557ceebc593bd393acc52d1b19a8f023fec40bc200e6063880d8531fc`
- 32-floor block start: `0x47A488`
- International floor size: `0x3E0` (992 bytes)
- Total block size: `0x7C00`

`tools/extract_trainer_tower_cards.py` extracts those 32 records without storing ROM data in this repository.

## Japanese-layout caveat

Research on the original e-Reader transfer format documents that Japanese Trainer Tower records
use a 980-byte floor structure, while international games use 992 bytes. Therefore the
international 992-byte records must **not** be blindly copied into the Japanese ROM or save.

The next ROM-side integration must preserve:

1. the Japanese 980-byte structure;
2. Japanese trainer-name encoding;
3. Japanese Pokémon nickname text;
4. per-floor checksum semantics;
5. the original four-color card groups / card order so all 32 Trainer cards remain selectable
   without an e-Reader.

## Card map

See `manifests/trainer_tower_cards.json` for the complete 15-A001..15-A032 mapping to the
decompilation floor declarations, trainer names, battle types, and prizes.

## Sources

- Nintendo/Pokémon official product page: Pokémon Battle Card e+ FireRed & LeafGreen.
- `pret/pokefirered`: `src/trainer_tower_sets.c`, `src/trainer_tower.c`, `src/cereader_tool.c`,
  `include/cereader_tool.h`.
- Preserved e-Reader reverse-engineering notes documenting the 980-byte Japanese vs 992-byte
  international Trainer Tower structures.
