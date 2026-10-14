class TestResult:
    """所有UDS服务的统一返回类型"""

    def __init__(self, success: bool, data=None, nrc: int = None):
        self.success = success
        self.data = data
        self.nrc = nrc

    def __repr__(self):
        return f"<TestResult success={self.success}, data={self.data}, nrc={self.nrc}>"

    def __bool__(self):
        return self.success