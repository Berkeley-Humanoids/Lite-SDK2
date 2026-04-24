from enum import IntEnum


class Configuration(IntEnum):
    NONE = 0x00
    FULL_BODY = 0x01
    FULL_BODY_WITH_FINGERS = 0x02
    ARMS_AND_LEGS = 0x03
    BIMANUAL_ARMS = 0x04
    LEFT_ARM = 0x05
    RIGHT_ARM = 0x06


def validate_configuration(value: int | Configuration) -> int:
    code = int(value)
    if code not in _VALID_CODES:
        valid = ", ".join(f"0x{candidate:02X}" for candidate in _VALID_CODES)
        raise ValueError(f"configuration must be one of: {valid}.")
    return code


_VALID_CODES = frozenset(candidate.value for candidate in Configuration)
