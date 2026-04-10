from src.protocol.checksum import crc16


def test_empty_input_returns_zero():
    assert crc16(b"") == 0


def test_returns_16_bit_value():
    result = crc16(b"hello world")
    assert 0 <= result <= 0xFFFF


def test_deterministic():
    assert crc16(b"garmin") == crc16(b"garmin")


def test_different_input_different_checksum():
    assert crc16(b"hello") != crc16(b"world")


def test_single_byte_difference_changes_checksum():
    assert crc16(b"\x00") != crc16(b"\x01")


def test_init_value_affects_result():
    assert crc16(b"data", init=0) != crc16(b"data", init=1)


def test_accepts_bytearray():
    assert crc16(bytearray(b"test")) == crc16(b"test")
