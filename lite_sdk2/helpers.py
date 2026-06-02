"""Small constructors for common bar_msgs commands."""

from __future__ import annotations

from collections.abc import Sequence

from bar_msgs_dds import MITCommand

__all__ = ["zero_mit_command"]


def zero_mit_command(
    joint_names: Sequence[str],
    *,
    stiffness: float = 0.0,
    damping: float = 0.0,
) -> MITCommand:
    """A :class:`MITCommand` holding zero position/velocity/effort for each joint.

    Per-joint torque on the hardware is
    ``tau = stiffness*(pos - q) + damping*(vel - qdot) + effort``; with the
    defaults here every term is zero (a zero-torque command). For a safe "park"
    command, pass ``damping > 0`` (and ``stiffness = 0``) so the joints resist
    motion without holding a position.
    """
    n = len(joint_names)
    return MITCommand(
        joint_names=list(joint_names),
        position=[0.0] * n,
        velocity=[0.0] * n,
        effort=[0.0] * n,
        stiffness=[float(stiffness)] * n,
        damping=[float(damping)] * n,
    )
