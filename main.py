import pyautogui
import io
from utils.local_env import LocalEnv
from utils.grounding import OSWorldACI
from agent.agent import Agent
import logging
import os
import pdb


def setup_logging():
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, "agent.log")

    # 🔑 统一的父 logger
    root_logger = logging.getLogger("ComputerAgent")
    root_logger.setLevel(logging.INFO)

    # 文件 handler
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)

    # 防止重复添加 handler
    if not root_logger.handlers:
        root_logger.addHandler(file_handler)




def init_computer_agent():
    current_platform = "windows"

    engine_params = {
    "engine_type": "openai",
    "model": "Qwen/Qwen3-VL-30B-A3B-Thinking",
    "base_url": 'https://api-inference.modelscope.cn/v1',           # Optional
    "api_key": "ms-f3d132da-0b7d-4ea5-a713-c5052b097761",        # Optional
    "temperature": 0 # Optional
    }

    # Load the grounding engine from a custom endpoint
    ground_provider = engine_params["engine_type"]  # Use the same provider as above
    ground_url = engine_params["base_url"]  # Use the same base URL as above
    ground_model = engine_params["model"]  # Use the same model as above
    ground_api_key = engine_params["api_key"]  # Use the same API key as above

    # Set grounding dimensions based on your model's output coordinate resolution
    # qwen3-vl-30b-a3b-thinking 输出坐标分辨率为 1000x1000
    grounding_width = 1000
    grounding_height = 1000

    engine_params_for_grounding = {
    "engine_type": ground_provider,
    "model": ground_model,
    "base_url": ground_url,
    "api_key": ground_api_key,  # Optional
    "grounding_width": grounding_width,
    "grounding_height": grounding_height,
    }

    # Optional: Enable local coding environment
    enable_local_env = False  # Set to True to enable local code execution
    local_env = LocalEnv() if enable_local_env else None

    screen_width = 1920
    screen_height = 1080

    grounding_agent = OSWorldACI(
        env=local_env,  # Pass local_env for code execution capability
        platform=current_platform,
        engine_params_for_generation=engine_params,
        engine_params_for_grounding=engine_params_for_grounding,
        width=screen_width,  # Optional: screen width
        height=screen_height  # Optional: screen height
    )

    agent = Agent(
        engine_params,
        grounding_agent,
        platform=current_platform,
        max_trajectory_length=8,  # Optional: maximum image turns to keep
        enable_reflection=True     # Optional: enable reflection agent
    )

    return grounding_agent, agent


if __name__ == "__main__":

    pdb.set_trace = lambda *args, **kwargs: None  # 注释掉所有 pdb.set_trace 调用

    setup_logging()
    grounding_agent, agent = init_computer_agent()
    print("Computer Agent initialized successfully.")

    # instruction = "打开浏览器中的bilibili网站，然后搜索走路摇ZLY相关的视频并播放一个。"

    label = 0
    while True:
        if label == 0:
            # Get user instruction
            instruction = input("请输入命令（输入exit or q退出）：")
            if instruction.lower() == "exit" or instruction.lower() == "q":
                break
            else:
                label = 1

        # Get screenshot.
        screenshot = pyautogui.screenshot()
        buffered = io.BytesIO() 
        screenshot.save(buffered, format="PNG")
        screenshot_bytes = buffered.getvalue()

        obs = {
        "screenshot": screenshot_bytes,
        }
        
        pdb.set_trace()
        info, action = agent.predict(instruction=instruction, observation=obs)

        # 打印代理决策信息和执行代码
        print("="*50 + " Agent Info " + "="*50)
        print(info)
        print("\n" + "="*50 + " Agent Action " + "="*50)
        print(action[0])

        # 执行生成的代码（完整完成任务）
        print("\n" + "="*50 + " 开始执行单步任务 " + "="*50)
        # 任务完成返回的是DONE
        if action[0] != "DONE":
            exec(action[0])
            print("单步任务执行完成！\n\n")
        else:
            label = 0
            print("任务执行完成！\n\n")
            

        