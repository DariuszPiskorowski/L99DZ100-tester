from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Event, Lock, Thread
from typing import Callable
from uuid import uuid4

from .device import L99DZ100
from .registers import (
    CR1_HEN,
    CR11_ECON,
    CR11_ECV_LS,
    OUTPUT_CONTROL_REGISTERS,
    OUTPUTS_HIGH_PROFILE,
    OUTPUTS_LOW_PROFILE,
    SR1_DEBUG_ACTIVE,
)


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
            "outputs_high": self._outputs_high,
            "outputs_low": self._outputs_low,
            "register_dump": self._register_dump,
        }
        self._monitor_stop = Event()
        self._monitor_thread: Thread | None = None
        self._snapshot_lock = Lock()
        self._active_profile: str | None = None
        self._status_snapshot: dict = {
            "active_profile": None,
            "monitoring": False,
            "updated_at": None,
            "debug_active": None,
            "registers": [],
            "error": None,
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

    def live_status(self) -> dict:
        with self._snapshot_lock:
            return {
                "active_profile": self._status_snapshot["active_profile"],
                "monitoring": self._status_snapshot["monitoring"],
                "updated_at": self._status_snapshot["updated_at"],
                "debug_active": self._status_snapshot["debug_active"],
                "registers": list(self._status_snapshot["registers"]),
                "error": self._status_snapshot["error"],
            }

    def _communication(self) -> tuple[bool, dict]:
        info = self.device.device_info()
        return bool(info["is_l99dz100g"]), info

    def _register_dump(self) -> tuple[bool, dict]:
        rows = self.device.dump()
        return True, {"count": len(rows), "registers": rows}

    def _safe_off_no_monitor(self) -> tuple[bool, dict]:
        before = {}
        after = {}

        for address in (0x01, *OUTPUT_CONTROL_REGISTERS, 0x0B):
            before[f"CR{address}"] = self.device.read(address).as_dict()

        # External MOSFET H-bridge: HEN=0. Only write CR1 when necessary so
        # normal watchdog operation is disturbed as little as possible.
        cr1 = int(before["CR1"]["payload"], 16)
        if cr1 & CR1_HEN:
            self.device.write(0x01, cr1 & ~CR1_HEN)

        # Integrated half-bridges and high-side outputs, plus GH heater in CR5.
        for address in OUTPUT_CONTROL_REGISTERS:
            self.device.write(address, 0x000000)

        # Electro-chrome path can independently force OUT10 on. Disable ECON
        # and the ECV low-side while preserving the reference and OCR settings.
        cr11 = int(before["CR11"]["payload"], 16)
        cr11_off = cr11 & ~(CR11_ECON | CR11_ECV_LS)
        if cr11_off != cr11:
            self.device.write(0x0B, cr11_off)

        passed = True
        for address in (0x01, *OUTPUT_CONTROL_REGISTERS, 0x0B):
            response = self.device.read(address)
            after[f"CR{address}"] = response.as_dict()

        passed = passed and not (int(after["CR1"]["payload"], 16) & CR1_HEN)
        passed = passed and all(
            int(after[f"CR{address}"]["payload"], 16) == 0
            for address in OUTPUT_CONTROL_REGISTERS
        )
        passed = passed and not (
            int(after["CR11"]["payload"], 16) & (CR11_ECON | CR11_ECV_LS)
        )

        return passed, {
            "profile": "ALL OFF",
            "datasheet": "ST DS11546 Rev 5: CR1 HEN, CR4-CR6, CR11 ECON/ECV_LS",
            "before": before,
            "after": after,
            "note": (
                "LS1_FSO/LS2_FSO belong to the independent fail-safe block and may be "
                "forced active by hardware fail-safe logic."
            ),
        }

    def _all_off(self) -> tuple[bool, dict]:
        self._stop_monitor()
        passed, details = self._safe_off_no_monitor()
        self._set_snapshot(None, False, None, [], None)
        return passed, details

    def _outputs_high(self) -> tuple[bool, dict]:
        return self._apply_output_profile("OUTPUTS HIGH", OUTPUTS_HIGH_PROFILE)

    def _outputs_low(self) -> tuple[bool, dict]:
        return self._apply_output_profile("OUTPUTS LOW", OUTPUTS_LOW_PROFILE)

    def _apply_output_profile(self, name: str, profile: dict[int, int]) -> tuple[bool, dict]:
        # DS11546 4.3.3: DEBUG high disables the window watchdog while keeping
        # all device functionality available. Manual measurement profiles are
        # blocked unless SR1.DEBUG_ACTIVE confirms this state.
        sr1 = self.device.read(0x31)
        if not (sr1.payload & SR1_DEBUG_ACTIVE):
            return False, {
                "profile": name,
                "blocked": True,
                "reason": "DEBUG_ACTIVE is 0; live output profiles require Debug mode",
                "sr1": sr1.as_dict(),
                "required": "DEBUG pin high and SR1 bit 16 = 1",
            }

        self._stop_monitor()
        safe_passed, safe_details = self._safe_off_no_monitor()
        if not safe_passed:
            return False, {
                "profile": name,
                "blocked": True,
                "reason": "could not establish ALL OFF baseline",
                "safe_off": safe_details,
            }

        for address, value in profile.items():
            self.device.write(address, value)

        after = {}
        passed = True
        for address, expected in profile.items():
            response = self.device.read(address)
            after[f"CR{address}"] = response.as_dict()
            passed = passed and response.payload == expected

        if passed:
            self._start_monitor(name)

        return passed, {
            "profile": name,
            "debug_active": True,
            "written": {f"CR{address}": f"0x{value:06X}" for address, value in profile.items()},
            "after": after,
            "monitoring": passed,
            "safe_off_baseline": safe_details,
        }

    def _start_monitor(self, profile: str) -> None:
        self._monitor_stop.clear()
        self._active_profile = profile
        self._set_snapshot(profile, True, None, [], None)
        self._monitor_thread = Thread(target=self._monitor_loop, name="l99-status-monitor", daemon=True)
        self._monitor_thread.start()

    def _stop_monitor(self) -> None:
        self._monitor_stop.set()
        thread = self._monitor_thread
        if thread and thread.is_alive():
            thread.join(timeout=1.0)
        self._monitor_thread = None
        self._active_profile = None

    def _monitor_loop(self) -> None:
        while not self._monitor_stop.is_set():
            try:
                rows = self.device.status_dump()
                sr1_value = int(rows[0]["value"], 16) if rows else 0
                debug_active = bool(sr1_value & SR1_DEBUG_ACTIVE)
                self._set_snapshot(
                    self._active_profile,
                    True,
                    datetime.now(timezone.utc).isoformat(),
                    rows,
                    None,
                    debug_active,
                )

                # If Debug mode disappears while a manual output profile is
                # active, immediately request the safe state and stop polling.
                if not debug_active:
                    self._safe_off_no_monitor()
                    self._set_snapshot(
                        None,
                        False,
                        datetime.now(timezone.utc).isoformat(),
                        rows,
                        "Debug mode lost; outputs forced to ALL OFF",
                        False,
                    )
                    self._monitor_stop.set()
                    self._active_profile = None
                    return
            except Exception as exc:  # hardware communication errors are reported, not hidden
                self._set_snapshot(
                    self._active_profile,
                    True,
                    datetime.now(timezone.utc).isoformat(),
                    [],
                    str(exc),
                    None,
                )
            self._monitor_stop.wait(0.25)

    def _set_snapshot(
        self,
        profile: str | None,
        monitoring: bool,
        updated_at: str | None,
        registers: list[dict],
        error: str | None,
        debug_active: bool | None = None,
    ) -> None:
        with self._snapshot_lock:
            self._status_snapshot = {
                "active_profile": profile,
                "monitoring": monitoring,
                "updated_at": updated_at,
                "debug_active": debug_active,
                "registers": registers,
                "error": error,
            }
