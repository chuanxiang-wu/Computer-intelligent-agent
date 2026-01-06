from typing import Dict, Optional
from core.llm import LLMAgent


class BaseModule:
    def __init__(self, engine_params: Dict, platform: str):
        self.engine_params = engine_params
        self.platform = platform

    def _create_agent(
        self, system_prompt: str = None, engine_params: Optional[Dict] = None
    ) -> LLMAgent:
        """Create a new LLMAgent instance"""
        agent = LLMAgent(engine_params or self.engine_params)
        if system_prompt:
            agent.add_system_prompt(system_prompt)
        return agent
