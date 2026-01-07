import re
import time
from io import BytesIO
from PIL import Image
import pdb
from typing import Tuple, Dict

from prompt.sys_prompt import PROCEDURAL_MEMORY

import logging

# 获取通用工具模块的 logger
logger = logging.getLogger("ComputerAgent.utils.common_utils")


def create_pyautogui_code(agent, code: str, obs: Dict) -> str:
    """
    使用当前 observation（截图）对输入的代码进行 eval，
    生成基于 pyautogui 的可执行代码字符串。

    参数:
        agent (ACI): 用于执行 grounding 的 agent
        code (str): 需要 eval 的代码字符串（通常是 agent.xxx(...)）
        obs (Dict): 当前环境观测，必须包含 screenshot

    返回:
        exec_code (str): 生成的 pyautogui 可执行代码字符串

    异常:
        Exception: 当 eval 执行失败时抛出
    """
    # 为 agent 设置当前截图，用于坐标 / OCR grounding
    agent.assign_screenshot(obs)
    # 执行代码字符串（通常会调用 agent 的 action 方法）
    exec_code = eval(code)
    return exec_code


def call_llm_safe(
    agent, temperature: float = 0.0, use_thinking: bool = False, **kwargs
) -> str:
    """
    安全调用 LLM 接口，失败时自动重试。

    参数:
        agent: LLM agent 实例
        temperature (float): 采样温度
        use_thinking (bool): 是否启用思考模式
        **kwargs: 其他传给 agent.get_response 的参数

    返回:
        response (str): LLM 返回的文本结果
    """
    max_retries = 3  # 最大重试次数
    attempt = 0
    response = ""

    while attempt < max_retries:
        try:
            # pdb.set_trace()
            response = agent.get_response(
                temperature=temperature, use_thinking=use_thinking, **kwargs
            )
            assert response is not None, "LLM 返回结果不能为空"
            print(f"LLM 调用成功，返回结果: {response}")
            # logger.info(f"LLM 调用成功，返回结果: {response}")
            break
        except Exception as e:
            attempt += 1
            print(f"第 {attempt} 次调用失败: {e}")
            if attempt == max_retries:
                print("已达到最大重试次数，放弃调用")
        time.sleep(1.0)

    return response if response is not None else ""


def split_thinking_response(full_response: str) -> Tuple[str, str]:
    """
    从包含 <thoughts> 和 <answer> 标签的响应中，
    分离出最终回答和思考过程。

    参数:
        full_response (str): 完整 LLM 输出

    返回:
        answer (str): 最终回答内容
        thoughts (str): 思考过程内容
    """
    try:
        # 提取思考内容
        thoughts = full_response.split("<thoughts>")[-1].split("</thoughts>")[0].strip()
        # 提取最终回答
        answer = full_response.split("<answer>")[-1].split("</answer>")[0].strip()
        return answer, thoughts
    except Exception:
        # 如果解析失败，直接返回原始内容
        return full_response, ""


def call_llm_formatted(generator, format_checkers, **kwargs):
    """
    调用 LLM 并确保输出格式符合要求，不符合则给反馈并重试。

    参数:
        generator: 负责生成内容的 agent
        format_checkers (list[Callable]): 格式校验函数列表，
            每个函数返回 (success: bool, feedback: str)
        **kwargs: 传给 LLM 的额外参数

    返回:
        response (str): 最终符合格式要求的 LLM 输出
    """
    max_retries = 3  # 最大重试次数
    attempt = 0
    response = ""

    # 如果没有传 messages，则使用 agent 当前的 messages 副本
    if kwargs.get("messages") is None:
        messages = generator.messages.copy()
    else:
        messages = kwargs["messages"]
        del kwargs["messages"]  # 防止 messages 被重复传参

    while attempt < max_retries:
        response = call_llm_safe(generator, messages=messages, **kwargs)
        logger.info(f"第 {attempt} 次生成器返回结果: {response}")

        # 收集格式错误反馈
        feedback_msgs = []
        for format_checker in format_checkers:
            success, feedback = format_checker(response)
            if not success:
                feedback_msgs.append(feedback)

        # 如果没有格式错误，直接返回
        if not feedback_msgs:
            break

        logger.error(
            f"格式错误（第 {attempt} 次），模型 {generator.engine.model} 返回: {response}，"
            f"问题: {', '.join(feedback_msgs)}"
        )

        # 把错误响应加入对话历史
        messages.append(
            {
                "role": "assistant",
                "content": [{"type": "text", "text": response}],
            }
        )

        # 构造格式反馈提示
        delimiter = "\n- "
        formatting_feedback = f"- {delimiter.join(feedback_msgs)}"

        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": PROCEDURAL_MEMORY.FORMATTING_FEEDBACK_PROMPT.replace(
                            "FORMATTING_FEEDBACK", formatting_feedback
                        ),
                    }
                ],
            }
        )

        logger.info("格式反馈:\n%s", formatting_feedback)

        attempt += 1
        if attempt == max_retries:
            logger.error("格式修正已达到最大重试次数")

        time.sleep(1.0)

    return response


def parse_code_from_string(input_string):
    """
    从字符串中解析出被三反引号 ``` 包裹的代码块，
    返回最后一个代码块内容。

    参数:
        input_string (str): 包含代码块的字符串

    返回:
        str: 最后一个代码块内容，若不存在则返回空字符串
    """

    # logger.info("正在从字符串中解析代码块: %s", input_string)
    
    input_string = input_string.strip()

    # 匹配 ```code``` 或 ```python code``` 形式
    pattern = r"```(?:\w+\s+)?(.*?)```"

    matches = re.findall(pattern, input_string, re.DOTALL)
    if len(matches) == 0:
        return ""

    # 只取最后一个代码块（通常是最终 grounded action）
    return matches[-1]


def extract_agent_functions(code):
    """
    从代码字符串中提取所有 agent.xxx(...) 形式的函数调用。

    参数:
        code (str): 需要分析的代码字符串

    返回:
        list[str]: 匹配到的 agent 方法调用列表
    """
    # logger.info("正在从代码中提取 agent 函数调用: %s", code)
    pattern = r"(agent\.\w+\(\s*.*\))"
    return re.findall(pattern, code)
