"""Register address map from ST DS11546 Rev 5, tables 75-77.

Only address, width and access semantics are encoded here. Bit fields should be
added only after they have been transcribed and reviewed against the datasheet.
"""
from dataclasses import dataclass
from enum import Enum


class Access(str, Enum):
    READ_WRITE = "read-write"
    READ_CLEAR = "read-clear"
    READ_ONLY = "read-only"


@dataclass(frozen=True)
class Register:
    address: int
    name: str
    access: Access
    width: int


# CR1..CR34 are consecutive at 0x01..0x22 (Table 75).
APPLICATION_REGISTERS = {
    address: Register(address, f"CR{address}", Access.READ_WRITE, 24)
    for address in range(0x01, 0x23)
}
# SR1..SR12 are consecutive at 0x31..0x3C (Table 75).
APPLICATION_REGISTERS.update({
    address: Register(address, f"SR{address - 0x30}", Access.READ_CLEAR, 24)
    for address in range(0x31, 0x3D)
})
APPLICATION_REGISTERS[0x3F] = Register(0x3F, "CONFIG", Access.READ_WRITE, 24)

INFORMATION_REGISTERS = {
    0x00: Register(0x00, "COMPANY_CODE", Access.READ_ONLY, 8),
    0x01: Register(0x01, "DEVICE_FAMILY", Access.READ_ONLY, 8),
    0x02: Register(0x02, "DEVICE_NUMBER_1", Access.READ_ONLY, 8),
    0x03: Register(0x03, "DEVICE_NUMBER_2", Access.READ_ONLY, 8),
    0x04: Register(0x04, "DEVICE_NUMBER_3", Access.READ_ONLY, 8),
    0x05: Register(0x05, "DEVICE_NUMBER_4", Access.READ_ONLY, 8),
    0x06: Register(0x06, "DEVICE_NUMBER_5", Access.READ_ONLY, 8),
    0x0A: Register(0x0A, "SILICON_VERSION", Access.READ_ONLY, 8),
    0x10: Register(0x10, "SPI_MODE", Access.READ_ONLY, 8),
    0x11: Register(0x11, "WD_TYPE_1", Access.READ_ONLY, 8),
    0x12: Register(0x12, "WD_TYPE_2", Access.READ_ONLY, 8),
    0x13: Register(0x13, "WD_BIT_POSITION_1", Access.READ_ONLY, 8),
    0x14: Register(0x14, "WD_BIT_POSITION_2", Access.READ_ONLY, 8),
    0x15: Register(0x15, "WD_BIT_POSITION_3", Access.READ_ONLY, 8),
    0x16: Register(0x16, "WD_BIT_POSITION_4", Access.READ_ONLY, 8),
    0x20: Register(0x20, "SPI_CPHA_TEST", Access.READ_ONLY, 8),
    0x3E: Register(0x3E, "GSB_OPTIONS", Access.READ_ONLY, 8),
}

EXPECTED_L99DZ100G_ID = bytes((0x00, 0x01, 0x55, 0x42, 0x46, 0x09, 0x01))


def application_register(address: int) -> Register:
    try:
        return APPLICATION_REGISTERS[address]
    except KeyError as exc:
        raise ValueError(f"invalid application register address: 0x{address:02X}") from exc

