from utils import (
    hex_str_to_bytes, bytes_to_hex_str,
    parse_dtc_status, crc8_sae_j1850
)


def test_hex_str_to_bytes():
    assert hex_str_to_bytes("02 10 03") == b'\x02\x10\x03'
    assert hex_str_to_bytes("62 F1 90 4C 53 56 41") == b'\x62\xF1\x90\x4c\x53\x56\x41'
    assert hex_str_to_bytes("0x02,0x10,0x03") == b'\x02\x10\x03'
    assert hex_str_to_bytes("021003") == b'\x02\x10\x03'


def test_bytes_to_hex_str():
    assert bytes_to_hex_str(b'\x62\xF1\x90') == "62 F1 90"
    assert bytes_to_hex_str(b'\x02\x10\x03') == "02 10 03"


def test_parse_dtc_status():
    assert parse_dtc_status(0x09) == ["testFailed", "confirmedDTC"]
    assert parse_dtc_status(0x00) == []
    assert parse_dtc_status(0x80) == ["warningIndicatorRequested"]


def test_crc8():
    assert crc8_sae_j1850(b'\x00') == 0x3B
    assert crc8_sae_j1850(b'\x01') == 0x26
    