# LEAFGREEN

Pokémon LeafGreen ROM research and reproducible patch tooling. ROM binaries are not stored in this repository.

## Emerald item-parameter baseline

All item gameplay parameters are standardized against **Pokémon Emerald** across the full
canonical item range **0..376**. This applies to every item, not only event tickets.

See `manifests/emerald_item_parameters.json` and `docs/emerald-item-parameters.md`.
LeafGreen-specific bag containers and code addresses are treated as engine adapters so Emerald
semantics are preserved without copying invalid raw pointers or enum values.

## Always-on external event content

Current ROM patch policy:

- **MysticTicket / Navel Rock** — a permanent Mystery Gift Deliveryman NPC is added to Pallet Town. Talking to him gives the real MysticTicket if it is missing and sets the same ship/received flags as the original distribution.
- **AuroraTicket / Birth Island** — the same Pallet Town NPC gives the real AuroraTicket if it is missing and sets the original distribution flags.
- **Original story logic stays intact** — the Vermilion ferry ticket checks are no longer forced or rewritten. The player simply owns the legitimate Key Items from the beginning area; ordinary Sevii / Rainbow Pass progression still controls when the relevant ferry menu is reachable.
- **Altering Cave** — all nine programmed selector tables are replaced by one permanent merged encounter table, removing the unreleased Wonder Spot dependency.
- **Save compatibility** — no save-format change. Existing and new saves use the ROM-side behavior.

The added NPC uses the game's existing **Mystery Gift Deliveryman** overworld graphic and the standard localized item-obtain routine, so Japanese, English, German, French, Italian and Spanish ROMs display their own native item names/messages without new translated text.

Supported clean ROMs: Japanese, USA, Europe Rev 1, German, French, Italian and Spanish LeafGreen.

## Trainer Tower / e-Reader

Trainer Tower e-Reader data remains a separate external-data workstream:

- `manifests/trainer_tower_cards.json`
- `tools/extract_trainer_tower_cards.py`
- `docs/trainer-tower-ereader.md`

The ticket-NPC change does not alter these files or Trainer Tower save sectors.

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
