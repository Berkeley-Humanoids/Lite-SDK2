"""Default ROS topic + QoS for each humanoid_control_msgs type, matching the Humanoid Control bringup.

The host SDK and the robot must agree on topic name *and* QoS for DDS to pair a
writer with a reader. These defaults mirror what the `Humanoid Control` controllers
declare; override per call with ``publisher(..., topic=, qos=)`` when needed.

``ros_topic_to_dds`` is re-exported from ``humanoid_control_msgs_dds`` (the single canonical
copy) so the SDK and the message package can never disagree on the ``rt/`` rule.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from humanoid_control_msgs_dds import (
    ControlMode,
    JointState,
    MITCommand,
    SafetyStatus,
    StandbyState,
    reliable_keep_last,
    ros_topic_to_dds,
    transient_local,
)

__all__ = ["default_topic", "default_qos", "ros_topic_to_dds"]

# ROS topic names as declared by the Humanoid Control bringup.
COMMAND = "/remote_policy_controller/command"
JOINT_STATES = "/lite/joint_states"
CONTROL_MODE = "/control_mode"
SAFETY_STATUS = "/safety_status"
STANDBY_STATE = "/standby_controller/state"

_DEFAULT_TOPIC: dict[type, str] = {
    MITCommand: COMMAND,
    JointState: JOINT_STATES,
    ControlMode: CONTROL_MODE,
    SafetyStatus: SAFETY_STATUS,
    StandbyState: STANDBY_STATE,
}

# QoS factories (called per endpoint). Reliability + durability must match the
# bringup; history depth is local. mode_manager publishes /control_mode and
# /safety_status reliable, and latches /standby_controller/state.
_DEFAULT_QOS: dict[type, Callable[[], Any]] = {
    MITCommand: lambda: reliable_keep_last(4),
    JointState: lambda: reliable_keep_last(10),
    ControlMode: lambda: reliable_keep_last(10),
    SafetyStatus: lambda: reliable_keep_last(10),
    StandbyState: lambda: transient_local(1),
}


def default_topic(message_type: type) -> str:
    try:
        return _DEFAULT_TOPIC[message_type]
    except KeyError:
        raise ValueError(f"No default topic for {message_type.__name__}; pass topic= explicitly.") from None


def default_qos(message_type: type) -> Any | None:
    """Default QoS for ``message_type`` (or ``None`` if unregistered — the caller
    then falls back to the CycloneDDS default)."""
    factory = _DEFAULT_QOS.get(message_type)
    return factory() if factory is not None else None
