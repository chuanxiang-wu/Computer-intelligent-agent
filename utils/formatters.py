from utils.common_utils import (
    split_thinking_response,
    create_pyautogui_code,
    parse_code_from_string,
    extract_agent_functions,
)

import logging

logger = logging.getLogger("ComputerAgent.utils.formatters")



# 校验：代码响应中必须且只能包含一个 agent action
single_action_check = (
    lambda response: len(
        extract_agent_functions(
            parse_code_from_string(response)
        )
    ) == 1
)

# 单一 action 校验失败时的错误提示
single_action_error_msg = (
    "Incorrect code: The code response must contain exactly one agent action."
)

# 单一 action 校验格式器，返回 (是否通过, 错误信息)
SINGLE_ACTION_FORMATTER = lambda response: (
    single_action_check(response),
    single_action_error_msg,
)


def _attempt_code_creation(agent, code, obs):
    """尝试根据响应代码生成一段 pyautogui 代码"""
    try:
        return create_pyautogui_code(agent, code, obs)
    except Exception:
        return None


# 校验：agent action 是否为合法函数，且参数符合文档字符串中定义的范围
code_valid_check = (
    lambda agent, obs, response: _attempt_code_creation(
        agent,
        parse_code_from_string(response),
        obs,
    )
    is not None
)

# 代码合法性校验失败时的错误提示
code_valid_error_msg = (
    "代理动作必须为有效函数并使用文档字符串列表中的有效参数。"
)

# 代码合法性校验格式器，返回 (是否通过, 错误信息)
CODE_VALID_FORMATTER = lambda agent, obs, response: (
    code_valid_check(agent, obs, response),
    code_valid_error_msg,
)

# 校验：响应中必须包含非空的 <thoughts>...</thoughts> 和 <answer>...</answer> 标签
thoughts_answer_tag_check = lambda response: split_thinking_response(response)[1] != ""
thoughts_answer_tag_error_msg = "Incorrect response: The response must contain both <thoughts>...</thoughts> and <answer>...</answer> tags."
THOUGHTS_ANSWER_TAG_FORMATTER = lambda response: (
    thoughts_answer_tag_check(response),
    thoughts_answer_tag_error_msg,
)

integer_answer_check = (
    lambda response: split_thinking_response(response)[0].strip().isdigit()
)
integer_answer_error_msg = (
    "Incorrect response: The <answer>...</answer> tag must contain a single integer."
)
INTEGER_ANSWER_FORMATTER = lambda response: (
    integer_answer_check(response),
    integer_answer_error_msg,
)