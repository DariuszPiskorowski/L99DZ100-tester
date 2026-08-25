from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

from .device import L99DZ100


@dataclass(frozen=True)
class TestResult:
    id: str
    name: str
    passed: bool
    started_at: str
    details: dict


class TestEngine:
    def __init__(self, device: L99DZ100):
        self.device = device
        self._tests: dict[str, Callable[[], tuple[bool, dict]]] = {
            "communication": self._communication,
            "register_dump": self._register_dump,
        }

    def names(self) -> list[str]:
        return sorted(self._tests)

    def run(self, name: str) -> TestResult:
        try:
            test = self._tests[name]
        except KeyError as exc:
            raise ValueError(f"unknown test: {name}") from exc
        started = datetime.now(timezone.utc).isoformat()
        passed, details = test()
        return TestResult(str(uuid4()), name, passed, started, details)

    def _communication(self) -> tuple[bool, dict]:
        info = self.device.device_info()
        return bool(info["is_l99dz100g"]), info

    def _register_dump(self) -> tuple[bool, dict]:
        rows = self.device.dump()
        return True, {"count": len(rows), "registers": rows}

