import pytest

from lite_sdk2 import (
    ActuatorCommand,
    ActuatorState,
    Configuration,
    ImuState,
    LowCommand,
    LowState,
    zero_actuator_commands,
)
from lite_sdk2.topics import dds_topic_to_ros, ros_topic_to_dds


def test_ros_topic_to_dds_accepts_relative_names():
    assert ros_topic_to_dds("lowcommand") == "rt/lowcommand"


def test_dds_topic_to_ros_round_trip():
    assert dds_topic_to_ros("rt/lowstate") == "/lowstate"


def test_low_command_serialize_roundtrip():
    # Field values must be exactly representable in float32 to survive CDR round-trip.
    command = LowCommand(
        configuration=Configuration.FULL_BODY_WITH_FINGERS,
        actuator_commands=[
            ActuatorCommand(mode=10, position=1.25, velocity=-0.5, torque=0.75, kp=5.0, kd=0.125),
            ActuatorCommand(mode=20, position=-2.0, velocity=1.5, torque=-0.25, kp=8.0, kd=0.25),
        ],
    )
    assert LowCommand.deserialize(command.serialize()) == command


def test_zero_helper():
    commands = zero_actuator_commands(3, mode=1, kp=2.0, kd=0.1)
    assert len(commands) == 3
    assert all(c.mode == 1 and c.kp == 2.0 and c.kd == 0.1 for c in commands)


def test_low_command_none_configuration_is_valid():
    assert LowCommand(configuration=0).configuration == Configuration.NONE


def test_low_command_out_of_range_configuration_raises():
    with pytest.raises(ValueError):
        LowCommand(configuration=0x07)


def test_low_state_serialize_roundtrip():
    # Field values must be exactly representable in float32.
    state = LowState(
        version=7,
        tick=1234,
        configuration=Configuration.FULL_BODY_WITH_FINGERS,
        imu_state=ImuState(
            quaternion=[1.0, 0.0, 0.0, 0.0],
            gyroscope=[0.125, 0.25, 0.5],
            accelerometer=[8.0, 0.0, -8.0],
            rpy=[0.125, 0.25, 0.5],
            temperature=32.0,
        ),
        actuator_states=[
            ActuatorState(mode=1, position=0.5, velocity=0.25, torque=0.125, acceleration=1.0, temperature=25.0),
            ActuatorState(mode=2, position=-1.0, velocity=1.5, torque=-0.5, acceleration=2.0, temperature=40.0),
        ],
    )
    assert LowState.deserialize(state.serialize()) == state


def test_low_state_invalid_imu_vector_length_raises():
    with pytest.raises(ValueError):
        LowState(
            configuration=Configuration.BIMANUAL_ARMS,
            imu_state=ImuState(quaternion=[1.0, 0.0, 0.0]),
        )


def test_low_state_out_of_range_configuration_raises():
    with pytest.raises(ValueError):
        LowState(configuration=0x07)
