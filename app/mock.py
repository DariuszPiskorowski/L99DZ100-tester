from .core.registers import EXPECTED_L99DZ100G_ID, SR1_DEBUG_ACTIVE


class MockSpiPort:
    """Deterministic in-memory device for development and CI."""
    def __init__(self):
        application_addresses = (
            list(range(0x01, 0x1E))
            + [0x22]
            + list(range(0x31, 0x3D))
            + [0x3F]
        )
        self.application = {address: 0 for address in application_addresses}
        # The development/CI fixture represents a tester with DEBUG asserted,
        # so manual output profiles can be exercised without a real watchdog.
        self.application[0x31] = SR1_DEBUG_ACTIVE
        self.info = {i: value for i, value in enumerate(EXPECTED_L99DZ100G_ID)}
        self.info.update({0x0A: 0x10, 0x10: 0xB0, 0x20: 0x55, 0x3E: 0x00})
        self.closed = False

    def transfer(self, data: bytes) -> bytes:
        if len(data) != 4:
            raise ValueError("expected four bytes")
        opcode, address = data[0] >> 6, data[0] & 0x3F
        payload = int.from_bytes(data[1:], "big")
        if opcode == 3:
            return bytes((0x80, self.info.get(address, 0), 0, 0))
        old = self.application.get(address, 0)
        if opcode == 0 and address in self.application:
            self.application[address] = payload
        elif opcode == 2 and address in range(0x31, 0x3D):
            self.application[address] = old & ~payload
        return bytes((0x80,)) + old.to_bytes(3, "big")

    def close(self) -> None:
        self.closed = True
