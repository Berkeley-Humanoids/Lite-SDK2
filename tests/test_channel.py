"""Registry resolution and topic-name mangling (no live DDS comms)."""

import pytest

pytest.importorskip("cyclonedds")

import lite_sdk2  # noqa: E402
from lite_sdk2 import JointState, MITCommand, topics  # noqa: E402


def test_default_topic_registered():
    assert topics.default_topic(MITCommand) == "/remote_policy_controller/command"
    assert topics.default_topic(JointState) == "/lite/joint_states"


def test_default_qos_present_for_known_types():
    assert topics.default_qos(MITCommand) is not None
    assert topics.default_qos(JointState) is not None


def test_unregistered_type_raises():
    class Unknown:
        pass

    with pytest.raises(ValueError):
        topics.default_topic(Unknown)


def test_ros_topic_to_dds():
    assert lite_sdk2.ros_topic_to_dds("/lite/joint_states") == "rt/lite/joint_states"
    assert lite_sdk2.ros_topic_to_dds("lite/joint_states") == "rt/lite/joint_states"
    assert lite_sdk2.ros_topic_to_dds("rt/already") == "rt/already"


def test_publisher_subscriber_resolve_topic_name():
    pub = lite_sdk2.publisher(MITCommand)
    assert pub.topic_name == "rt/remote_policy_controller/command"
    sub = lite_sdk2.subscriber(JointState)
    assert sub.topic_name == "rt/lite/joint_states"
