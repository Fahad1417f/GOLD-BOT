# KFOO Visual Verification V1

## Contract

A screenshot crop is an artifact, not evidence.

The pipeline has four states:

- PRESENT: an external OCR/vision adapter explicitly observed the configured KFOO feature.
- ABSENT: the adapter explicitly observed a negative state.
- UNREADABLE: the region exists but semantic interpretation is unavailable or invalid.
- DATA_UNAVAILABLE: the frame/observation source is unavailable.

Confidence is metadata only. It never upgrades UNREADABLE to PRESENT.

## Current implementation

`kfoo_evidence_regions_v1.py` captures configured normalized regions.

`kfoo_visual_verifier_v1.py` normalizes trusted OCR/vision observations.

No OCR engine is silently installed or assumed. This avoids treating arbitrary pixels, generic indicators, or guessed screen coordinates as KFOO evidence.

## Next integration

Connect a real OCR/vision adapter to the TradingView screenshot stream. The adapter must return explicit observations for:

- continuity_average
- liquidity_table
- liquidity_net_positive
- ascending_channel
- whales_buying
- kfoo_arrow
- divergence
- whale_wave_sync

Only after that observation layer is proven should the KFOO rule engine consume the evidence.

Execution remains OFF.
