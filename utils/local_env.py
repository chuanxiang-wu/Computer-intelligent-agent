import subprocess
import sys
from typing import Dict


class LocalController:
    """最小化控制器，用于在本地执行 Bash 和 Python 代码。

    警告：执行任意代码是危险的。请仅在受信任环境和可信输入下使用。
    """

    def run_bash_script(self, code: str, timeout: int = 30) -> Dict:
        """在本地执行 Bash 脚本。

        参数:
            code (str): 要执行的 Bash 代码
            timeout (int): 最大执行时间，单位秒，默认 30 秒

        返回:
            Dict: 包含执行状态、输出、错误信息的字典
        """
        try:
            proc = subprocess.run(
                ["/bin/bash", "-lc", code],  # 启动 login shell 执行代码
                capture_output=True,  # 捕获 stdout 和 stderr
                text=True,  # 输出为文本
                timeout=timeout,  # 超时限制
            )
            output = (proc.stdout or "") + (proc.stderr or "")

            # 打印执行输出（调试用）
            print("BASH OUTPUT =======================================")
            print(output)
            print("BASH OUTPUT =======================================")

            return {
                "status": "ok" if proc.returncode == 0 else "error",
                "returncode": proc.returncode,
                "output": output,
                "error": "",
            }
        except subprocess.TimeoutExpired as e:
            # Bash 执行超时
            return {
                "status": "error",
                "returncode": -1,
                "output": e.stdout or "",
                "error": f"TimeoutExpired: {str(e)}",
            }
        except Exception as e:
            # 其他异常
            return {
                "status": "error",
                "returncode": -1,
                "output": "",
                "error": str(e),
            }

    def run_python_script(self, code: str) -> Dict:
        """在本地执行 Python 脚本。

        参数:
            code (str): 要执行的 Python 代码

        返回:
            Dict: 包含执行状态、输出、错误信息的字典
        """
        try:
            proc = subprocess.run(
                [sys.executable, "-c", code],  # 使用当前 Python 解释器执行代码
                capture_output=True,  # 捕获 stdout 和 stderr
                text=True,  # 输出为文本
            )
            # 打印执行输出（调试用）
            print("PYTHON OUTPUT =======================================")
            print(proc.stdout or "")
            print("PYTHON OUTPUT =======================================")
            return {
                "status": "ok" if proc.returncode == 0 else "error",
                "return_code": proc.returncode,
                "output": proc.stdout or "",
                "error": proc.stderr or "",
            }
        except Exception as e:
            # 异常处理
            return {
                "status": "error",
                "return_code": -1,
                "output": "",
                "error": str(e),
            }


class LocalEnv:
    """简单环境，提供一个与 CodeAgent 兼容的控制器。"""

    def __init__(self):
        # 创建本地控制器实例
        self.controller = LocalController()
