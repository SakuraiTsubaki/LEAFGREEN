# External event policy

## Ticket islands: keep the actual tickets

The previous implementation forced the Vermilion ferry ticket-check subroutines to return TRUE.
That is intentionally replaced by a more faithful item-based policy.

Vanilla LeafGreen checks both an event-enable flag and the corresponding Key Item:

- `FLAG_ENABLE_SHIP_NAVEL_ROCK` + `ITEM_MYSTIC_TICKET`
- `FLAG_ENABLE_SHIP_BIRTH_ISLAND` + `ITEM_AURORA_TICKET`

For permanent availability, the patched check routine now does this instead:

1. check whether the Key Item is already owned;
2. if it is owned, return TRUE normally;
3. if it is missing, call the normal `additem` script command for one ticket;
4. check the bag again and return the real result.

This means the player **actually owns the ticket**. No duplicate ticket is added when it is already present.
If the Key Items pocket cannot accept the ticket, the destination remains unavailable until the item can be added.

The ordinary late-game Sevii / Rainbow Pass branch that reaches the ferry menu is not bypassed.
Ho-Oh, Lugia and Deoxys encounter flags/puzzle state are unchanged.

## Altering Cave

LeafGreen contains nine programmed Altering Cave selectors: the baseline Zubat table plus event
tables for Mareep, Pineco, Houndour, Teddiursa, Aipom, Shuckle, Stantler and Smeargle. The
Mystery Event script would normally advance `VAR_ALTERING_CAVE_WILD_SET`; the intended
Wonder Spot distribution was never released.

For permanent availability, every selector table is rewritten to the same merged 12-slot table.
Therefore old saves with any selector value and new saves with the default selector all expose
the same complete species pool.

Vanilla land-slot weights are preserved: `20, 20, 10, 10, 10, 10, 5, 5, 4, 4, 1, 1`.

| Slot | Pokémon | Rate | Level |
|---:|---|---:|---:|
| 0 | Mareep | 20% | 7 |
| 1 | Pineco | 20% | 25 |
| 2 | Houndour | 10% | 14 |
| 3 | Teddiursa | 10% | 26 |
| 4 | Aipom | 10% | 22 |
| 5 | Shuckle | 10% | 24 |
| 6 | Stantler | 5% | 28 |
| 7 | Smeargle | 5% | 18 |
| 8-11 | Zubat | 10% total | 8 / 14 / 8 / 14 |

## Separate external-data path: Trainer Tower e-Reader

Japanese FireRed/LeafGreen also accepts Trainer Tower Battle-e card data. This is not the same
mechanism as the wireless ticket distributions or Altering Cave selector.

The public decompilation contains 32 card-derived international `TrainerTowerFloor` records,
mapped in `manifests/trainer_tower_cards.json`. Japanese e-Reader records use a 980-byte floor
layout while international records use 992 bytes, so direct byte copying is not safe. See
`docs/trainer-tower-ereader.md`.

## Reference source paths

Public `pret/pokefirered` paths used to derive the patch logic:

- `data/maps/VermilionCity/scripts.inc`
- `data/mystery_event_msg.s`
- `src/wild_encounter.c`
- `src/data/wild_encounters.json`
- `include/constants/flags.h`
- `include/constants/vars.h`
- `src/trainer_tower.c`
- `src/trainer_tower_sets.c`
- `src/cereader_tool.c`
- `include/cereader_tool.h`
