import can
import isotp
import udsoncan
import logging
from udsoncan.connections import PythonIsoTpConnection
from udsoncan.client import Client
from udsoncan.exceptions import NegativeResponseException

logger = logging.getLogger(__name__)


class TestResult:
    def __init__(self, success, data=None, nrc=None):
        self.success = success
        self.data = data
        self.nrc = nrc

    def __repr__(self):
        return f"<TestResult success={self.success}, data={self.data}, nrc={self.nrc}>"

    def __bool__(self):
        return self.success


class UdsClient:
    def __init__(self, channel='vcan0', tx_id=0x7E0, rx_id=0x7E8):
        self.tx_id = tx_id
        self.rx_id = rx_id

        logger.info(f"初始化UdsClient: channel={channel}, tx=0x{tx_id:X}, rx=0x{rx_id:X}")

        self.bus = can.Bus(interface='virtual', channel=channel)
        self.isotp_layer = isotp.CanStack(
            bus=self.bus,
            address=isotp.Address(
                isotp.AddressingMode.Normal_11bits,
                txid=self.tx_id,
                rxid=self.rx_id
            )
        )
        self.conn = PythonIsoTpConnection(self.isotp_layer)

        self.config = {
            'request_timeout': 5.0,
            'p2_timeout': 5.0,          # 关键：把P2也改成5秒
            'p2_star_timeout': 10.0,
            'data_identifiers': {
                0xF190: udsoncan.AsciiCodec(17),
                0x1902: udsoncan.AsciiCodec(4),
                0xFFFF: udsoncan.AsciiCodec(4)
            }
        }

    def __enter__(self):
        self.client = Client(self.conn, config=self.config)
        self.client.__enter__()
        logger.info("UDS客户端已连接")
        return self

    def __exit__(self, *args):
        self.client.__exit__(*args)
        self.bus.shutdown()
        logger.info("UDS客户端已关闭")

    def change_session(self, sub_func=0x03):
        if isinstance(sub_func, str):
            sub_func = int(sub_func, 16)
        try:
            self.client.change_session(sub_func)
            logger.info(f"[PASS] 进入扩展会话成功 (0x10 0x{sub_func:02X})")
            return TestResult(True)
        except NegativeResponseException as e:
            logger.error(f"[FAIL] 进入会话失败, NRC=0x{e.response.code:02X}")
            return TestResult(False, nrc=e.response.code)

    def security_access(self, seed_level=0x01):
        if isinstance(seed_level, str):
            seed_level = int(seed_level, 16)
        try:
            resp = self.client.request_seed(seed_level)
            seed = resp.data[2:]
            logger.info(f"[STEP] 收到种子: {seed.hex().upper()}")
            key = bytes([s ^ 0xA5 for s in seed])
            self.client.send_key(seed_level + 1, key)
            logger.info("[PASS] 安全访问解锁成功")
            return TestResult(True)
        except NegativeResponseException as e:
            logger.error(f"[FAIL] 安全访问失败, NRC=0x{e.response.code:02X}")
            return TestResult(False, nrc=e.response.code)

    def read_data_by_id(self, did=0xF190):
        if isinstance(did, str):
            did = int(did, 16)
        try:
            resp = self.client.read_data_by_identifier(did)
            data = resp.service_data.values[did]
            logger.info(f"[PASS] 读数据成功 DID=0x{did:04X}, 数据={data}")
            return TestResult(True, data=data)
        except NegativeResponseException as e:
            logger.error(f"[FAIL] 读数据失败, NRC=0x{e.response.code:02X}")
            return TestResult(False, nrc=e.response.code)

    def write_data_by_id(self, did, data):
        if isinstance(did, str):
            did = int(did, 16)
        try:
            self.client.write_data_by_identifier(did, data)
            logger.info(f"[PASS] 写数据成功 DID=0x{did:04X}")
            return TestResult(True)
        except NegativeResponseException as e:
            logger.error(f"[FAIL] 写数据失败, NRC=0x{e.response.code:02X}")
            return TestResult(False, nrc=e.response.code)

    def read_dtc(self, status_mask=0x08):
        if isinstance(status_mask, str):
            status_mask = int(status_mask, 16)
        try:
            dtcs = self.client.get_dtc_by_status_mask(status_mask)
            logger.info(f"[PASS] 读DTC成功, 共 {len(dtcs)} 条")
            return TestResult(True, data=dtcs)
        except NegativeResponseException as e:
            logger.error(f"[FAIL] 读DTC失败, NRC=0x{e.response.code:02X}")
            return TestResult(False, nrc=e.response.code)