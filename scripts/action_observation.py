import argparse
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Lock, Thread

from lite_sdk2 import initialize, publisher, subscriber
from lite_sdk2.messages import ActuatorState, LowCommand, LowState, zero_actuator_commands
from lite_sdk2.topics import LOWCOMMAND, LOWSTATE


DEFAULT_ACTUATOR_COUNT = 34


@dataclass(slots=True)
class SummaryStats:
    count: int
    minimum_ms: float
    mean_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    maximum_ms: float
    std_ms: float


def parse_args(default_role: str | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Latency and traffic test over LowCommand/LowState DDS topics."
    )
    if default_role is None:
        parser.add_argument("role", choices=("host", "robot"))
    parser.add_argument("nic")
    parser.add_argument("--domain-id", type=int, default=0)
    parser.add_argument("--action-topic", default=LOWCOMMAND)
    parser.add_argument("--observation-topic", default=LOWSTATE)
    parser.add_argument("--num-joints", type=int, default=DEFAULT_ACTUATOR_COUNT)
    parser.add_argument("--action-hz", type=float, default=100.0)
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--interface", default=None)
    return parser.parse_args()


def _percentile(sorted_values: list[float], percentile: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    index = (len(sorted_values) - 1) * percentile
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = index - lower
    return sorted_values[lower] * (1.0 - fraction) + sorted_values[upper] * fraction


def _summarize(latencies_ms: list[float]) -> SummaryStats | None:
    if not latencies_ms:
        return None
    ordered = sorted(latencies_ms)
    return SummaryStats(
        count=len(ordered),
        minimum_ms=ordered[0],
        mean_ms=statistics.fmean(ordered),
        p50_ms=_percentile(ordered, 0.50),
        p95_ms=_percentile(ordered, 0.95),
        p99_ms=_percentile(ordered, 0.99),
        maximum_ms=ordered[-1],
        std_ms=statistics.pstdev(ordered) if len(ordered) > 1 else 0.0,
    )


def _interface_bytes(interface: str | None) -> tuple[int, int] | None:
    if interface is None:
        return None
    base = Path("/sys/class/net") / interface / "statistics"
    try:
        rx = int((base / "rx_bytes").read_text(encoding="utf-8").strip())
        tx = int((base / "tx_bytes").read_text(encoding="utf-8").strip())
    except FileNotFoundError:
        return None
    return rx, tx


def _message_bytes(message: object) -> int:
    serialize = getattr(message, "serialize", None)
    if not callable(serialize):
        return 0
    try:
        return len(serialize())
    except Exception:
        return 0


def _run_host(args: argparse.Namespace) -> int:
    initialize(args.domain_id, network_interface=args.nic)
    cmd = publisher(LowCommand, topic=args.action_topic, domain_id=args.domain_id, network_interface=args.nic)
    state = subscriber(LowState, topic=args.observation_topic, domain_id=args.domain_id, network_interface=args.nic)
    cmd.initialize()
    state.initialize()

    outstanding: dict[int, float] = {}
    lock = Lock()
    latencies: list[float] = []
    tx_bytes = 0
    rx_bytes = 0
    stop = Event()

    def reader() -> None:
        nonlocal rx_bytes
        while not stop.is_set():
            msg = state.read(timeout=0.05)
            if msg is None:
                continue
            rx_bytes += _message_bytes(msg)
            if not msg.actuator_states:
                continue
            sequence_id = int(round(msg.actuator_states[0].position))
            with lock:
                sent = outstanding.pop(sequence_id, None)
            if sent is not None:
                latencies.append((time.perf_counter() - sent) * 1000.0)

    thread = Thread(target=reader, daemon=True)
    thread.start()

    if_start = _interface_bytes(args.interface)
    deadline = time.perf_counter() + args.duration
    sequence_id = 0

    try:
        while time.perf_counter() < deadline:
            cycle = time.perf_counter()
            command = LowCommand(actuator_commands=zero_actuator_commands(args.num_joints, mode=1))
            command.actuator_commands[0].position = float(sequence_id)
            with lock:
                outstanding[sequence_id] = cycle
            cmd.write(command)
            tx_bytes += _message_bytes(command)
            sequence_id += 1
            remaining = (1.0 / args.action_hz) - (time.perf_counter() - cycle)
            if remaining > 0.0:
                time.sleep(remaining)
    except KeyboardInterrupt:
        pass
    finally:
        time.sleep(0.5)
        stop.set()
        thread.join(timeout=1.0)
        cmd.close()
        state.close()

    if_end = _interface_bytes(args.interface)
    summary = _summarize(latencies)

    print(f"Host mode complete. Sent {sequence_id} actions, received {len(latencies)} observations.")
    print(f"Application bytes: tx={tx_bytes} rx={rx_bytes}")
    if if_start is not None and if_end is not None:
        print(f"Interface bytes: tx={if_end[1] - if_start[1]} rx={if_end[0] - if_start[0]}")
    if summary is None:
        print("No round-trip samples matched.")
    else:
        print(
            f"Latency ms: count={summary.count} min={summary.minimum_ms:.3f} mean={summary.mean_ms:.3f} "
            f"p50={summary.p50_ms:.3f} p95={summary.p95_ms:.3f} p99={summary.p99_ms:.3f} "
            f"max={summary.maximum_ms:.3f} std={summary.std_ms:.3f}"
        )
    return 0


def _run_robot(args: argparse.Namespace) -> int:
    initialize(args.domain_id, network_interface=args.nic)
    cmd = subscriber(LowCommand, topic=args.action_topic, domain_id=args.domain_id, network_interface=args.nic)
    state = publisher(LowState, topic=args.observation_topic, domain_id=args.domain_id, network_interface=args.nic)
    cmd.initialize()
    state.initialize()

    processed = 0
    tx_bytes = 0
    rx_bytes = 0
    if_start = _interface_bytes(args.interface)
    deadline = None if args.duration <= 0 else time.perf_counter() + args.duration

    try:
        while deadline is None or time.perf_counter() < deadline:
            command = cmd.read(timeout=0.1)
            if command is None:
                continue
            rx_bytes += _message_bytes(command)
            reply = LowState(
                actuator_states=[
                    ActuatorState(
                        mode=c.mode,
                        position=c.position,
                        velocity=c.velocity,
                        torque=c.torque,
                    )
                    for c in command.actuator_commands
                ]
            )
            state.write(reply)
            tx_bytes += _message_bytes(reply)
            processed += 1
    except KeyboardInterrupt:
        pass
    finally:
        cmd.close()
        state.close()

    if_end = _interface_bytes(args.interface)
    print(f"Robot mode complete. Processed {processed} LowCommand samples.")
    print(f"Application bytes: tx={tx_bytes} rx={rx_bytes}")
    if if_start is not None and if_end is not None:
        print(f"Interface bytes: tx={if_end[1] - if_start[1]} rx={if_end[0] - if_start[0]}")
    return 0


def main(role: str | None = None) -> int:
    args = parse_args(role)
    selected = role or args.role
    if selected == "host":
        return _run_host(args)
    if selected == "robot":
        return _run_robot(args)
    raise ValueError(f"Unsupported role: {selected}")


if __name__ == "__main__":
    raise SystemExit(main())
