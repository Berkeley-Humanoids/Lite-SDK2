# lite_sdk2 (Rust)

Rust bindings for the `lite_sdk2` DDS message set.

- Schemas in [`../idl/lite_sdk2/msg/`](../idl/lite_sdk2/msg) are the single source of truth.
- Structs in `src/messages.rs` are hand-maintained to mirror those schemas.
- `src/cdr.rs` is a minimal LE PLAIN_CDR codec sufficient for these messages.
- `tests/wire_compat.rs` decodes a CDR fixture produced by the Python SDK to catch drift.

## What this crate does *not* do yet

Transport. Real DDS (discovery, QoS, matched-reader tracking) is not implemented here.
When it's needed, the recommended path is to wrap `cyclonedds-sys` (FFI to the same C
library the Python SDK uses, guaranteeing wire compat) and keep the `CdrBody` structs
in this file untouched.

## Regenerating fixtures

```bash
cd ..
./scripts/refresh_fixtures.py
```

The script lives at the repo root so Python and Rust stay in lockstep.
