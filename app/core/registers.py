"""L99DZ100G register map and reviewed profile constants.

Addresses are transcribed from ST DS11546 Rev 5, Table 86/87.
Bit/profile constants below are added only where explicitly reviewed against
DS11546 Rev 5 tables 88-117 and 142-143.
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


# CR1..CR29 occupy 0x01..0x1D. Addresses 0x1E..0x21 are reserved.
APPLICATION_REGISTERS = {
    address: Register(address, f"CR{address}", Access.READ_WRITE, 24)
    for address in range(0x01, 0x1E)
}
# CR34 is at 0x22 (there are no CR30..CR33).
APPLICATION_REGISTERS[0x22] = Register(0x22, "CR34", Access.READ_WRITE, 24)

# SR1..SR12 are consecutive at 0x31..0x3C.
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

# Reviewed control bits.
CR1_HEN = 1 << 6                    # Table 89: external H-bridge enable
CR11_ECON = 1 << 8                  # Table 117: electro-chrome controller enable
CR11_ECV_LS = 1 << 13               # Table 117: ECV low-side switch
SR1_DEBUG_ACTIVE = 1 << 16          # Table 143: live Debug Mode indicator

# Direct integrated output registers, Tables 99-105.
OUTPUT_CONTROL_REGISTERS = (0x04, 0x05, 0x06)

# OUT1..OUT6 high-side bits in CR4: 21,17,13,9,5,1.
# OUT7/8/10/OUT_HS use configuration 0001=ON in CR5.
# OUT9/11/12/13/14/15 use configuration 0001=ON in CR6.
OUTPUTS_HIGH_PROFILE = {
    0x04: 0x222222,
    0x05: 0x110101,
    0x06: 0x111111,
}

# OUT1..OUT6 low-side bits in CR4: 20,16,12,8,4,0.
# OUT7..OUT15 and OUT_HS are high-side-only and remain OFF in this profile.
OUTPUTS_LOW_PROFILE = {
    0x04: 0x111111,
    0x05: 0x000000,
    0x06: 0x000000,
}

STATUS_REGISTERS = tuple(range(0x31, 0x3D))


def application_register(address: int) -> Register:
    try:
        return APPLICATION_REGISTERS[address]
    except KeyError as exc:
        raise ValueError(f"invalid application register address: 0x{address:02X}") from exc
