import re
import logging

logger = logging.getLogger(__name__)


def hex_str_to_bytes(hex_str):
    """'02 10 03' / '0x02,0x10,0x03' / '02-10-03' / '021003'
     """
    if not isinstance(hex_str, str):
        raise TypeError(f"期望str，实际得到 {type(hex_str)}")

    cleaned = re.sub(r'0[xX]', '', hex_str)
    cleaned = re.sub(r'[,;\-\n\t]', ' ', cleaned)
    cleaned = cleaned.strip()

    if not cleaned:
        raise ValueError("空字符串无法转换")

    if ' ' not in cleaned and len(cleaned) % 2 == 0:
        cleaned = ' '.join(cleaned[i:i+2] for i in range(0, len(cleaned), 2))

    try:
        return bytes(int(byte_str, 16) for byte_str in cleaned.split())
    except ValueError as e:
        raise ValueError(f"十六进制字符串格式错误: {hex_str}, 错误: {e}")
        


def bytes_to_hex_str(data):
    """b'\x62\xF1\x90' -> '62 F1 90'"""
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError(f"期望bytes或bytearray，实际得到 {type(data)}")
    return ' '.join(f'{b:02X}' for b in data)


DTC_STATUS_BITS = {
    0: "testFailed",
    1: "testFailedThisOperationCycle",
    2: "pendingDTC",
    3: "confirmedDTC",
    4: "testNotCompletedSinceLastClear",
    5: "testFailedSinceLastClear",
    6: "testNotCompletedThisOperationCycle",
    7: "warningIndicatorRequested",
}


def parse_dtc_status(status_byte):
    """解析DTC状态字节，返回置位的状态列表"""
    if not isinstance(status_byte, int) or not (0 <= status_byte <= 0xFF):
        raise ValueError(f"状态字节必须是0-0xFF的整数，实际: {status_byte}")
    return [name for bit, name in DTC_STATUS_BITS.items() if status_byte & (1 << bit)]


def crc8_sae_j1850(data):
    """CRC-8/SAE-J1850，多项式0x1D，初始值0xFF，结果异或0xFF"""
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError(f"期望bytes或bytearray，实际得到 {type(data)}")

    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x1D) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc ^ 0xFF