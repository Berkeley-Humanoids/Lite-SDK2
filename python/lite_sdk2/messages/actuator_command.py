from dataclasses import dataclass

from cyclonedds.idl import IdlStruct
from cyclonedds.idl.types import float32, uint32


@dataclass
class ActuatorCommand(IdlStruct, typename="lite_sdk2.msg.ActuatorCommand"):
    mode: uint32 = 0
    position: float32 = 0.0
    velocity: float32 = 0.0
    torque: float32 = 0.0
    kp: float32 = 0.0
    kd: float32 = 0.0


def zero_actuator_commands(
    count: int,
    mode: int = 0,
    position: float = 0.0,
    velocity: float = 0.0,
    torque: float = 0.0,
    kp: float = 0.0,
    kd: float = 0.0,
) -> list[ActuatorCommand]:
    return [
        ActuatorCommand(
            mode=mode,
            position=position,
            velocity=velocity,
            torque=torque,
            kp=kp,
            kd=kd,
        )
        for _ in range(count)
    ]
