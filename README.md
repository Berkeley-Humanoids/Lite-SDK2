# Lite SDK2

Host-side SDK for **Berkeley Humanoid Lite**. It gives a pure-Python (no `rclpy`)
process on a host machine a publisher/subscriber API onto a robot running the
[`humanoid_control`](https://github.com/Berkeley-Humanoids/humanoid_control) control stack, over CycloneDDS.

## What it provides

- **Message types** — re-exported from `humanoid_control_msgs_dds`: `MITCommand`, `JointState`,
  `ControlMode`, `SafetyStatus`, `StandbyState` (+ `Header`/`Time`). These carry the
  rmw type-name mangling, so they interoperate with a live `humanoid_control` graph.
- **A message-agnostic channel layer** — a process-wide DDS participant, NIC
  selection, realtime-safe `write()`, discovery wait, and callback subscriptions.
- **A topic + QoS registry** — per-type defaults matching the bringup, so
  `publisher(MITCommand)` "just works"; override with `topic=`/`qos=`.
- **CLIs** — `lite-sdk2-monitor` and `lite-sdk2-control`.

## Install

```bash
cd Lite-SDK2
uv sync          # uses the in-tree humanoid_control_msgs_dds via [tool.uv.sources]
uv run pytest
```

CycloneDDS is pulled in as a dependency. As a dependency of another project:

```toml
dependencies = [
    "lite_sdk2 @ git+https://github.com/Berkeley-Humanoids/Lite-SDK2.git",
]
```

## DDS model

| Direction | Message | ROS topic | DDS topic | QoS |
| --- | --- | --- | --- | --- |
| host → robot | `MITCommand` | `/remote_policy_controller/command` | `rt/…` | reliable, depth 4 |
| robot → host | `JointState` | `/lite/joint_states` | `rt/…` | reliable, depth 10 |
| robot → host | `ControlMode` | `/control_mode` | `rt/…` | reliable |
| robot → host | `SafetyStatus` | `/safety_status` | `rt/…` | reliable |
| robot → host | `StandbyState` | `/standby_controller/state` | `rt/…` | transient-local (latched) |

ROS topic names get the `rt/` prefix on the wire; the wire typename is
`pkg::msg::dds_::Name_` (the rmw mangling). Both are handled by `humanoid_control_msgs_dds`.

## Usage

```python
import lite_sdk2
from lite_sdk2 import MITCommand, JointState, zero_mit_command

lite_sdk2.initialize(domain_id=0, network_interface="enp2s0")

sub = lite_sdk2.subscriber(JointState)          # topic + QoS from the registry
sub.initialize()
state = sub.read(timeout=0.5)

pub = lite_sdk2.publisher(MITCommand)
pub.initialize()
pub.wait_for_reader(timeout=2.0)                # optional discovery wait
pub.write(zero_mit_command(state.name, damping=2.0))   # safe "park" command
```

### CLIs

```bash
uv run lite-sdk2-monitor enp2s0 joint_states          # print decoded JointState traffic
uv run lite-sdk2-monitor enp2s0 control_mode
uv run lite-sdk2-control enp2s0 damping               # stream damping until Ctrl+C
uv run lite-sdk2-control enp2s0 disable               # zero-torque burst, then exit
```

Both take the network interface as the first argument; `--domain-id` selects the
`ROS_DOMAIN_ID`. `lite-sdk2-control` discovers the joint order from `/joint_states`.

## Adding or changing a message

Messages live in `humanoid_control`, not here. Edit `humanoid_control_msgs/msg/*.msg`, run
`pixi run gen-dds` to regenerate `humanoid_control_msgs_dds`, and the new/changed type is
available through `lite_sdk2` automatically. There is no schema, IDL, or Rust
mirror to keep in sync in this repo anymore.

## Architecture

```
humanoid_control_msgs (.msg)      ← single source of truth, in humanoid_control
   │ pixi run gen-dds
humanoid_control_msgs_dds         ← generated cyclonedds types + topic/QoS conventions
   │ pip dependency
lite_sdk2 (this repo) ← message-agnostic channel layer + CLIs
   │
host apps            ← policy runners, Lite-Gravity-Compensation, data tools
```
