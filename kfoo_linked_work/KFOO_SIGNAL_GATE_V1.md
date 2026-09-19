# KFOO Signal Gate V1

The signal gate is the single fail-closed decision layer after KFOO visual evidence.

## Order

1. KFOO hard evidence
2. MTF alignment: 4H -> 1H -> 15M -> 3M
3. Entry / stop / target validation
4. R:R calculation
5. Final state

## States

- **CONFIRMED**: every required layer is confirmed.
- **WAITING_FOR_EVIDENCE**: KFOO hard evidence is incomplete or unreadable.
- **DATA_UNAVAILABLE**: required MTF or numeric risk inputs are unavailable.
- **REJECTED**: explicit MTF direction conflict or invalid stop/target geometry.

## R:R

No default R:R is invented. For BUY:

- risk = entry - stop
- reward = target - entry

For SELL:

- risk = stop - entry
- reward = entry - target

Both distances must be strictly positive and finite.

## Safety

The gate is decision-only. Its output always carries `execution: OFF`. It does not submit, enable, or modify orders.

The module deliberately does not impose an undocumented minimum R:R threshold; it validates that a real, positive R:R can be calculated.
