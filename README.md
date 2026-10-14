# 车载 UDS 诊断自动化测试平台

基于 WSL + Python + pytest + YAML 搭建的车载 UDS 诊断自动化测试框架。

## 核心特性
- 底层通信：基于 python-can 和 udsoncan 封装，支持标准 UDS 诊断服务（0x10 / 0x27 / 0x22 / 0x1902）。
- 数据驱动：测试用例与代码分离，使用 YAML 管理测试数据，新增用例无需修改代码。
- 虚拟环境：基于 Linux vcan 构建纯软件仿真，无需真实 CAN 硬件即可进行闭环测试。
- 自动化报告：集成 pytest-html，一键生成可视化 HTML 测试报告。
- CI/CD：集成 GitHub Actions，代码提交后云端自动执行测试。

## 技术栈
- 语言：Python 3.10+
- 测试框架：pytest, pyyaml
- 协议与工具：python-can, udsoncan, can-isotp
- 开发环境：WSL (Ubuntu), VS Code

## 项目结构
- .github/workflows/ci.yml：CI/CD 流水线
- test_uds_api.py：pytest 测试脚本（调度层）
- uds_client.py：OOP 底层 UDS 通信封装（驱动层）
- testcases.yaml：YAML 数据驱动用例（数据层）
- README.md

## 如何运行
1. 克隆本项目：
   git clone https://github.com/xgw7117/auuuuuuuuds-test-platform.git
   cd auuuuuuuuds-test-platform

2. 安装依赖：
   pip3 install pytest pyyaml python-can udsoncan can-isotp --break-system-packages

3. 执行自动化测试：
   python3 -m pytest test_uds_api.py -s --html=report.html

## 测试报告
运行后会在当前目录生成 report.html，浏览器打开即可查看详细的测试用例通过情况。