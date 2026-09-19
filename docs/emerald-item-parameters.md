# Emerald item-parameter baseline

## Rule

**Every LeafGreen item uses Pokémon Emerald as the canonical gameplay-parameter reference.**

This is a project-wide rule, not an event-ticket-only rule. The canonical item domain is **0..376**.

- IDs **0..374** line up numerically between the public FireRed/LeafGreen and Emerald sources.
- **375 = ITEM_MAGMA_EMBLEM**
- **376 = ITEM_OLD_SEA_MAP**

The machine-readable baseline is `manifests/emerald_item_parameters.json`, derived from
`pret/pokeemerald` commit `5eff78649e7170a877b961ef0b3da13b81a16038`.

## Gameplay parameters

Emerald is authoritative for the semantic value of:

- price
- held effect
- held-effect parameter
- importance
- registrability
- pocket
- item-use type
- out-of-battle use behavior
- battle usage
- in-battle use behavior
- secondary ID

Names and descriptions remain localized per target ROM. This policy does **not** make every
LeafGreen language ROM English.

## LeafGreen engine adapters

Emerald and LeafGreen do not use every engine enum and function address identically. Therefore
the normalization layer must preserve Emerald **semantics** while using valid LeafGreen engine
representations.

Examples:

- Emerald `POCKET_BERRIES` maps to LeafGreen's Berry Pouch storage/UI.
- Emerald `POCKET_TM_HM` maps to LeafGreen's TM Case storage/UI.
- Emerald code pointers are never copied verbatim into a LeafGreen ROM.
- An Emerald callback is mapped to the equivalent LeafGreen callback when one exists.
- If Emerald behavior does not exist in LeafGreen, it must be explicitly ported before that
  parameter is marked implemented.

This avoids corrupt pointers or broken bag navigation while keeping the gameplay baseline
Emerald-canonical.

## Structural verification

Reference commits:

- `pret/pokeemerald`: `5eff78649e7170a877b961ef0b3da13b81a16038`
- `pret/pokefirered`: `c75f352304d529f6ba92d4f74b9cf8b5c3810788`

The complete Emerald table contains **377 items**. IDs 0..374 align with FR/LG; Emerald adds
Magma Emblem and Old Sea Map at 375 and 376.

A source-level comparison also shows why this must be handled as a full-table policy instead of
a four-ticket exception. Most basic numeric values already match, but there are real differences
in pricing and use behavior. For example, Emerald defines Retro Mail with price 0, and several
berries/key items have different use types or callbacks from their FR/LG compatibility entries.

## Event-item ordering

The Pallet Town selector should expose the requested four event items while using the same global
Emerald baseline:

1. Eon Ticket — ID 275
2. MysticTicket — ID 370
3. AuroraTicket — ID 371
4. Old Sea Map — ID 376

Old Sea Map must use its canonical Emerald ID; it is not aliased onto an unrelated FR/LG slot.
