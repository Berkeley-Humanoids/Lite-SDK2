"""``lite-sdk2-monitor`` — subscribe to a bar_ros2 topic and print each sample.

Useful for confirming a publisher is on the wire and the QoS/typename line up.

    lite-sdk2-monitor enp2s0 joint_states
    lite-sdk2-monitor enp2s0 control_mode --domain-id 3
"""

from __future__ import annotations

import argparse
import sys

import lite_sdk2
from lite_sdk2 import ControlMode, JointState, SafetyStatus, StandbyState

_TYPES = {
    "joint_states": JointState,
    "control_mode": ControlMode,
    "safety_status": SafetyStatus,
    "standby_state": StandbyState,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lite-sdk2-monitor",
        description="Subscribe to a bar_ros2 topic and print decoded samples.",
    )
    parser.add_argument("network_interface", help="NIC to bind CycloneDDS to (e.g. enp2s0).")
    parser.add_argument("message", choices=sorted(_TYPES), help="Which stream to print.")
    parser.add_argument("--domain-id", type=int, default=0, help="ROS_DOMAIN_ID (default 0).")
    parser.add_argument("--topic", default=None, help="Override the default ROS topic.")
    args = parser.parse_args(argv)

    message_type = _TYPES[args.message]
    lite_sdk2.initialize(domain_id=args.domain_id, network_interface=args.network_interface)
    sub = lite_sdk2.subscriber(message_type, topic=args.topic)
    sub.initialize()
    print(
        f"Subscribed to {sub.topic_name} ({message_type.__name__}) on domain {args.domain_id}; Ctrl+C to stop.",
        file=sys.stderr,
    )
    try:
        while True:
            sample = sub.read(timeout=1.0)
            if sample is not None:
                print(sample)
    except KeyboardInterrupt:
        pass
    finally:
        sub.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
