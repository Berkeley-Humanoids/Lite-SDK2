from dataclasses import dataclass

from cyclonedds.idl import IdlStruct


@dataclass
class UserData(IdlStruct, typename="lite_sdk2.example.UserData"):
    string_data: str
    float_data: float
