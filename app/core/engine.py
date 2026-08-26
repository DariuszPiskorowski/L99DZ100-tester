from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

from .device import L99DZ100
from .registers import OUTPUT_CONTROL_REGISTERS


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
            "all_off": self._all_off,
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

    def _all_off(self) -> tuple[bool, dict]:
        before = {}
        after = {}
        for address in OUTPUT_CONTROL_REGISTERS:
            before[f"CR{address}"] = self.device.read(address).as_dict()

        for address in OUTPUT_CONTROL_REGISTERS:
            self.device.write(address, 0x000000)

        passed = True
        for address in OUTPUT_CONTROL_REGISTERS:
            response = self.device.read(address)
            after[f"CR{address}"] = response.as_dict()
            passed = passed and response.payload == 0

        return passed, {
            "profile": "ALL OFF",
            "datasheet": "ST DS11546 Rev 5, CR4/CR5/CR6",
            "written": {f"CR{address}": "0x000000" for address in OUTPUT_CONTROL_REGISTERS},
            "before": before,
            "after": after,
        }
