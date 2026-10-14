import can
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s'
)
logger = logging.getLogger("NM")


def run_nm_demo():
    """模拟NM节点：发心跳5秒，然后停发，观察监控端判定睡眠"""
    bus = can.Bus(interface='virtual', channel='vcan0')
    NM_ID = 0x500
    NM_CYCLE = 0.2
    NM_TIMEOUT = 1.0

    logger.info("===== NM睡眠监控演示开始 =====")

    # 阶段1：正常发NM报文5秒
    logger.info("阶段1: 节点正常发送NM心跳（5秒）")
    start = time.time()
    last_nm_time = time.time()
    is_awake = True

    while time.time() - start < 8:  # 跑8秒，其中前5秒发心跳，后3秒停发
        elapsed = time.time() - start

        # 前5秒发心跳
        if elapsed < 5:
            msg = can.Message(
                arbitration_id=NM_ID,
                data=[0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],
                is_extended_id=False
            )
            bus.send(msg)
            logger.info(f"发送NM心跳: 数据={msg.data.hex().upper()}")
            last_nm_time = time.time()

        # 每100ms检查一次是否超时
        time.sleep(0.1)

        # 检查睡眠逻辑
        if is_awake and (time.time() - last_nm_time) > NM_TIMEOUT:
            logger.warning(f"💤 超过{NM_TIMEOUT}秒未收到NM报文，判定为睡眠！")
            is_awake = False

    logger.info("===== 演示结束 =====")
    bus.shutdown()


if __name__ == "__main__":
    run_nm_demo()
    