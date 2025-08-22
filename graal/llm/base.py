"""
Base LLM-enabled agent class
Extends BaseAgent with LLM capabilities
"""
from typing import Dict, Any, Optional
from ..base import BaseAgent, AgentConfig
from ..models import AgentCapability
from .client import LLMClient, LLMConfig


class BaseLLMAgent(BaseAgent):
    """
    Base class for LLM-enabled GRAAL agents
    
    Provides:
    - LLM client integration
    - System prompt management
    - Automatic LLM capability registration
    """
    
    def __init__(self, config: AgentConfig, llm_config: Optional[LLMConfig] = None):
        super().__init__(config)
        
        # Initialize LLM client
        self.llm_config = llm_config or LLMConfig.from_env()
        self.llm_client = LLMClient(self.llm_config)
        
        # Register LLM capabilities
        self._register_llm_capabilities()
    
    def _register_llm_capabilities(self):
        """Register LLM-specific capabilities"""
        model_info = self.llm_client.get_model_info()
        
        self.add_capability(AgentCapability(
            name="llm_conversation",
            version="1.1.0",
            description=f"LLM-powered conversations using {model_info['provider']} {model_info['model']}",
            enabled=True
        ))
        
        self.add_capability(AgentCapability(
            name="context_awareness", 
            version="1.1.0",
            description="Contextual understanding and response generation",
            enabled=True
        ))
    
    def get_system_prompt(self) -> str:
        """
        Get system prompt for this agent
        Override this method to customize the agent's behavior
        """
        return f"""You are {self.config.name}, a specialized AI assistant.

Description: {self.config.description}

Your role is to help users with tasks related to your specialization. Be helpful, accurate, and professional in your responses. Always stay in character as {self.config.name}.

Guidelines:
- Provide clear, actionable responses
- Ask clarifying questions when needed
- Acknowledge limitations honestly
- Maintain a friendly but professional tone
"""
    
    async def process_message(
        self, 
        message: str, 
        context: Dict[str, Any],
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> str:
        """
        Process message using LLM
        Can be overridden for custom logic
        """
        try:
            # Build enhanced context for LLM
            enhanced_context = {
                **context,
                "agent_name": self.config.name,
                "agent_description": self.config.description,
                "user_id": user_id,
                "conversation_id": conversation_id
            }
            
            # Get system prompt
            system_prompt = self.get_system_prompt()
            
            # Call LLM
            response = await self.llm_client.chat(
                message=message,
                system_prompt=system_prompt,
                context=enhanced_context
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"LLM processing error: {e}")
            
            # Fallback response
            return f"I apologize, but I'm experiencing technical difficulties. As {self.config.name}, I'm temporarily unable to process your request. Please try again later."
    
    async def on_startup(self):
        """Extended startup for LLM agents"""
        await super().on_startup()
        
        # Test LLM connection
        try:
            test_response = await self.llm_client.chat(
                "Hello", 
                "Respond with just 'OK' to confirm connection."
            )
            self.logger.info(f"LLM connection test successful: {test_response[:20]}...")
        except Exception as e:
            self.logger.warning(f"LLM connection test failed: {e}")
    
    def get_llm_info(self) -> Dict[str, Any]:
        """Get current LLM configuration info"""
        return self.llm_client.get_model_info()