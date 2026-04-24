from .messages.low_command import LowCommand
from .messages.low_state import LowState


LOWCOMMAND = "/lowcommand"
LOWSTATE = "/lowstate"

_DEFAULTS: dict[type, str] = {
    LowCommand: LOWCOMMAND,
    LowState: LOWSTATE,
}


def default_topic(message_type: type) -> str:
    try:
        return _DEFAULTS[message_type]
    except KeyError as exc:
        raise ValueError(f"No default topic registered for {message_type.__name__}.") from exc


def ros_topic_to_dds(name: str) -> str:
    if name.startswith("rt/"):
        return name
    return f"rt{_normalize_ros(name)}"


def dds_topic_to_ros(name: str) -> str:
    if not name:
        raise ValueError("DDS topic names must be non-empty.")
    if name.startswith("rt/"):
        return name[2:]
    return name


def _normalize_ros(name: str) -> str:
    if not name:
        raise ValueError("ROS topic names must be non-empty.")
    if name.startswith("rt/"):
        raise ValueError("Expected a ROS topic name, not a DDS topic name.")
    return name if name.startswith("/") else f"/{name}"
