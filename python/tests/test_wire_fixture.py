"""Cross-language wire-format regression.

The `rust/tests/data/*.cdr` fixtures are produced by `scripts/refresh_fixtures.py`
and consumed by the Rust crate's `tests/wire_compat.rs`. This test re-encodes
the same reference messages on the Python side and asserts byte equality so
that drift between the hand-maintained IDL bindings is caught locally, not
only when the Rust CI runs.
"""
from pathlib import Path

from lite_sdk2 import ActuatorCommand, Configuration, LowCommand


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "rust" / "tests" / "data"


def _reference_low_command() -> LowCommand:
    return LowCommand(
        configuration=Configuration.BIMANUAL_ARMS,
        actuator_commands=[
            ActuatorCommand(mode=1, position=1.25, velocity=-0.5, torque=0.75, kp=5.0, kd=0.125),
            ActuatorCommand(mode=2, position=-2.0, velocity=1.5, torque=-0.25, kp=8.0, kd=0.25),
        ],
    )


def test_low_command_fixture_matches_current_encoder():
    fixture = (FIXTURE_DIR / "low_command.cdr").read_bytes()
    assert _reference_low_command().serialize() == fixture
