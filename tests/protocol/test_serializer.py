from src.protocol.serializer import (
    garmin_timestamp, garmin_coordinate, clamp_temperature,
    pack_string, definition, data, GARMIN_EPOCH,
)


# --- garmin_timestamp ---

def test_garmin_timestamp_subtracts_epoch():
    assert garmin_timestamp(GARMIN_EPOCH) == 0


def test_garmin_timestamp_positive_for_recent_time():
    assert garmin_timestamp(1712764800) > 0


# --- garmin_coordinate ---

def test_garmin_coordinate_zero():
    assert garmin_coordinate(0.0) == 0


def test_garmin_coordinate_positive():
    assert garmin_coordinate(90.0) > 0


def test_garmin_coordinate_negative():
    assert garmin_coordinate(-90.0) < 0


def test_garmin_coordinate_symmetry():
    assert garmin_coordinate(45.0) == -garmin_coordinate(-45.0)


# --- clamp_temperature ---

def test_clamp_temperature_within_range():
    assert clamp_temperature(22.3) == 22


def test_clamp_temperature_clamps_high():
    assert clamp_temperature(200) == 127


def test_clamp_temperature_clamps_low():
    assert clamp_temperature(-200) == -128


def test_clamp_temperature_rounds():
    assert clamp_temperature(22.4) == 22
    assert clamp_temperature(22.6) == 23


# --- pack_string ---

def test_pack_string_pads_to_size():
    assert len(pack_string("hi", 15)) == 15


def test_pack_string_truncates_long_input():
    assert len(pack_string("a" * 100, 15)) == 15


def test_pack_string_null_terminated():
    result = pack_string("hi", 15)
    assert result[2] == 0


# --- definition ---

def test_definition_starts_with_definition_flag():
    result = definition(0, 128, [(0, 1, 0x00)])
    assert result[0] & 0x40 == 0x40


def test_definition_contains_field_count():
    fields = [(0, 1, 0x00), (1, 1, 0x01), (2, 2, 0x84)]
    result = definition(0, 128, fields)
    assert result[5] == 3


# --- data ---

def test_data_starts_with_local_type():
    result = data(2, "<B", 42)
    assert result[0] == 2


def test_data_contains_packed_value():
    result = data(0, "<B", 42)
    assert result[1] == 42
