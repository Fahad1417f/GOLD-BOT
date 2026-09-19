# KFOO Hard Gate V1

The hard gate requires all five documented core KFOO evidence items before a directional signal can be marked CONFIRMED:

1. continuity_average
2. liquidity_table
3. liquidity_net_positive
4. ascending_channel
5. whales_buying

Missing or unreadable evidence produces WAITING_FOR_EVIDENCE. Unavailable source data produces DATA_UNAVAILABLE. Invalid direction is REJECTED.

This gate does not create entry, stop, target, or R:R values. Execution remains OFF.
