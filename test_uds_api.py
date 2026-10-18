import pytest
import yaml
import allure


with open('testcases.yaml', 'r', encoding='utf-8') as f:
    test_cases = yaml.safe_load(f)


@allure.feature("UDS诊断服务测试")
@pytest.mark.parametrize("case", test_cases)
def test_uds_services(uds_client, case, request):
    if request.config.getoption("--uds-mode") == "hardware":
        if case['action'] == "security_access":
            pytest.skip("安全访问使用的是演示密钥算法，未配置 ECU 专属算法")
        if case.get("virtual_only"):
            pytest.skip("该用例的期望值仅适用于虚拟 ECU，请先配置目标 ECU 的期望值")
        if case['action'] == "write_data_by_id" and not request.config.getoption("--allow-write"):
            pytest.skip("硬件写 DID 需要显式指定 --allow-write")

    allure.dynamic.title(f"{case['name']} [{uds_client.transport.upper()}]")
    action = case['action']
    params = case.get('params', [])

    method = getattr(uds_client, action)
    result = method(*params)

    if 'expect_nrc' in case:
        assert result.success is False, f"期望失败，实际成功"
        assert result.nrc == case['expect_nrc'], f"期望NRC 0x{case['expect_nrc']:02X}，实际 0x{result.nrc:02X}"
        return

    if case.get('expect_success'):
        assert result.success is True, f"期望成功，实际失败，NRC=0x{result.nrc:02X}"
        return

    if 'expect_data' in case:
        assert result.success is True, f"期望成功，实际失败"
        assert result.data == case['expect_data'], f"期望 {case['expect_data']}，实际 {result.data}"
        return

    assert result.success is True, f"执行失败，NRC=0x{result.nrc:02X}"