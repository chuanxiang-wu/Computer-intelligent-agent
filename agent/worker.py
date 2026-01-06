from functools import partial
import logging
import textwrap
from typing import Dict, List, Tuple
import pdb
from utils.grounding import ACI
from core.model import BaseModule
from prompt.sys_prompt import PROCEDURAL_MEMORY
from utils.common_utils import call_llm_safe, split_thinking_response, call_llm_formatted, create_pyautogui_code, parse_code_from_string

from utils.formatters import SINGLE_ACTION_FORMATTER, CODE_VALID_FORMATTER

logger = logging.getLogger("ComputerAgent.agent.worker")


class Worker(BaseModule):
    def __init__(
        self,
        worker_engine_params: Dict,
        grounding_agent: ACI,
        platform: str = "windows",
        max_trajectory_length: int = 8,
        enable_reflection: bool = True,
        use_thinking: bool = True,
    ):
        """
        Worker 接收主要任务并生成动作，不依赖层级规划。
        
        参数:
            worker_engine_params: Dict
                Worker agent 的参数
            grounding_agent: Agent
                使用的 grounding agent
            platform: str
                Agent 所在操作系统 (darwin, linux, windows)
            max_trajectory_length: int
                保留的历史截图和操作轮次
            enable_reflection: bool
                是否启用反思功能
            use_thinking: bool
                是否启用“思考模式”
        """
        super().__init__(worker_engine_params, platform)
        self.grounding_agent = grounding_agent
        self.max_trajectory_length = max_trajectory_length  
        self.enable_reflection = enable_reflection

        self.temperature = worker_engine_params.get("temperature", 0.0)
        self.use_thinking = use_thinking

        self.reset()


    def reset(self):
        # 根据平台跳过某些 action
        if self.platform != "linux":
            skipped_actions = ["set_cell_values"]
        else:
            skipped_actions = []

        # 如果没有 env 或 controller，则隐藏 code agent action
        if not getattr(self.grounding_agent, "env", None) or not getattr(
            getattr(self.grounding_agent, "env", None), "controller", None
        ):
            skipped_actions.append("call_code_agent")

        sys_prompt = PROCEDURAL_MEMORY.construct_simple_worker_procedural_memory(
            type(self.grounding_agent), skipped_actions=skipped_actions
        ).replace("CURRENT_OS", self.platform)

        # 创建生成 agent 和反思 agent
        self.generator_agent = self._create_agent(sys_prompt)
        self.reflection_agent = self._create_agent(
            PROCEDURAL_MEMORY.REFLECTION_ON_TRAJECTORY
        )

        # 初始化状态变量
        self.turn_count = 0
        self.worker_history = []
        self.reflections = []
        self.cost_this_turn = 0
        self.screenshot_inputs = []


    def flush_messages(self):
        """
        根据模型上下文限制刷新消息历史。

        该方法确保 agent 的消息历史不会超过最大轨迹长度。

        副作用:
            - 修改 generator、reflection agent 的消息以适应上下文限制
        """
        engine_type = self.engine_params.get("engine_type", "")

        # 长上下文模型策略：保留所有文本，只保留最新的图片
        if engine_type in ["openai"]:
            max_images = self.max_trajectory_length
            for agent in [self.generator_agent, self.reflection_agent]:
                if agent is None:
                    continue
                # 保留最近 k 张图片
                img_count = 0
                for i in range(len(agent.messages) - 1, -1, -1):
                    for j in range(len(agent.messages[i]["content"])):
                        if "image" in agent.messages[i]["content"][j].get("type", ""):
                            img_count += 1
                            if img_count > max_images:
                                del agent.messages[i]["content"][j]

        # 非长上下文模型策略：删除整个轮次消息
        else:
            # generator 消息轮流交替 [user, assistant]，每轮 2 条
            if len(self.generator_agent.messages) > 2 * self.max_trajectory_length + 1:
                self.generator_agent.messages.pop(1)
                self.generator_agent.messages.pop(1)
            # reflection 消息每轮 1 条 [(user text, user image)]
            if len(self.reflection_agent.messages) > self.max_trajectory_length + 1:
                self.reflection_agent.messages.pop(1)


    def _generate_reflection(self, instruction: str, obs: Dict) -> Tuple[str, str]:
        """
        基于当前观察和任务指令生成反思。

        参数:
            instruction (str): 当前任务指令
            obs (Dict): 当前观察结果，包含截图等信息

        返回:
            Optional[str, str]: 生成的反思文本和思考内容 (turn_count > 0 时可能存在)

        副作用:
            - 更新 reflection agent 的消息历史
            - 使用 API 调用生成反思
        """
        reflection = None
        reflection_thoughts = None
        if self.enable_reflection:
            # 加载初始消息
            if self.turn_count == 0:
                text_content = textwrap.dedent(
                    f"""
                    任务描述: {instruction}
                    当前轨迹如下:
                    """
                )
                updated_sys_prompt = (
                    self.reflection_agent.system_prompt + "\n" + text_content
                )
                self.reflection_agent.add_system_prompt(updated_sys_prompt)
                self.reflection_agent.add_message(
                    text_content="提供了初始屏幕，尚未执行任何动作。",
                    image_content=obs["screenshot"],
                    role="user",
                )
            # 加载最新动作
            else:
                self.reflection_agent.add_message(
                    text_content=self.worker_history[-1],
                    image_content=obs["screenshot"],
                    role="user",
                )
                full_reflection = call_llm_safe(
                    self.reflection_agent,
                    temperature=self.temperature,
                    use_thinking=self.use_thinking,
                )
                reflection, reflection_thoughts = split_thinking_response(
                    full_reflection
                )
                self.reflections.append(reflection)
                logger.info("REFLECTION THOUGHTS: %s", reflection_thoughts)
                logger.info("REFLECTION: %s", reflection)
        return reflection, reflection_thoughts


    def generate_next_action(self, instruction: str, obs: Dict) -> Tuple[Dict, List]:
        """
        基于当前观察生成下一步动作（action）。

        参数:
            instruction (str): 当前任务指令
            obs (Dict): 当前观察结果，包含截图等信息

        返回:
            Tuple[Dict, List]: 包含执行信息的字典和动作列表
        """

        # 将当前截图和任务指令分配给 grounding agent
        self.grounding_agent.assign_screenshot(obs)
        self.grounding_agent.set_task_instruction(instruction)

        # 如果是第一轮，则初始化消息内容
        generator_message = (
            ""
            if self.turn_count > 0
            else "提供了初始屏幕，尚未执行任何动作。"
        )

        # 在系统提示中加载任务
        if self.turn_count == 0:
            prompt_with_instructions = self.generator_agent.system_prompt.replace(
                "TASK_DESCRIPTION", instruction
            )
            self.generator_agent.add_system_prompt(prompt_with_instructions)

        # 获取每一步的反思
        reflection, reflection_thoughts = self._generate_reflection(instruction, obs)
        if reflection:
            generator_message += f"REFLECTION: 可以利用以下反思改进前一步动作或整体轨迹：\n{reflection}\n"

        # 加入 grounding agent 的文本缓冲知识
        generator_message += (
            f"\n当前文本缓冲 = [{','.join(self.grounding_agent.notes)}]\n"
        )
        logger.info("generator_message: %s", generator_message)
        pdb.set_trace()
        # 如果上一轮有 code agent 结果，则加入
        if (
            hasattr(self.grounding_agent, "last_code_agent_result")
            and self.grounding_agent.last_code_agent_result is not None
        ):
            code_result = self.grounding_agent.last_code_agent_result
            generator_message += f"\nCODE AGENT 结果:\n"
            generator_message += f"任务/子任务指令: {code_result['task_instruction']}\n"
            generator_message += f"已完成步骤数: {code_result['steps_executed']}\n"
            generator_message += f"最大步骤数: {code_result['budget']}\n"
            generator_message += f"完成原因: {code_result['completion_reason']}\n"
            generator_message += f"总结: {code_result['summary']}\n"
            if code_result["execution_history"]:
                generator_message += f"执行历史:\n"
                for i, step in enumerate(code_result["execution_history"]):
                    action = step["action"]
                    # 对代码片段进行格式化
                    if "```python" in action:
                        code_start = action.find("```python") + 9
                        code_end = action.find("```", code_start)
                        if code_end != -1:
                            python_code = action[code_start:code_end].strip()
                            generator_message += f"步骤 {i+1}: \n```python\n{python_code}\n```\n"
                        else:
                            generator_message += f"步骤 {i+1}: \n{action}\n"
                    elif "```bash" in action:
                        code_start = action.find("```bash") + 7
                        code_end = action.find("```", code_start)
                        if code_end != -1:
                            bash_code = action[code_start:code_end].strip()
                            generator_message += f"步骤 {i+1}: \n```bash\n{bash_code}\n```\n"
                        else:
                            generator_message += f"步骤 {i+1}: \n{action}\n"
                    else:
                        generator_message += f"步骤 {i+1}: \n{action}\n"
            generator_message += "\n"

            # 日志记录 code agent 结果（执行历史截断显示）
            log_message = f"\nCODE AGENT 结果:\n"
            log_message += f"任务/子任务指令: {code_result['task_instruction']}\n"
            log_message += f"已完成步骤数: {code_result['steps_executed']}\n"
            log_message += f"最大步骤数: {code_result['budget']}\n"
            log_message += f"完成原因: {code_result['completion_reason']}\n"
            log_message += f"总结: {code_result['summary']}\n"
            if code_result["execution_history"]:
                log_message += f"执行历史 (截断):\n"
                total_steps = len(code_result["execution_history"])
                for i, step in enumerate(code_result["execution_history"]):
                    if i < 3 or i >= total_steps - 2:  # 前三步和最后两步
                        action = step["action"]
                        if "```python" in action:
                            code_start = action.find("```python") + 9
                            code_end = action.find("```", code_start)
                            if code_end != -1:
                                python_code = action[code_start:code_end].strip()
                                log_message += f"步骤 {i+1}: ```python\n{python_code}\n```\n"
                            else:
                                log_message += f"步骤 {i+1}: {action}\n"
                        elif "```bash" in action:
                            code_start = action.find("```bash") + 7
                            code_end = action.find("```", code_start)
                            if code_end != -1:
                                bash_code = action[code_start:code_end].strip()
                                log_message += f"步骤 {i+1}: ```bash\n{bash_code}\n```\n"
                            else:
                                log_message += f"步骤 {i+1}: {action}\n"
                        else:
                            log_message += f"步骤 {i+1}: {action}\n"
                    elif i == 3 and total_steps > 5:
                        log_message += f"... (截断 {total_steps - 5} 步) ...\n"

            logger.info(
                f"WORKER_CODE_AGENT_RESULT_SECTION - 第 {self.turn_count + 1} 步: Code agent 结果已加入 generator 消息:\n{log_message}"
            )

            # 重置 code agent 结果
            self.grounding_agent.last_code_agent_result = None
        pdb.set_trace()
        # 将 generator 消息加入到 agent 历史
        self.generator_agent.add_message(
            generator_message, image_content=obs["screenshot"], role="user"
        )

        # 生成计划和下一步动作
        format_checkers = [
            SINGLE_ACTION_FORMATTER,
            partial(CODE_VALID_FORMATTER, self.grounding_agent, obs),
        ]
        
        plan = call_llm_formatted(
            self.generator_agent,
            format_checkers,
            temperature=self.temperature,
            use_thinking=self.use_thinking,
        )
        self.worker_history.append(plan)
        self.generator_agent.add_message(plan, role="assistant")
        logger.info("PLAN:\n %s", plan)   

        # 从计划中提取下一步动作
        plan_code = parse_code_from_string(plan)
        try:
            assert plan_code, "计划代码不能为空"
            exec_code = create_pyautogui_code(self.grounding_agent, plan_code, obs)
        except Exception as e:
            logger.error(
                f"无法执行以下计划代码:\n{plan_code}\n错误: {e}"
            )
            exec_code = self.grounding_agent.wait(1.333)  # 如果代码无法执行，则跳过此轮

        executor_info = {
            "plan": plan,
            "plan_code": plan_code,
            "exec_code": exec_code,
            "reflection": reflection,
            "reflection_thoughts": reflection_thoughts,
            "code_agent_output": (
                self.grounding_agent.last_code_agent_result
                if hasattr(self.grounding_agent, "last_code_agent_result")
                and self.grounding_agent.last_code_agent_result is not None
                else None
            ),
        }
        pdb.set_trace()
        self.turn_count += 1
        self.screenshot_inputs.append(obs["screenshot"])
        self.flush_messages()
        if exec_code == "DONE":
            self.turn_count = 0
        return executor_info, [exec_code]
