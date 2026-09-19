# LEAFGREEN

Pokémon LeafGreen ROM research and reproducible patch tooling. ROM binaries are not stored in this repository.

## Always-on external event content

Current patch policy removes the external distribution dependency while preserving normal story progression:

- **MysticTicket / Navel Rock** — the Seagallop destination check always succeeds once the normal late-game Sevii ferry menu is available.
- **AuroraTicket / Birth Island** — same policy; Deoxys remains a normal one-time encounter controlled by the game's own encounter flags.
- **Altering Cave** — all nine programmed selector tables are replaced with one permanent merged encounter table, so the unreleased Wonder Spot rotation is no longer required.
- **Save compatibility** — no save-format change. Existing and new saves use the ROM-side behavior.

The patch intentionally does **not** bypass the ordinary Sevii story/Rainbow Pass progression. It removes the external-event requirement, not the game's main progression.

## Files

- `tools/patch_external_events.py` — signature-checked patcher for the supported Japanese, North American and European LeafGreen ROM revisions.
- `patches/` — IPS patches generated from the verified clean ROMs.
- `manifests/leafgreen_roms.json` — original/patched SHA-256 values and discovered offsets.
- `docs/external-events.md` — technical scope and source rationale.
- `checksums/SHA256SUMS.txt` — patch and manifest/tool hashes.

## Usage

```bash
python tools/patch_external_events.py "Pocket Monsters - Leaf Green (Japan).gba"
```

The script refuses unknown or already modified ROM hashes.
