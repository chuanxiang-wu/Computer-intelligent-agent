import logging
import platform
from typing import Dict, List, Tuple
import pdb
from utils.grounding import ACI
from agent.worker import Worker


logger = logging.getLogger("ComputerAgent.agent.agent")
logger.setLevel(logging.INFO)  # 可以改为 DEBUG 查看详细信息

class Agent:
    """Agent that uses no hierarchy for less inference time"""

    def __init__(
        self,
        worker_engine_params: Dict,
        grounding_agent: ACI,
        platform: str = platform.system().lower(),
        max_trajectory_length: int = 8,
        enable_reflection: bool = True,
    ):
        """Initialize a minimalist AgentS2 without hierarchy

        Args:
            worker_engine_params: Configuration parameters for the worker agent.
            grounding_agent: Instance of ACI class for UI interaction
            platform: Operating system platform (darwin, linux, windows)
            max_trajectory_length: Maximum number of image turns to keep
            enable_reflection: Creates a reflection agent to assist the worker agent
        """

        self.worker_engine_params = worker_engine_params
        self.grounding_agent = grounding_agent
        self.platform = platform
        self.max_trajectory_length = max_trajectory_length
        self.enable_reflection = enable_reflection

        self.reset()

    def reset(self) -> None:
        """Reset agent state and initialize components"""
        self.executor = Worker(
            worker_engine_params=self.worker_engine_params,
            grounding_agent=self.grounding_agent,
            platform=self.platform,
            max_trajectory_length=self.max_trajectory_length,
            enable_reflection=self.enable_reflection,
        )

    def predict(self, instruction: str, observation: Dict) -> Tuple[Dict, List[str]]:
        # Initialize the three info dictionaries
        executor_info, actions = self.executor.generate_next_action(
            instruction=instruction, obs=observation
        )
        # pdb.set_trace()
        # concatenate the three info dictionaries
        info = {**{k: v for d in [executor_info or {}] for k, v in d.items()}}

        # logger.info(f"Agent predict info: {info}")
        # logger.info(f"Agent predict actions: {actions}")
        
        return info, actions