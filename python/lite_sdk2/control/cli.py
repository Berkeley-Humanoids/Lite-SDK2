"""Command-line tool for switching actuators between damping and disabled."""
import argparse
import time
from typing import Sequence

from lite_sdk2 import (
    Configuration,
    LowCommand,
    initialize,
    publisher,
    zero_actuator_commands,
)
from lite_sdk2.topics import LOWCOMMAND


ACTUATOR_MODE_DISABLED = 0
ACTUATOR_MODE_ENABLED = 1
DAMPING_KP = 0.0
DAMPING_KD = 8.0

ACTIONS = ("damping", "disable")

ACTUATORS_PER_CONFIGURATION = {
    Configuration.FULL_BODY: 34,
    Configuration.FULL_BODY_WITH_FINGERS: 74,
    Configuration.ARMS_AND_LEGS: 28,
    Configuration.BIMANUAL_ARMS: 14,
    Configuration.LEFT_ARM: 7,
    Configuration.RIGHT_ARM: 7,
}


def _parse_configuration(value: str) -> Configuration:
    normalized = value.strip().upper().replace("-", "_")
    try:
        configuration = Configuration[normalized]
    except KeyError as exc:
        valid = ", ".join(c.name.lower() for c in Configuration if c is not Configuration.NONE)
        raise argparse.ArgumentTypeError(f"configuration must be one of: {valid}") from exc
    if configuration is Configuration.NONE:
        raise argparse.ArgumentTypeError("configuration cannot be 'none'.")
    return configuration


def _damping_command(configuration: Configuration) -> LowCommand:
    return LowCommand(
        configuration=configuration,
        actuator_commands=zero_actuator_commands(
            ACTUATORS_PER_CONFIGURATION[configuration],
            mode=ACTUATOR_MODE_ENABLED,
            kp=DAMPING_KP,
            kd=DAMPING_KD,
        ),
    )


def _disable_command(configuration: Configuration) -> LowCommand:
    return LowCommand(
        configuration=configuration,
        actuator_commands=zero_actuator_commands(
            ACTUATORS_PER_CONFIGURATION[configuration],
            mode=ACTUATOR_MODE_DISABLED,
            kp=0.0,
            kd=0.0,
        ),
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Switch Lite actuators into damping or disabled mode.",
    )
    parser.add_argument("nic", help="Network interface bound by the DDS participant.")
    parser.add_argument(
        "action",
        choices=ACTIONS,
        help="'damping' streams damping commands until Ctrl+C; 'disable' sends disable commands once.",
    )
    parser.add_argument("--domain-id", type=int, default=0)
    parser.add_argument("--topic", default=LOWCOMMAND)
    parser.add_argument(
        "--configuration",
        type=_parse_configuration,
        default=Configuration.BIMANUAL_ARMS,
    )
    parser.add_argument("--period", type=float, default=0.02)
    parser.add_argument("--enable-timeout", type=float, default=2.0)
    parser.add_argument("--disable-retries", type=int, default=5)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    initialize(args.domain_id, network_interface=args.nic)
    pub = publisher(
        LowCommand,
        topic=args.topic,
        domain_id=args.domain_id,
        network_interface=args.nic,
    )
    pub.initialize()
    pub.wait_for_reader(args.enable_timeout)

    num_joints = ACTUATORS_PER_CONFIGURATION[args.configuration]
    disable = _disable_command(args.configuration)

    try:
        if args.action == "damping":
            damping = _damping_command(args.configuration)
            print(
                f"Streaming damping on '{args.topic}' (domain {args.domain_id}, NIC {args.nic}) "
                f"for configuration '{args.configuration.name.lower()}' ({num_joints} actuators)."
            )
            try:
                while True:
                    pub.write(damping)
                    time.sleep(args.period)
            except KeyboardInterrupt:
                print("Disabling actuators.")
            for _ in range(max(args.disable_retries, 1)):
                pub.write(disable)
                time.sleep(args.period)
        else:
            print(
                f"Disabling actuators on '{args.topic}' (domain {args.domain_id}, NIC {args.nic}) "
                f"for configuration '{args.configuration.name.lower()}' ({num_joints} actuators)."
            )
            for _ in range(max(args.disable_retries, 1)):
                pub.write(disable)
                time.sleep(args.period)
    finally:
        pub.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
