from __future__ import annotations


class SpidevPort:
    """Linux spidev adapter configured for the datasheet-required SPI mode 0."""
    def __init__(self, bus: int = 0, device: int = 0, speed_hz: int = 500_000):
        try:
            import spidev
        except ImportError as exc:
            raise RuntimeError("install the 'rpi' extra to use real SPI") from exc
        self._spi = spidev.SpiDev()
        self._spi.open(bus, device)
        self._spi.mode = 0
        self._spi.max_speed_hz = speed_hz
        self._spi.bits_per_word = 8

    def transfer(self, data: bytes) -> bytes:
        if len(data) != 4:
            raise ValueError("L99DZ100G application frames must be exactly 4 bytes")
        return bytes(self._spi.xfer2(list(data)))

    def close(self) -> None:
        self._spi.close()

