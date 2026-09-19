# External event policy

## Scope

This patch internalizes FireRed/LeafGreen game content whose normal activation depends on Mystery Gift / Wonder Spot distribution. It does not turn every internal Mystery Gift test/helper script into retail content.

### MysticTicket → Navel Rock

Vanilla Vermilion City ferry logic requires both `FLAG_ENABLE_SHIP_NAVEL_ROCK` and `ITEM_MYSTIC_TICKET`. The patch replaces the ticket-check subroutine with `VAR_RESULT = TRUE; return`. Normal Sevii ferry progression is retained. Ho-Oh and Lugia encounter flags are unchanged.

### AuroraTicket → Birth Island

Vanilla ferry logic similarly requires `FLAG_ENABLE_SHIP_BIRTH_ISLAND` and `ITEM_AURORA_TICKET`. The same always-true subroutine policy is applied. Deoxys encounter/puzzle state is otherwise unchanged.

### Altering Cave

The retail engine contains nine selector tables: the baseline Zubat table plus eight additional tables for Mareep, Pineco, Houndour, Teddiursa, Aipom, Shuckle, Stantler and Smeargle. The Mystery Event script increments `VAR_ALTERING_CAVE_WILD_SET`; public documentation notes that the Wonder Spot distribution intended to alter the cave was never released.

For permanent availability, every one of the nine selector tables is rewritten to the same merged 12-slot table. Therefore old saves with any selector value and new saves with the default selector all see identical content.

Vanilla land-slot weights are preserved: `20, 20, 10, 10, 10, 10, 5, 5, 4, 4, 1, 1`. The merged assignment is:

| Slots | Pokémon | Combined rate | Level(s) |
|---|---|---:|---|
| 0 | Mareep | 20% | 7 |
| 1 | Pineco | 20% | 25 |
| 2 | Houndour | 10% | 14 |
| 3 | Teddiursa | 10% | 26 |
| 4 | Aipom | 10% | 22 |
| 5 | Shuckle | 10% | 24 |
| 6 | Stantler | 5% | 28 |
| 7 | Smeargle | 5% | 18 |
| 8-11 | Zubat | 10% total | 8/14/8/14 |

The chosen levels come from the corresponding vanilla programmed tables.

## Deliberately excluded from this patch

`mystery_event_msg.s` also contains generic/unused Mystery Gift infrastructure such as Stamp Card, Battle Card, Visiting Trainer and Surf Pichu helper scripts. They are not automatically promoted to always-on retail events without evidence that a concrete LeafGreen distribution used them.

Japanese Trainer Tower e-Reader card loading is a separate external-data facility rather than the MysticTicket/AuroraTicket/Wonder Spot event-gating path. It is tracked separately so that importing card data does not get conflated with event-island activation.

## Reference source paths

The implementation was derived against the public `pret/pokefirered` decompilation, especially:

- `data/maps/VermilionCity/scripts.inc`
- `data/mystery_event_msg.s`
- `src/wild_encounter.c`
- `src/data/wild_encounters.json`
- `include/constants/flags.h`
- `include/constants/vars.h`
