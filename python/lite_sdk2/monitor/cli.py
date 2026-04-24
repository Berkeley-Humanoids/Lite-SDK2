import argparse
from collections.abc import Sequence
from typing import Any

from .. import initialize, subscriber, topics
from ..messages import LowCommand, LowState


_MONITOR_TYPES: dict[str, type] = {
    "lowcommand": LowCommand,
    "lowstate": LowState,
}

_DEFAULT_TOPICS: dict[str, str] = {
    "lowcommand": topics.LOWCOMMAND,
    "lowstate": topics.LOWSTATE,
}

_ALIASES = {"low-command": "lowcommand", "low-state": "lowstate"}


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print decoded Lite SDK2 traffic.")
    parser.add_argument("nic", help="NIC name, e.g. enp2s0.")
    parser.add_argument("monitor", choices=sorted([*_MONITOR_TYPES, *_ALIASES]))
    parser.add_argument("--domain-id", type=int, default=0)
    parser.add_argument("--topic", help="Override the default ROS topic.")
    args = parser.parse_args(argv)
    args.monitor = _ALIASES.get(args.monitor, args.monitor)
    return args


def _print_low_command(sample: Any) -> None:
    print(
        f"  configuration=0x{int(sample.configuration):02X} "
        f"num_actuators={len(sample.actuator_commands)}"
    )
    for index, cmd in enumerate(sample.actuator_commands):
        print(
            f"  actuator[{index}] mode={cmd.mode} "
            f"pos={cmd.position:.4f} vel={cmd.velocity:.4f} torque={cmd.torque:.4f} "
            f"kp={cmd.kp:.4f} kd={cmd.kd:.4f}"
        )


def _print_low_state(sample: Any) -> None:
    print(
        f"  configuration=0x{int(sample.configuration):02X} "
        f"version={sample.version} tick={sample.tick} "
        f"imu_temp={sample.imu_state.temperature:.2f}"
    )
    for index, state in enumerate(sample.actuator_states):
        print(
            f"  actuator[{index}] mode={state.mode} "
            f"pos={state.position:.4f} vel={state.velocity:.4f} "
            f"torque={state.torque:.4f} temp={state.temperature:.2f}"
        )


_PRINTERS = {"lowcommand": _print_low_command, "lowstate": _print_low_state}


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    topic = args.topic if args.topic is not None else _DEFAULT_TOPICS[args.monitor]
    initialize(args.domain_id, network_interface=args.nic)
    sub = subscriber(
        _MONITOR_TYPES[args.monitor],
        topic=topic,
        domain_id=args.domain_id,
        network_interface=args.nic,
    )
    sub.initialize()
    print(f"Listening for {args.monitor} on '{topic}' in domain {args.domain_id} via {args.nic}.")
    try:
        while True:
            sample = sub.read()
            if sample is None:
                continue
            print("Received sample:")
            _PRINTERS[args.monitor](sample)
    except KeyboardInterrupt:
        return 0
    finally:
        sub.close()


if __name__ == "__main__":
    raise SystemExit(main())
