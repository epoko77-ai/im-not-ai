# Changelog

## v2.0-patch - 2026-07-04

- Repaired metrics tests so clean clones use the tracked `baseline.json` instead of the ignored `_workspace` KatFish baseline.
- Hardened `metrics.py` baseline loading so a missing override path falls back with a warning instead of crashing.
- Fixed `test_metrics_v2.py` project-root resolution for direct unittest execution.
