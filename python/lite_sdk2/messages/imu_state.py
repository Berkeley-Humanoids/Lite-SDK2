from dataclasses import dataclass, field

from cyclonedds.idl import IdlStruct
from cyclonedds.idl.types import float32, sequence


@dataclass
class ImuState(IdlStruct, typename="lite_sdk2.msg.ImuState"):
    quaternion: sequence[float32] = field(default_factory=lambda: [0.0] * 4)
    gyroscope: sequence[float32] = field(default_factory=lambda: [0.0] * 3)
    accelerometer: sequence[float32] = field(default_factory=lambda: [0.0] * 3)
    rpy: sequence[float32] = field(default_factory=lambda: [0.0] * 3)
    temperature: float32 = 0.0

    def __post_init__(self) -> None:
        _require_length(self.quaternion, 4, "quaternion")
        _require_length(self.gyroscope, 3, "gyroscope")
        _require_length(self.accelerometer, 3, "accelerometer")
        _require_length(self.rpy, 3, "rpy")


def _require_length(values: list[float], expected: int, name: str) -> None:
    if len(values) != expected:
        raise ValueError(f"{name} must contain exactly {expected} float values.")
