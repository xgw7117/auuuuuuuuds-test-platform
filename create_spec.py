import pandas as pd

spec = [
    {"Service": "0x10", "SubFunction": "0x03", "Data": "", "Description": "进入扩展会话", "Expect": "50 03"},
    {"Service": "0x27", "SubFunction": "0x01", "Data": "", "Description": "请求安全种子", "Expect": "67 01"},
    {"Service": "0x27", "SubFunction": "0x02", "Data": "A5 5A A5 5A", "Description": "发送密钥", "Expect": "67 02"},
    {"Service": "0x22", "SubFunction": "", "Data": "F1 90", "Description": "读取VIN码", "Expect": "LSVAA1234567890AB"},
    {"Service": "0x22", "SubFunction": "", "Data": "19 02", "Description": "读取DTC", "Expect": "AA BB CC DD"},
    {"Service": "0x22", "SubFunction": "", "Data": "FF FF", "Description": "读不存在的DID", "Expect": "NRC 0x31"},
]

df = pd.DataFrame(spec)
df.to_excel("diagnostic_spec.xlsx", index=False)
print("[OK] diagnostic_spec.xlsx 已生成")