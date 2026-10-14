import pytest
import logging
import sys
import threading
import time
import yaml
import can
import isotp
from uds_client import UdsClient


# ==========================
# 全局日志配置
# ==========================
def pytest_configure(config):
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    if root_logger.handlers:
        return

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(lineno)d - %(levelname)s - %(message)s"
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler("uds_test.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


# ==========================
# 虚拟ECU线程
# ==========================
def _run_virtual_ecu():
    bus = can.Bus(interface='virtual', channel='vcan0')
    ecu_isotp = isotp.CanStack(
        bus=bus,
        address=isotp.Address(
            isotp.AddressingMode.Normal_11bits,
            txid=0x7E8,
            rxid=0x7E0
        )
    )

    while True:
        try:
            ecu_isotp.process()
            uds_data = ecu_isotp.recv()
            if uds_data is None:
                continue
            uds_data = list(uds_data)
            service = uds_data[0]
            resp = []

            if service == 0x10:
                resp = [0x50, 0x03, 0x00, 0x32, 0x01, 0xF4]
            elif service == 0x27:
                if uds_data[1] == 0x01:
                    resp = [0x67, 0x01, 0xAA, 0xBB, 0xCC, 0xDD]
                elif uds_data[1] == 0x02:
                    resp = [0x67, 0x02]
            elif service == 0x22:
                if uds_data[1] == 0xF1 and uds_data[2] == 0x90:
                    vin = "LSVAA1234567890AB"
                    resp = [0x62, 0xF1, 0x90] + list(vin.encode('ascii'))
                elif uds_data[1] == 0x19 and uds_data[2] == 0x02:
                    resp = [0x62, 0x19, 0x02, 0xAA, 0xBB, 0xCC, 0xDD]
                elif uds_data[1] == 0xFF and uds_data[2] == 0xFF:
                    resp = [0x7F, 0x22, 0x31]
            elif service == 0x2E:
                resp = [0x6E, uds_data[1], uds_data[2]]
            elif service == 0x19:
                resp = [0x59, 0x02, 0xFF, 0x00, 0x02,
                        0x12, 0x34, 0x56, 0x78, 0x08,
                        0x65, 0x43, 0x21, 0x87, 0x08]

            if resp:
                ecu_isotp.send(bytes(resp))
        except Exception:
            pass


@pytest.fixture(scope="session", autouse=True)
def start_virtual_ecu():
    t = threading.Thread(target=_run_virtual_ecu, daemon=True)
    t.start()
    time.sleep(2)
    logging.info("虚拟ECU已启动")
    yield


@pytest.fixture(scope="session")
def uds_client(start_virtual_ecu):
    with UdsClient() as c:
        yield c