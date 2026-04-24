from dataclasses import dataclass

from cyclonedds.idl import IdlStruct
from cyclonedds.idl.types import float32, uint32


@dataclass
class ActuatorState(IdlStruct, typename="lite_sdk2.msg.ActuatorState"):
    mode: uint32 = 0
    position: float32 = 0.0
    velocity: float32 = 0.0
    torque: float32 = 0.0
    acceleration: float32 = 0.0
    temperature: float32 = 0.0


def zero_actuator_states(count: int, mode: int = 0) -> list[ActuatorState]:
    return [ActuatorState(mode=mode) for _ in range(count)]
