from dataclasses import dataclass, field

from cyclonedds.idl import IdlStruct
from cyclonedds.idl.types import sequence, uint32

from .actuator_command import ActuatorCommand
from .configuration import validate_configuration


@dataclass
class LowCommand(IdlStruct, typename="lite_sdk2.msg.LowCommand"):
    configuration: uint32 = 0
    actuator_commands: sequence[ActuatorCommand] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.configuration = validate_configuration(self.configuration)
