# LEAFGREEN

Pokémon LeafGreen ROM research and reproducible patch tooling. ROM binaries are not stored in this repository.

## Always-on external event content

Current ROM patch policy:

- **MysticTicket / Navel Rock** — the ticket remains a real Key Item. When the normal late-game Vermilion ferry check first needs it, a missing MysticTicket is inserted into the Key Items pocket, then the normal item check is used.
- **AuroraTicket / Birth Island** — same policy for AuroraTicket.
- **Altering Cave** — all nine programmed selector tables are replaced by one permanent merged encounter table, removing the unreleased Wonder Spot dependency.
- **Story compatibility** — ordinary Sevii / Rainbow Pass progression is preserved; legendary one-time encounter state is unchanged.
- **Save compatibility** — no save-format change. Existing and new saves use the ROM-side behavior.

Supported clean ROMs: Japanese, USA, Europe Rev 1, German, French, Italian and Spanish LeafGreen.

## Trainer Tower / e-Reader

The Japanese games' Trainer Tower has a separate e-Reader external-data path. Research and extraction tooling is tracked separately:

- `manifests/trainer_tower_cards.json` maps card IDs `15-A001`..`15-A032` to the 32 card-derived floor records in the public decompilation.
- `tools/extract_trainer_tower_cards.py` extracts the corresponding 32 international floor records from a user-supplied clean USA LeafGreen ROM.
- `docs/trainer-tower-ereader.md` records the Japanese 980-byte vs international 992-byte structure constraint. International data is **not** blindly injected into the Japanese ROM.

## Files

- `tools/patch_external_events.py` — signature-checked patcher for the seven supported clean ROMs.
- `patches/` — IPS patches generated from the verified clean ROMs.
- `manifests/leafgreen_roms.json` — original/patched SHA-256 values and discovered offsets.
- `docs/external-events.md` — event policy and technical rationale.
- `checksums/SHA256SUMS.txt` — repository artifact hashes.

## Usage

```bash
python tools/patch_external_events.py "Pocket Monsters - Leaf Green (Japan).gba"
```

The patcher refuses unknown or already-modified ROM hashes.
