# IDL

Canonical message schemas for `lite_sdk2`. This directory is the single source of truth.

- `lite_sdk2/msg/*.idl` — OMG IDL (subset compatible with CycloneDDS `idlc`).
- Python bindings live in `../python/lite_sdk2/messages/`, hand-maintained to match these IDLs and verified by `../python/tests/test_codecs.py`.
- Rust bindings live in `../rust/src/messages.rs`, hand-maintained to match these IDLs and verified by `../rust/tests/wire_compat.rs`.

## Typename convention

Wire typename is `lite_sdk2::msg::<Type>` (CDR/XTypes form). The Python `IdlStruct` `typename=` kwarg mirrors it as `lite_sdk2.msg.<Type>`.

## Adding a new message

1. Add `Foo.idl` here.
2. Mirror it in `python/lite_sdk2/messages/foo.py` as an `IdlStruct` with matching `typename` and field order.
3. Mirror it in `rust/src/messages.rs` with the same field layout.
4. Add a wire round-trip entry to the tests in both languages.

Changes to IDL are breaking unless the field is appended as a mutable/extensible extension — prefer bumping the package minor version for safety while in dev.
