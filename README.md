# Lite SDK2

SDK for Berkeley Humanoid Lite host-to-robot communication. Defines low-level message types,
topic conventions, and publisher/subscriber wrappers. Messages are wire-compatible across
language implementations.

## Repo layout

```
idl/                   OMG IDL schemas — single source of truth
python/                Python implementation (package: lite_sdk2)
rust/                  Rust implementation (crate: lite_sdk2)
scripts/               Cross-language tooling (e.g. fixture regeneration)
```

Language bindings are hand-maintained to match the IDL and pinned to each other
by a shared CDR fixture in `rust/tests/data/`. Drift is caught by
`python/tests/test_wire_fixture.py` and `rust/tests/wire_compat.rs`.

## Python

```bash
cd python
uv sync
uv run pytest
```

CycloneDDS must be installed — see `install_cyclonedds.sh` for Linux.

### Tools

Both CLIs take the network interface as the first positional argument.

**`lite-sdk2-monitor`** — subscribe to `LowCommand` or `LowState` and print each
sample as it arrives. Useful for verifying a publisher is on the wire.

```bash
uv run lite-sdk2-monitor enp2s0 lowstate                # print decoded LowState traffic
uv run lite-sdk2-monitor enp2s0 lowcommand              # print decoded LowCommand traffic
```

**`lite-sdk2-control`** — publish `LowCommand`s to put the robot into a safe
state. `damping` streams zero-position-gain / high-damping commands until
Ctrl+C (and sends a disable burst on exit); `disable` sends a short disable
burst and exits. Use this to park the robot before/after an experiment.

```bash
uv run lite-sdk2-control enp2s0 damping                 # stream damping until Ctrl+C
uv run lite-sdk2-control enp2s0 disable                 # disable all actuators and exit
uv run lite-sdk2-control enp2s0 damping --configuration full_body
uv run lite-sdk2-control enp2s0 damping --domain-id 3 --period 0.01
```

Defaults to `Configuration.BIMANUAL_ARMS`; pass `--configuration` with any of
`full_body`, `full_body_with_fingers`, `arms_and_legs`, `bimanual_arms`,
`left_arm`, `right_arm` to target a different layout.

## Rust

```bash
cd rust
cargo test
```

Provides the message types, a pure-Rust CDR codec (`cdr`), and a
CycloneDDS-backed `Publisher` / `Subscriber` behind a default `transport`
Cargo feature. Disable with `default-features = false` for a codec-only build
(no C library required).

The build script locates CycloneDDS via (in order) `CYCLONEDDS_HOME`,
`pkg-config CycloneDDS`, and the system include paths.

## Scripts

```bash
# Regenerate the wire-compat fixture after changing a message layout.
uv run --directory python python ../scripts/refresh_fixtures.py

# Latency + throughput test. Run one end per machine (or in two terminals on one).
uv run --directory python python ../scripts/action_observation.py robot eno1
uv run --directory python python ../scripts/action_observation.py host  eno1
```

## DDS model

| Direction | ROS topic | DDS topic | Message type |
| --- | --- | --- | --- |
| Host → robot | `/lowcommand` | `rt/lowcommand` | `LowCommand` |
| Robot → host | `/lowstate` | `rt/lowstate` | `LowState` |

ROS topic names are prefixed with `rt/` on the wire (ROS 2 convention). Wire
typename is `lite_sdk2::msg::<Type>`.

### Messages

`LowCommand` / `LowState` each carry a `configuration` field (uint32) that
selects the active robot layout, analogous to Unitree SDK2's `mode_machine`.
Per-joint commands and states are sequences whose length must match the active
configuration.

| Value | Name | Actuator count |
| --- | --- | --- |
| `0x01` | `Configuration.FULL_BODY` | 34 |
| `0x02` | `Configuration.FULL_BODY_WITH_FINGERS` | 74 |
| `0x03` | `Configuration.ARMS_AND_LEGS` | 28 |
| `0x04` | `Configuration.BIMANUAL_ARMS` | 14 |
| `0x05` | `Configuration.LEFT_ARM` | 7 |
| `0x06` | `Configuration.RIGHT_ARM` | 7 |

See `idl/lite_sdk2/msg/*.idl` for the canonical field lists.

## Usage

```python
import lite_sdk2
from lite_sdk2 import LowCommand, LowState, Configuration, zero_actuator_commands

lite_sdk2.initialize(domain_id=0, network_interface="enp2s0")

pub = lite_sdk2.publisher(LowCommand)
pub.initialize()
pub.wait_for_reader(timeout=2.0)          # optional discovery wait (not realtime-safe)
pub.write(LowCommand(                      # realtime-safe, fire-and-forget
    configuration=Configuration.BIMANUAL_ARMS,
    actuator_commands=zero_actuator_commands(14, mode=1),
))

sub = lite_sdk2.subscriber(LowState)
sub.initialize()
state = sub.read(timeout=0.1)
```

## Adding a message

1. Add `idl/lite_sdk2/msg/Foo.idl`.
2. Mirror it in `python/lite_sdk2/messages/foo.py` as an `IdlStruct` with matching
   `typename="lite_sdk2.msg.Foo"` and field order.
3. Mirror it in `rust/src/messages.rs` (implement `CdrBody`) with the same field
   order.
4. Regenerate fixtures: `uv run --directory python python ../scripts/refresh_fixtures.py`.
5. Run `pytest` and `cargo test`.
