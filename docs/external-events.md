# External event policy

## Ticket islands: Pallet Town delivery NPC

MysticTicket and AuroraTicket remain real Key Items. The ROM no longer forces the Vermilion ferry ticket checks to pass and no longer waits until the ferry is used to inject a missing ticket.

Instead, a fourth object event is added to **Pallet Town**:

- graphics: the game's existing `OBJ_EVENT_GFX_MG_DELIVERYMAN`;
- location: `(14, 12)`, near Professor Oak's lab without replacing an existing NPC;
- local id: `4`;
- permanent: no hide flag;
- interaction: uses the standard localized `STD_OBTAIN_ITEM` routine.

On interaction, the script independently handles each ticket:

1. if MysticTicket is missing, attempt to give `ITEM_MYSTIC_TICKET`;
2. if the item is present or the give succeeds, set `FLAG_ENABLE_SHIP_NAVEL_ROCK` and `FLAG_RECEIVED_MYSTIC_TICKET`;
3. if AuroraTicket is missing, attempt to give `ITEM_AURORA_TICKET`;
4. if the item is present or the give succeeds, set `FLAG_ENABLE_SHIP_BIRTH_ISLAND` and `FLAG_RECEIVED_AURORA_TICKET`;
5. if the Key Items pocket is full, the failed ticket's flags are not set; talking to the NPC later retries it.

This deliberately preserves the original ferry scripts and the ordinary Sevii / Rainbow Pass progression. The tickets can be owned early, but the main story still determines when the ferry path becomes reachable. Ho-Oh, Lugia and Deoxys one-time encounter/puzzle state is unchanged.

### Binary implementation

For each supported clean ROM the patcher:

- locates Pallet Town's three vanilla object-event records by structure/signature;
- locates the corresponding `MapEvents` record (`3` objects / `3` warps / `3` coord events / `5` bg events);
- copies the original three objects plus the new Deliveryman to verified unused `0xFF` space at ROM offset `0x800000`;
- places the new ticket script immediately after the four-object array at `0x800060`;
- changes only Pallet Town's object count (`3 -> 4`) and object-array pointer.

The original Pallet Town object records are not edited in place.

## Altering Cave

LeafGreen contains nine programmed Altering Cave selectors: the baseline Zubat table plus event tables for Mareep, Pineco, Houndour, Teddiursa, Aipom, Shuckle, Stantler and Smeargle. The Mystery Event script would normally advance `VAR_ALTERING_CAVE_WILD_SET`; the intended Wonder Spot distribution was never released.

For permanent availability, every selector table is rewritten to the same merged 12-slot table. Therefore old saves with any selector value and new saves with the default selector all expose the same complete species pool.

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

Trainer Tower Battle-e card data is a separate system and is not changed by the Pallet Town ticket NPC patch. See `docs/trainer-tower-ereader.md`.

## Reference source paths

Public `pret/pokefirered` paths used to derive the patch logic:

- `data/maps/PalletTown/map.json`
- `data/maps/PalletTown/scripts.inc`
- `data/maps/VermilionCity/scripts.inc`
- `data/mystery_event_msg.s`
- `data/scripts/obtain_item.inc`
- `asm/macros/event.inc`
- `asm/macros/map.inc`
- `include/global.fieldmap.h`
- `include/constants/event_objects.h`
- `include/constants/event_object_movement.h`
- `include/constants/flags.h`
- `src/wild_encounter.c`
- `src/data/wild_encounters.json`
