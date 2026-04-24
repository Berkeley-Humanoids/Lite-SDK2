"""Regenerate cross-language CDR fixtures used by the Rust wire-compat tests.

Run from the repo root after changing any message layout:

    uv run --directory python --with . python ../scripts/refresh_fixtures.py
"""
from pathlib import Path

from lite_sdk2 import ActuatorCommand, Configuration, LowCommand


REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "rust" / "tests" / "data"


def low_command_fixture() -> bytes:
    command = LowCommand(
        configuration=Configuration.BIMANUAL_ARMS,
        actuator_commands=[
            ActuatorCommand(mode=1, position=1.25, velocity=-0.5, torque=0.75, kp=5.0, kd=0.125),
            ActuatorCommand(mode=2, position=-2.0, velocity=1.5, torque=-0.25, kp=8.0, kd=0.25),
        ],
    )
    return command.serialize()


def main() -> int:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    (FIXTURES_DIR / "low_command.cdr").write_bytes(low_command_fixture())
    print(f"Wrote fixtures under {FIXTURES_DIR.relative_to(REPO_ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
