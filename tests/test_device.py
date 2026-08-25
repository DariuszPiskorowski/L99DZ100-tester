import pytest

from app.core.device import L99DZ100, Opcode
from app.mock import MockSpiPort


def test_frame_encoding_and_response_decoding():
    class Spy:
        def transfer(self, data):
            assert data == bytes((Opcode.READ << 6 | 0x01, 0, 0, 0))
            return bytes.fromhex("80234567")
        def close(self): pass
    response = L99DZ100(Spy()).read(0x01)
    assert response.global_status == 0x80
    assert response.payload == 0x234567


def test_write_read_and_selective_clear():
    device = L99DZ100(MockSpiPort())
    device.write(0x01, 0xABCDEF)
    assert device.read(0x01).payload == 0xABCDEF
    device.spi.application[0x31] = 0xFFFFFF
    old = device.read_clear(0x31, 0x00FF00)
    assert old.payload == 0xFFFFFF
    assert device.read(0x31).payload == 0xFF00FF


def test_access_rules_are_enforced():
    device = L99DZ100(MockSpiPort())
    with pytest.raises(ValueError): device.write(0x31, 1)
    with pytest.raises(ValueError): device.read_clear(0x01, 1)
    with pytest.raises(ValueError): device.read(0x23)


def test_device_identification():
    assert L99DZ100(MockSpiPort()).device_info()["is_l99dz100g"] is True

