"""Hardware boundaries. GPIO/CAN/LIN implementations are intentionally deferred."""
from typing import Protocol


class SpiPort(Protocol):
    def transfer(self, data: bytes) -> bytes: ...
    def close(self) -> None: ...


class GpioPort(Protocol):
    def read(self, name: str) -> bool: ...
    def write(self, name: str, value: bool) -> None: ...


class BusPort(Protocol):
    def send(self, data: bytes) -> None: ...
    def receive(self, timeout: float) -> bytes | None: ...


class UnsupportedGpio:
    def read(self, name: str) -> bool:
        raise NotImplementedError("GPIO adapter is not configured")
    def write(self, name: str, value: bool) -> None:
        raise NotImplementedError("GPIO adapter is not configured")


class UnsupportedBus:
    def send(self, data: bytes) -> None:
        raise NotImplementedError("bus adapter is not configured")
    def receive(self, timeout: float) -> bytes | None:
        raise NotImplementedError("bus adapter is not configured")

