"""
Example: LLM-enabled GRAAL agent using the framework
Demonstrates how to create an agent with LLM capabilities
"""
from graal.llm import BaseLLMAgent, LLMConfig
from graal import AgentConfig


class ExampleLLMAgent(BaseLLMAgent):
    """Example LLM agent demonstrating framework LLM integration"""
    
    def get_system_prompt(self) -> str:
        """Customize the system prompt for this agent"""
        return f"""You are {self.config.name}, a friendly and helpful AI assistant.

Your specialization: {self.config.description}

Personality traits:
- Enthusiastic and positive
- Clear and concise in explanations  
- Ask clarifying questions when needed
- Provide practical, actionable advice

Always introduce yourself as {self.config.name} in your first response.
"""

    async def on_startup(self):
        """Custom startup logic"""
        await super().on_startup()
        self.logger.info(f"🧠 LLM Agent ready with {self.llm_config.provider.value} {self.llm_config.model_tier}")


if __name__ == "__main__":
    # Configuration
    config = AgentConfig(
        name="Smart Example Agent",
        slug="smart-example-agent", 
        description="An intelligent example agent powered by LLM",
        port=5501,
        version="1.1.0"
    )
    
    # LLM Configuration (from environment or explicit)
    llm_config = LLMConfig.from_env()
    
    # Create and run LLM agent
    agent = ExampleLLMAgent(config, llm_config)
    print(f"Starting {config.name} on port {config.port}")
    print(f"Using {llm_config.provider.value} with {llm_config.get_model_name()}")
    agent.run()