"""
Example: Basic GRAAL agent using the framework
Demonstrates how to create a simple agent with the framework
"""
from typing import Dict, Any, Optional
from graal import BaseAgent, AgentConfig


class ExampleAgent(BaseAgent):
    """Example agent demonstrating basic framework usage"""
    
    async def process_message(
        self, 
        message: str, 
        context: Dict[str, Any],
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> str:
        """Process user message and return response"""
        
        # Simple echo functionality with some processing
        response_parts = [
            f"Hello! I'm {self.config.name}.",
            f"You said: '{message}'",
            f"Message length: {len(message)} characters"
        ]
        
        # Add context info if available
        if context:
            response_parts.append(f"Context keys: {list(context.keys())}")
        
        if user_id:
            response_parts.append(f"User ID: {user_id}")
            
        return " | ".join(response_parts)


if __name__ == "__main__":
    # Configuration
    config = AgentConfig(
        name="Example Agent",
        slug="example-agent",
        description="A simple example agent built with GRAAL framework",
        port=5500,
        version="1.0.0"
    )
    
    # Create and run agent
    agent = ExampleAgent(config)
    print(f"Starting {config.name} on port {config.port}")
    agent.run()