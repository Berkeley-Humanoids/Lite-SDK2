"""Local DDS loopback: a MITCommand written by a publisher is read back by a
subscriber on the same topic, with fields intact. Exercises the full channel +
QoS + humanoid_control_msgs_dds path in one process.
"""

import pytest

pytest.importorskip("cyclonedds")

import lite_sdk2  # noqa: E402
from lite_sdk2 import MITCommand, zero_mit_command  # noqa: E402

_TOPIC = "/test/lite_sdk2/roundtrip"


def test_zero_mit_command_shape():
    cmd = zero_mit_command(["j1", "j2", "j3"], damping=1.5)
    assert cmd.joint_names == ["j1", "j2", "j3"]
    assert cmd.position == [0.0, 0.0, 0.0]
    assert cmd.velocity == [0.0, 0.0, 0.0]
    assert cmd.stiffness == [0.0, 0.0, 0.0]
    assert cmd.damping == [1.5, 1.5, 1.5]


def test_local_loopback_roundtrip():
    lite_sdk2.initialize(domain_id=0)
    qos = lite_sdk2.reliable_keep_last(4)
    sub = lite_sdk2.subscriber(MITCommand, topic=_TOPIC, qos=qos)
    sub.initialize()
    pub = lite_sdk2.publisher(MITCommand, topic=_TOPIC, qos=qos)
    pub.initialize()
    assert pub.wait_for_reader(timeout=5.0), "writer never matched the in-process reader"

    cmd = zero_mit_command(["hip", "knee"], damping=2.0)
    cmd.position = [1.0, 2.0]
    cmd.header.frame_id = "base"
    pub.write(cmd)

    got = sub.read(timeout=2.0)
    assert got is not None, "no sample received over loopback"
    assert got.joint_names == ["hip", "knee"]
    assert got.position == [1.0, 2.0]
    assert got.damping == [2.0, 2.0]
    assert got.header.frame_id == "base"

    pub.close()
    sub.close()
