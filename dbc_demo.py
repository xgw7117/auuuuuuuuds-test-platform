import cantools
import can

# 1. 加载DBC
db = cantools.database.load_file('demo.dbc')

# 2. 遍历所有报文和信号
for msg in db.messages:
    print(f"报文: {msg.name}, ID: 0x{msg.frame_id:X}, 长度: {msg.length}")
    for sig in msg.signals:
        print(f"  信号: {sig.name}, 起始位: {sig.start}, 长度: {sig.length}, 单位: {sig.unit}")

# 3. 编码：把物理值变成原始CAN数据
data = db.encode_message('EngineData', {
    'EngineSpeed': 1500,
    'VehicleSpeed': 80,
    'CoolantTemp': 90
})
print(f"\n编码后: {data.hex().upper()}")

# 4. 解码：把原始CAN数据还原成物理值
decoded = db.decode_message(0x123, data)
print(f"解码后: {decoded}")