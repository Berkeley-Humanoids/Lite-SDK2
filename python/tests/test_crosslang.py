"""Python ↔ Rust cross-language DDS integration tests.

Builds the `responder` example from `../rust/` and launches it as a subprocess.
Python publishes `LowCommand`s; Rust subscribes, echoes each command into a
matching `LowState`, and publishes it back. Python subscribes to `LowState`
and asserts the fields round-tripped byte-identically.

Skips gracefully when `cargo` or CycloneDDS aren't on the build host.
"""
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

import lite_sdk2
from lite_sdk2 import ActuatorCommand, Configuration, LowCommand, LowState


REPO_ROOT = Path(__file__).resolve().parents[2]
RUST_DIR = REPO_ROOT / "rust"

# Give each test run a unique DDS domain so parallel runs (e.g. on CI) don't
# hear each other's traffic. Bounded to the valid DDS domain range [0, 230].
DDS_DOMAIN = (os.getpid() % 200) + 10

NIC = "lo"
RESPONDER_DURATION_S = 20.0


def _cargo_available() -> bool:
    return shutil.which("cargo") is not None


def _ddsc_available() -> bool:
    import ctypes
    candidates = ["libddsc.so", "libddsc.so.0", "libddsc.so.11", "libddsc.dylib", "ddsc.dll"]
    # Try the default loader path first.
    for name in candidates:
        try:
            ctypes.CDLL(name)
            return True
        except OSError:
            continue
    # Fall back to CYCLONEDDS_HOME/lib (the convention set by install_cyclonedds.sh).
    cyclonedds_home = os.environ.get("CYCLONEDDS_HOME")
    if cyclonedds_home:
        lib_dir = Path(cyclonedds_home) / "lib"
        for name in candidates:
            try:
                ctypes.CDLL(str(lib_dir / name))
                return True
            except OSError:
                continue
    return False


pytestmark = [
    pytest.mark.skipif(not _cargo_available(), reason="cargo not installed"),
    pytest.mark.skipif(not _ddsc_available(), reason="CycloneDDS (ddsc) not installed"),
]


@pytest.fixture(scope="module")
def responder_binary() -> Path:
    """Build the Rust responder example and return its path."""
    result = subprocess.run(
        ["cargo", "build", "--example", "responder", "--release"],
        cwd=RUST_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"cargo build failed:\n{result.stderr}")
    binary = RUST_DIR / "target" / "release" / "examples" / "responder"
    if not binary.exists():
        pytest.skip(f"responder binary not found at {binary}")
    return binary


@pytest.fixture
def responder(responder_binary: Path):
    """Spawn a responder subprocess for one test, tear it down afterwards."""
    proc = subprocess.Popen(
        [
            str(responder_binary),
            "--domain-id", str(DDS_DOMAIN),
            "--nic", NIC,
            "--duration-s", str(RESPONDER_DURATION_S),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Wait for the responder to print its ready line. If it exits early, surface
    # stderr so the failure is debuggable.
    ready_deadline = time.monotonic() + 10.0
    while time.monotonic() < ready_deadline:
        if proc.poll() is not None:
            out, err = proc.communicate(timeout=1.0)
            pytest.fail(
                f"responder exited before ready (rc={proc.returncode}):\n"
                f"stdout:\n{out.decode(errors='replace')}\n"
                f"stderr:\n{err.decode(errors='replace')}"
            )
        time.sleep(0.2)
        # The responder prints "responder ready: ..." to stderr on startup.
        # We don't block on reading stderr (that would deadlock); 2s of sleep
        # is enough for CycloneDDS to come up in practice.
        if time.monotonic() - ready_deadline + 10.0 > 2.0:
            break
    yield proc
    proc.terminate()
    try:
        proc.wait(timeout=5.0)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=2.0)


def _build_command(tick: int) -> LowCommand:
    # Values chosen to be exactly representable in float32 so round-trips are
    # bit-identical through CDR.
    return LowCommand(
        configuration=Configuration.BIMANUAL_ARMS,
        actuator_commands=[
            ActuatorCommand(
                mode=(index + 1) % 4,
                position=float(tick) + 0.25 + index,
                velocity=-0.5 + index,
                torque=0.75 + index * 0.125,
                kp=5.0 + index,
                kd=0.125 + index * 0.125,
            )
            for index in range(4)
        ],
    )


def _drain_matching_state(sub, expected_tick: int, timeout_s: float = 3.0) -> LowState | None:
    """Read LowState samples until one arrives whose tick is >= expected_tick."""
    deadline = time.monotonic() + timeout_s
    last = None
    while time.monotonic() < deadline:
        sample = sub.read(timeout=0.05)
        if sample is None:
            continue
        last = sample
        if sample.tick >= expected_tick:
            return sample
    return last


def test_python_publishes_and_rust_echoes(responder):
    lite_sdk2.initialize(DDS_DOMAIN, network_interface=NIC)
    pub = lite_sdk2.publisher(LowCommand, domain_id=DDS_DOMAIN, network_interface=NIC)
    sub = lite_sdk2.subscriber(LowState, domain_id=DDS_DOMAIN, network_interface=NIC)
    pub.initialize()
    sub.initialize()

    # Discovery settle: wait for the Rust responder to match our publisher+subscriber.
    assert pub.wait_for_reader(timeout=5.0), "Rust responder never matched our publisher"
    # The Rust side's writer matches ours asynchronously; give DDS a beat.
    time.sleep(0.5)

    try:
        # Send a small burst so at least one arrives after discovery fully settles.
        sent = [_build_command(tick) for tick in range(1, 6)]
        for command in sent:
            pub.write(command)
            time.sleep(0.02)

        # The responder echoes each command; we only need one matching reply to
        # prove wire-compat. Use the most recent sample.
        received = _drain_matching_state(sub, expected_tick=1, timeout_s=5.0)
        assert received is not None, "no LowState received from Rust responder"
        assert received.configuration == int(Configuration.BIMANUAL_ARMS)

        # Find which input tick the responder echoed by matching actuator count.
        assert len(received.actuator_states) == len(sent[0].actuator_commands)

        # Map actuator_commands → actuator_states via the responder's contract
        # (see examples/responder.rs): mode, position, velocity, torque copy
        # directly; acceleration = kp; temperature = 42.0.
        # Match against every sent command; at least one should line up.
        found_match = False
        for command in sent:
            match = all(
                received.actuator_states[i].mode == command.actuator_commands[i].mode
                and received.actuator_states[i].position == command.actuator_commands[i].position
                and received.actuator_states[i].velocity == command.actuator_commands[i].velocity
                and received.actuator_states[i].torque == command.actuator_commands[i].torque
                and received.actuator_states[i].acceleration == command.actuator_commands[i].kp
                and received.actuator_states[i].temperature == 42.0
                for i in range(len(command.actuator_commands))
            )
            if match:
                found_match = True
                break
        assert found_match, (
            "responder echo did not match any sent command; "
            f"received={received!r} sent={sent!r}"
        )
    finally:
        pub.close()
        sub.close()
