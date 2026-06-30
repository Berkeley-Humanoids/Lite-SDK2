"""Lite SDK2 — host-side CycloneDDS access to a Berkeley Humanoid Lite running
``humanoid_control``, with no ``rclpy``.

The SDK speaks ``humanoid_control_msgs`` directly: message types are re-exported from
``humanoid_control_msgs_dds`` (generated, wire-compatible with ROS 2), and the
publisher/subscriber layer is message-agnostic.

    import lite_sdk2
    from lite_sdk2 import MITCommand, JointState, zero_mit_command

    lite_sdk2.initialize(domain_id=0, network_interface="enp2s0")

    sub = lite_sdk2.subscriber(JointState)
    sub.initialize()
    state = sub.read(timeout=0.5)

    pub = lite_sdk2.publisher(MITCommand)
    pub.initialize()
    pub.wait_for_reader(timeout=2.0)            # optional discovery wait
    pub.write(zero_mit_command(state.name, damping=2.0))   # park
"""

from humanoid_control_msgs_dds import (
    ControlMode,
    Header,
    JointState,
    MITCommand,
    SafetyStatus,
    StandbyState,
    Time,
    best_effort_keep_last,
    reliable_keep_last,
    ros_topic_to_dds,
    transient_local,
)

from . import topics
from .channel import (
    ChannelPublisher,
    ChannelSubscriber,
    initialize,
    publisher,
    subscriber,
)
from .helpers import zero_mit_command

__all__ = [
    # message types (from humanoid_control_msgs_dds)
    "ControlMode",
    "Header",
    "JointState",
    "MITCommand",
    "SafetyStatus",
    "StandbyState",
    "Time",
    # channel API
    "ChannelPublisher",
    "ChannelSubscriber",
    "initialize",
    "publisher",
    "subscriber",
    "topics",
    # QoS + conventions
    "best_effort_keep_last",
    "reliable_keep_last",
    "ros_topic_to_dds",
    "transient_local",
    # helpers
    "zero_mit_command",
]
