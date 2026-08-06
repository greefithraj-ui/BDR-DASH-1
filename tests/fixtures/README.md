# BIC Golden Fixture Corpus (Sprint 1, T1.4)

Each fixture is a directory under `tests/fixtures/` holding static JSON payloads
that mirror the live per-machine files:

- `rings.json` — the `DESTINATION/rings/<machine>.json` payload. Slot-keyed
  dict; **only occupied slots appear** (slot *absence* means the slot is empty).
- `bdr.json` — the `DESTINATION/bdr/<machine>.json` payload:
  `{ "saved_at": <ISO-8601>, "slots": { <slot>: {...} } }`.

Load them via `tests/fixture_loader.py`
(`load_fixture(name)` / `list_fixtures()`). `bdr` is `None` when a fixture has
no `bdr.json`. Fixtures are read-only and never connected to any live system.

Timestamps are fixed (never `now`-relative) so tests stay deterministic:
the "fresh" fixtures use `saved_at = 2026-08-01T10:00:00.000000+05:30` and the
"offline" fixtures use `2026-08-01T08:00:00.000000+05:30` (2 h old, past both
the 60 s freshness window and the 30 min sync staleness).

## Fixtures and their documented facts

| Fixture | Occupied slots | Documented facts |
|---|---|---|
| `machine_active` | 1, 2, 3, 4 | Healthy machine: every slot `BDR_RUNNING`; rings and bdr agree on identity per slot; `saved_at` fresh. |
| `machine_empty` | — | Both payloads present and empty (`{}` rings, `{}` slots); machine is completely empty but fresh. |
| `ring_passed` | 2, 7, 11 | Slots 2 and 7 `PASSED` (test completed); slot 11 still `BDR_RUNNING`. |
| `ring_failed` | 4, 6 | Slot 4 `FAILED` with a non-null `error` and `BDR_TEST: FAILED`; slot 6 `BDR_RUNNING`. |
| `ring_assigned` | 9, 10 | Slot 9 `ASSIGNED` with `queued_at` set and `BDR_TEST: QUEUED`; slot 10 `BDR_RUNNING`. |
| `ring_bdr_running` | 1, 5, 8, 20, 30 | All `BDR_RUNNING`; slot 1 reports `dead_state=BATTERY_DEAD`, `dead_confirm_passes=1`; slot 30 has `discharge_connect_failures=1`. |
| `replacement` | 1, 2 | Slot 1 now holds **new** serial `RP-CH3-P18-WD-PA10-0009999`; prior observation of this slot held serial `RP-CH3-P18-WD-PA10-0005550` → direct swap must classify `REPLACED`. |
| `removal_pending` | 1, 2 | Slot 3 held serial `RP-CH3-P18-WD-PA10-0006313` previously; now absent from **both** payloads (consistent empty) → removal candidate. |
| `machine_offline` | 1, 2 | `saved_at` is 2 h stale → machine offline; collector must make **no** removal/classification decisions while offline. |
| `one_source_mismatch` | 1, 2, 3, 5* | Slot 5 present in `rings.json` only (absent from bdr) → one-source-only **data-quality mismatch**, blocks slot-5 decisions. Slots 1–3 agree across sources. |
| `machine_empty_bdr_absent` | — | `rings.json` is `{}` and there is **no** `bdr.json` file at all → loader returns `bdr=None`. |
| `removal_offline` | 1, 2 | Slot 3 previously held serial `RP-CH3-P18-WD-PA10-0009613`; now absent from both payloads **and** `saved_at` is stale → removal blocked by the offline rule. |

`tests/test_fixtures.py` asserts every documented fact above so a fixture can
never silently drift from its stated purpose.
