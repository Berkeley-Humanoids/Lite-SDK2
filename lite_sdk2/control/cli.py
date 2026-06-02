"""``lite-sdk2-control`` — publish safe ``MITCommand``s to park the robot.

``damping`` streams a zero-stiffness / high-damping command until Ctrl+C (and
sends a zero-torque burst on exit); ``disable`` sends a short zero-torque burst
and exits. The joint order is discovered from the robot's ``/joint_states`` so
no fixed configuration table is needed.

    lite-sdk2-control enp2s0 damping
    lite-sdk2-control enp2s0 disable
    lite-sdk2-control enp2s0 damping --damping 3.0 --rate 100 --domain-id 3
"""

from __future__ import annotations

import argparse
import sys

from loop_rate_limiters import RateLimiter

import lite_sdk2
from lite_sdk2 import JointState, MITCommand, zero_mit_command


def _discover_joints(domain_id: int, network_interface: str, timeout: float) -> list[str]:
    sub = lite_sdk2.subscriber(JointState)
    sub.initialize()
    print("Waiting for /joint_states to learn the joint order...", file=sys.stderr)
    deadline_iters = max(1, int(timeout / 0.05))
    try:
        for _ in range(deadline_iters):
            state = sub.read(timeout=0.05)
            if state is not None and state.name:
                return list(state.name)
        return []
    finally:
        sub.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lite-sdk2-control",
        description="Publish safe MITCommands (damping / disable) to park the robot.",
    )
    parser.add_argument("network_interface", help="NIC to bind CycloneDDS to (e.g. enp2s0).")
    parser.add_argument("action", choices=["damping", "disable"])
    parser.add_argument("--domain-id", type=int, default=0, help="ROS_DOMAIN_ID (default 0).")
    parser.add_argument(
        "--damping", type=float, default=2.0, help="Damping gain for 'damping' (N*m*s/rad; default 2.0)."
    )
    parser.add_argument("--rate", type=float, default=50.0, help="Publish rate in Hz (default 50).")
    parser.add_argument(
        "--discovery-timeout", type=float, default=5.0, help="Seconds to wait for /joint_states (default 5)."
    )
    args = parser.parse_args(argv)

    lite_sdk2.initialize(domain_id=args.domain_id, network_interface=args.network_interface)

    joints = _discover_joints(args.domain_id, args.network_interface, args.discovery_timeout)
    if not joints:
        print("No /joint_states received; cannot determine joint order. Aborting.", file=sys.stderr)
        return 1
    print(f"Joints ({len(joints)}): {joints}", file=sys.stderr)

    pub = lite_sdk2.publisher(MITCommand)
    pub.initialize()
    if not pub.wait_for_reader(timeout=2.0):
        print("Warning: no command subscriber matched; publishing anyway.", file=sys.stderr)

    disable_cmd = zero_mit_command(joints)
    try:
        if args.action == "disable":
            for _ in range(10):
                pub.write(disable_cmd)
            print("Sent disable (zero-torque) burst.", file=sys.stderr)
            return 0

        damp_cmd = zero_mit_command(joints, stiffness=0.0, damping=args.damping)
        print(f"Streaming damping={args.damping} at {args.rate} Hz; Ctrl+C to stop.", file=sys.stderr)
        rate = RateLimiter(frequency=args.rate, warn=False)
        try:
            while True:
                pub.write(damp_cmd)
                rate.sleep()
        except KeyboardInterrupt:
            for _ in range(10):
                pub.write(disable_cmd)
            print("\nStopped; sent disable burst.", file=sys.stderr)
        return 0
    finally:
        pub.close()


if __name__ == "__main__":
    raise SystemExit(main())
