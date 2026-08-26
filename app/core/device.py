from dataclasses import asdict, dataclass
from enum import IntEnum
from threading import Lock

from app.hal import SpiPort
from .registers import (
    Access,
    APPLICATION_REGISTERS,
    EXPECTED_L99DZ100G_ID,
    SR1_DEBUG_ACTIVE,
    STATUS_REGISTERS,
    application_register,
)


class Opcode(IntEnum):
    WRITE = 0b00
    READ = 0b01
    READ_CLEAR = 0b10
    DEVICE_INFO = 0b11


@dataclass(frozen=True)
class Response:
    global_status: int
    payload: int

    def as_dict(self) -> dict:
        return {"global_status": f"0x{self.global_status:02X}", "payload": f"0x{self.payload:06X}"}


class L99DZ100:
    def __init__(self, spi: SpiPort):
        self.spi = spi
        # One L99 SPI frame at a time. This also protects real spidev when a
        # background diagnostic monitor and an API request overlap.
        self._io_lock = Lock()

    def _exchange(self, opcode: Opcode, address: int, payload: int = 0) -> Response:
        if not 0 <= address <= 0x3F or not 0 <= payload <= 0xFFFFFF:
            raise ValueError("address or 24-bit payload out of range")
        tx = bytes(((int(opcode) << 6) | address,)) + payload.to_bytes(3, "big")
        with self._io_lock:
            rx = self.spi.transfer(tx)
        if len(rx) != 4:
            raise IOError(f"SPI adapter returned {len(rx)} bytes, expected 4")
        return Response(rx[0], int.from_bytes(rx[1:], "big"))

    def read(self, address: int) -> Response:
        application_register(address)
        return self._exchange(Opcode.READ, address)

    def write(self, address: int, value: int) -> Response:
        reg = application_register(address)
        if reg.access is not Access.READ_WRITE:
            raise ValueError(f"{reg.name} is not writable")
        return self._exchange(Opcode.WRITE, address, value)

    def read_clear(self, address: int, mask: int) -> Response:
        reg = application_register(address)
        if reg.access is not Access.READ_CLEAR:
            raise ValueError(f"{reg.name} is not a read-and-clear status register")
        return self._exchange(Opcode.READ_CLEAR, address, mask)

    def read_device_info(self, address: int) -> Response:
        result = self._exchange(Opcode.DEVICE_INFO, address)
        return Response(result.global_status, (result.payload >> 16) & 0xFF)

    def device_info(self) -> dict:
        raw = bytes(self.read_device_info(i).payload for i in range(7))
        silicon = self.read_device_info(0x0A).payload
        return {
            "raw_id": raw.hex().upper(),
            "is_l99dz100g": raw == EXPECTED_L99DZ100G_ID,
            "variant": "L99DZ100G" if raw == EXPECTED_L99DZ100G_ID else "unknown",
            "silicon_version": f"0x{silicon:02X}",
        }

    def debug_active(self) -> bool:
        return bool(self.read(0x31).payload & SR1_DEBUG_ACTIVE)

    def status_dump(self) -> list[dict]:
        rows = []
        for address in STATUS_REGISTERS:
            register = APPLICATION_REGISTERS[address]
            response = self.read(address)
            rows.append({
                **asdict(register),
                "access": register.access.value,
                "value": f"0x{response.payload:06X}",
                "global_status": f"0x{response.global_status:02X}",
            })
        return rows

    def dump(self) -> list[dict]:
        rows = []
        for address, register in sorted(APPLICATION_REGISTERS.items()):
            response = self.read(address)
            rows.append({**asdict(register), "access": register.access.value,
                         "value": f"0x{response.payload:06X}",
                         "global_status": f"0x{response.global_status:02X}"})
        return rows
