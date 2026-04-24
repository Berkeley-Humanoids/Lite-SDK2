from dataclasses import dataclass, field

from cyclonedds.idl import IdlStruct
from cyclonedds.idl.types import sequence, uint32

from .actuator_state import ActuatorState
from .configuration import validate_configuration
from .imu_state import ImuState


@dataclass
class LowState(IdlStruct, typename="lite_sdk2.msg.LowState"):
    version: uint32 = 1
    tick: uint32 = 0
    configuration: uint32 = 0
    imu_state: ImuState = field(default_factory=ImuState)
    actuator_states: sequence[ActuatorState] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.configuration = validate_configuration(self.configuration)
