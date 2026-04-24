//! Wire-compat tests.
//!
//! The `.cdr` fixtures in `tests/data/` are produced by the Python SDK via
//! `scripts/refresh_fixtures.py`. Decoding them here catches any drift between
//! the two hand-maintained ports of the IDL.

use lite_sdk2::{decode, encode, ActuatorCommand, LowCommand};

const LOW_COMMAND_FIXTURE: &[u8] = include_bytes!("data/low_command.cdr");

fn reference_low_command() -> LowCommand {
    LowCommand {
        configuration: 0x04,
        actuator_commands: vec![
            ActuatorCommand { mode: 1, position: 1.25, velocity: -0.5, torque: 0.75, kp: 5.0, kd: 0.125 },
            ActuatorCommand { mode: 2, position: -2.0, velocity: 1.5, torque: -0.25, kp: 8.0, kd: 0.25 },
        ],
    }
}

#[test]
fn decodes_python_produced_low_command() {
    let decoded: LowCommand = decode(LOW_COMMAND_FIXTURE).unwrap();
    assert_eq!(decoded, reference_low_command());
}

#[test]
fn encodes_byte_for_byte_identical_to_python() {
    let encoded = encode(&reference_low_command());
    assert_eq!(encoded, LOW_COMMAND_FIXTURE);
}

#[test]
fn round_trip_through_cdr() {
    let original = reference_low_command();
    let bytes = encode(&original);
    let decoded: LowCommand = decode(&bytes).unwrap();
    assert_eq!(decoded, original);
}
