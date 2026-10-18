import pytest
import logging
import sys
import socket
import struct
import threading
import time
import yaml
import can
import isotp
from uds_client import UdsClient


def _parse_int(value):
    return int(value, 0)


def pytest_addoption(parser):
    group = parser.getgroup("uds")
    group.addoption("--uds-mode", choices=["virtual", "hardware"], default="virtual")
    group.addoption("--uds-transport", choices=["can", "doip", "both"], default="both")
    group.addoption("--can-interface", default="virtual")
    group.addoption("--can-channel", default="vcan0")
    group.addoption("--can-tx-id", type=_parse_int, default=0x7E0)
    group.addoption("--can-rx-id", type=_parse_int, default=0x7E8)
    group.addoption("--doip-host", default=None)
    group.addoption("--doip-port", type=int, default=13400)
    group.addoption("--doip-ecu-address", type=_parse_int, default=0x1001)
    group.addoption("--doip-client-address", type=_parse_int, default=0x0E00)
    group.addoption("--allow-write", action="store_true", default=False)


def pytest_generate_tests(metafunc):
    if "uds_transport" not in metafunc.fixturenames:
        return
    selected = metafunc.config.getoption("--uds-transport")
    transports = ["can", "doip"] if selected == "both" else [selected]
    metafunc.parametrize("uds_transport", transports, ids=[name.upper() for name in transports])


def _handle_uds_request(uds_data):
    service = uds_data[0]
    if service == 0x10:
        return bytes([0x50, 0x03, 0x01, 0xF4, 0x01, 0xF4])
    if service == 0x27:
        if uds_data[1] == 0x01:
            return bytes([0x67, 0x01, 0xAA, 0xBB, 0xCC, 0xDD])
        if uds_data[1] == 0x02:
            return bytes([0x67, 0x02])
    elif service == 0x22:
        if uds_data[1:3] == [0xF1, 0x90]:
            return bytes([0x62, 0xF1, 0x90]) + b"LSVAA1234567890AB"
        if uds_data[1:3] == [0x19, 0x02]:
            return bytes([0x62, 0x19, 0x02]) + b"DEMO"
        if uds_data[1:3] == [0xFF, 0xFF]:
            return bytes([0x7F, 0x22, 0x31])
    elif service == 0x2E:
        return bytes([0x6E, uds_data[1], uds_data[2]])
    elif service == 0x19:
        return bytes([
            0x59, 0x02, 0xFF, 0x00, 0x02,
            0x12, 0x34, 0x56, 0x78, 0x08,
            0x65, 0x43, 0x21, 0x87, 0x08,
        ])
    return None


def _recv_exact(conn, size):
    data = bytearray()
    while len(data) < size:
        try:
            chunk = conn.recv(size - len(data))
        except socket.timeout:
            continue
        except OSError:
            return None
        if not chunk:
            return None
        data.extend(chunk)
    return bytes(data)


def _pack_doip(payload_type, payload):
    header = struct.pack("!BBHI", 0x02, 0xFD, payload_type, len(payload))
    return header + payload


class _DoIPVirtualECU:
    ecu_logical_address = 0x1001

    def __init__(self):
        self._stopped = threading.Event()
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("127.0.0.1", 0))
        self._server.listen()
        self._server.settimeout(0.2)
        self.port = self._server.getsockname()[1]
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self):
        while not self._stopped.is_set():
            try:
                conn, _ = self._server.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()

    def _handle_client(self, conn):
        with conn:
            conn.settimeout(0.2)
            while not self._stopped.is_set():
                header = _recv_exact(conn, 8)
                if header is None:
                    return
                version, inverse, payload_type, payload_length = struct.unpack("!BBHI", header)
                payload = _recv_exact(conn, payload_length)
                if payload is None or inverse != (version ^ 0xFF):
                    return

                if payload_type == 0x0005 and len(payload) >= 3:
                    client_address = struct.unpack("!H", payload[:2])[0]
                    activation = struct.pack(
                        "!HHBL", client_address, self.ecu_logical_address, 0x10, 0
                    )
                    conn.sendall(_pack_doip(0x0006, activation))
                elif payload_type == 0x8001 and len(payload) >= 5:
                    client_address, _ = struct.unpack("!HH", payload[:4])
                    ack = struct.pack("!HHB", self.ecu_logical_address, client_address, 0)
                    conn.sendall(_pack_doip(0x8002, ack))
                    response = _handle_uds_request(list(payload[4:]))
                    if response is not None:
                        addresses = struct.pack(
                            "!HH", self.ecu_logical_address, client_address
                        )
                        conn.sendall(_pack_doip(0x8001, addresses + response))

    def close(self):
        self._stopped.set()
        self._server.close()
        self._thread.join(timeout=1)


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
def _run_virtual_ecu(stop_event):
    bus = can.Bus(interface='virtual', channel='vcan0')
    ecu_isotp = isotp.CanStack(
        bus=bus,
        address=isotp.Address(
            isotp.AddressingMode.Normal_11bits,
            txid=0x7E8,
            rxid=0x7E0
        )
    )

    try:
        while not stop_event.is_set():
            try:
                ecu_isotp.process()
                uds_data = ecu_isotp.recv()
                if uds_data is None:
                    stop_event.wait(0.001)
                    continue
                response = _handle_uds_request(list(uds_data))
                if response is not None:
                    ecu_isotp.send(response)
            except Exception:
                logging.exception("虚拟 ECU 处理请求时发生异常")
                stop_event.wait(0.01)
    finally:
        bus.shutdown()


@pytest.fixture(scope="session")
def start_virtual_ecu():
    stop_event = threading.Event()
    t = threading.Thread(target=_run_virtual_ecu, args=(stop_event,), daemon=True)
    t.start()
    time.sleep(2)
    logging.info("虚拟ECU已启动")
    yield
    stop_event.set()
    t.join(timeout=1)


@pytest.fixture(scope="session")
def doip_virtual_ecu():
    ecu = _DoIPVirtualECU()
    yield ecu
    ecu.close()


@pytest.fixture(scope="function")
def uds_client(request, uds_transport):
    transport = uds_transport
    config = request.config
    virtual_mode = config.getoption("--uds-mode") == "virtual"

    if virtual_mode:
        request.getfixturevalue("start_virtual_ecu")

    options = {}
    if transport == "can":
        options.update(
            can_interface=config.getoption("--can-interface"),
            channel=config.getoption("--can-channel"),
            tx_id=config.getoption("--can-tx-id"),
            rx_id=config.getoption("--can-rx-id"),
        )
    if transport == "doip":
        options.update(
            ecu_logical_address=config.getoption("--doip-ecu-address"),
            client_logical_address=config.getoption("--doip-client-address"),
            tcp_port=config.getoption("--doip-port"),
        )
        if virtual_mode:
            ecu = request.getfixturevalue("doip_virtual_ecu")
            options.update(
                ecu_ip_address="127.0.0.1",
                ecu_logical_address=ecu.ecu_logical_address,
                tcp_port=ecu.port,
            )
        else:
            host = config.getoption("--doip-host")
            if not host:
                pytest.fail("硬件 DoIP 模式必须通过 --doip-host 指定 ECU IP 地址")
            options["ecu_ip_address"] = host

    with UdsClient(transport=transport, **options) as c:
        yield c