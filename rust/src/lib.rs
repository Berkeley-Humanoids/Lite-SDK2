//! Rust bindings for the `lite_sdk2` DDS message set.
//!
//! Schemas live in `../idl/lite_sdk2/msg/*.idl`. The structs in [`messages`]
//! are hand-maintained to match byte-for-byte; cross-language wire
//! compatibility is verified by `tests/wire_compat.rs` and the Python-side
//! cross-lang tests.
//!
//! With the default `transport` feature, this crate also owns a
//! CycloneDDS-backed transport (see [`channel`]). Pass
//! `default-features = false` to get only the message types + CDR codec.

pub mod cdr;
pub mod messages;
pub mod topics;

pub use cdr::{CdrError, decode, encode};
pub use messages::{ActuatorCommand, ActuatorState, Configuration, ImuState, LowCommand, LowState};

#[cfg(feature = "transport")]
pub mod channel;
#[cfg(feature = "transport")]
mod ffi;

#[cfg(feature = "transport")]
pub use channel::{Error as ChannelError, Message, Participant, Publisher, Subscriber, initialize};
