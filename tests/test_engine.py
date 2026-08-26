import pytest

from app.core.device import L99DZ100
from app.core.engine import TestEngine
from app.core.registers import (
    CR1_HEN,
    CR11_ECON,
    CR11_ECV_LS,
    OUTPUTS_HIGH_PROFILE,
    OUTPUTS_LOW_PROFILE,
    SR1_DEBUG_ACTIVE,
)
from app.mock import MockSpiPort


def make_engine():
    spi = MockSpiPort()
    return spi, TestEngine(L99DZ100(spi))


def test_reserved_register_gap_is_rejected():
    spi, engine = make_engine()
    with pytest.raises(ValueError):
        engine.device.read(0x1E)
    assert engine.device.read(0x22).payload == 0


def test_output_high_is_blocked_without_debug_and_writes_nothing():
    spi, engine = make_engine()
    spi.application[0x31] &= ~SR1_DEBUG_ACTIVE

    result = engine.run("outputs_high")

    assert result.passed is False
    assert result.details["blocked"] is True
    for address in (0x04, 0x05, 0x06):
        assert spi.application[address] == 0


def test_outputs_high_profile_and_all_off():
    spi, engine = make_engine()

    result = engine.run("outputs_high")
    assert result.passed is True
    for address, expected in OUTPUTS_HIGH_PROFILE.items():
        assert spi.application[address] == expected

    # Seed independently controlled output paths so ALL OFF must clear them too.
    spi.application[0x01] |= CR1_HEN
    spi.application[0x0B] |= CR11_ECON | CR11_ECV_LS

    off = engine.run("all_off")
    assert off.passed is True
    assert not (spi.application[0x01] & CR1_HEN)
    assert not (spi.application[0x0B] & (CR11_ECON | CR11_ECV_LS))
    for address in (0x04, 0x05, 0x06):
        assert spi.application[address] == 0


def test_outputs_low_profile():
    spi, engine = make_engine()

    result = engine.run("outputs_low")
    assert result.passed is True
    for address, expected in OUTPUTS_LOW_PROFILE.items():
        assert spi.application[address] == expected

    engine.run("all_off")


def test_live_status_is_cached_and_monitor_stops_on_all_off():
    spi, engine = make_engine()

    assert engine.run("outputs_high").passed is True
    snapshot = engine.live_status()
    assert snapshot["active_profile"] == "OUTPUTS HIGH"
    assert snapshot["monitoring"] is True

    assert engine.run("all_off").passed is True
    snapshot = engine.live_status()
    assert snapshot["active_profile"] is None
    assert snapshot["monitoring"] is False
