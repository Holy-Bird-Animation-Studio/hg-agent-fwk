"""
LLM Client abstraction for GRAAL agents
Supports multiple providers with unified interface
"""
import os
import asyncio
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
    """Supported LLM providers"""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


class LLMConfig(BaseModel):
    """Configuration for LLM client"""
    provider: LLMProvider = Field(default=LLMProvider.ANTHROPIC)
    model_tier: str = Field(default="fast", description="Model tier: fast, smart, premium")
    max_tokens: int = Field(default=1000, ge=1, le=8000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    timeout_seconds: float = Field(default=30.0, ge=1.0)
    
    # Provider-specific settings
    anthropic_api_key: Optional[str] = Field(default=None)
    openai_api_key: Optional[str] = Field(default=None)
    
    # Model mappings
    models: Dict[str, Dict[str, str]] = Field(default_factory=lambda: {
        "anthropic": {
            "fast": "claude-3-haiku-20240307",
            "smart": "claude-3-sonnet-20240229",
            "premium": "claude-3-opus-20240229"
        },
        "openai": {
            "fast": "gpt-3.5-turbo",
            "smart": "gpt-4-turbo-preview", 
            "premium": "gpt-4"
        }
    })
    
    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Create config from environment variables"""
        return cls(
            provider=LLMProvider(os.getenv("LLM_PROVIDER", "anthropic")),
            model_tier=os.getenv("LLM_MODEL_TIER", "fast"),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1000")),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
    
    def get_model_name(self) -> str:
        """Get the actual model name for current config"""
        return self.models.get(self.provider.value, {}).get(
            self.model_tier, 
            "claude-3-haiku-20240307"
        )
    
    def get_api_key(self) -> str:
        """Get API key for current provider"""
        if self.provider == LLMProvider.ANTHROPIC:
            return self.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY", "")
        elif self.provider == LLMProvider.OPENAI:
            return self.openai_api_key or os.getenv("OPENAI_API_KEY", "")
        return ""


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
    
    @abstractmethod
    async def chat(
        self, 
        message: str, 
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Send chat message and get response"""
        pass


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = None
    
    def _get_client(self):
        """Lazy initialization of Anthropic client"""
        if self.client is None:
            try:
                import anthropic
                self.client = anthropic.AsyncAnthropic(
                    api_key=self.config.get_api_key()
                )
            except ImportError:
                raise ImportError("anthropic package not installed. Install with: pip install anthropic")
        return self.client
    
    async def chat(
        self, 
        message: str, 
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Send message to Claude and get response"""
        client = self._get_client()
        
        messages = [{"role": "user", "content": message}]
        
        try:
            response = await client.messages.create(
                model=self.config.get_model_name(),
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                system=system_prompt or "You are a helpful AI assistant.",
                messages=messages
            )
            
            return response.content[0].text
            
        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider"""
    
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.client = None
    
    def _get_client(self):
        """Lazy initialization of OpenAI client"""
        if self.client is None:
            try:
                import openai
                self.client = openai.AsyncOpenAI(
                    api_key=self.config.get_api_key()
                )
            except ImportError:
                raise ImportError("openai package not installed. Install with: pip install openai")
        return self.client
    
    async def chat(
        self, 
        message: str, 
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Send message to GPT and get response"""
        client = self._get_client()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})
        
        try:
            response = await client.chat.completions.create(
                model=self.config.get_model_name(),
                messages=messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")


class LLMClient:
    """
    Main LLM client that delegates to specific providers
    Provides unified interface regardless of provider
    """
    
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig.from_env()
        self.provider = self._create_provider()
    
    def _create_provider(self) -> BaseLLMProvider:
        """Create appropriate provider based on config"""
        if self.config.provider == LLMProvider.ANTHROPIC:
            return AnthropicProvider(self.config)
        elif self.config.provider == LLMProvider.OPENAI:
            return OpenAIProvider(self.config)
        else:
            raise ValueError(f"Unsupported provider: {self.config.provider}")
    
    @classmethod
    def from_env(cls, provider: Optional[str] = None) -> "LLMClient":
        """Create client from environment variables"""
        config = LLMConfig.from_env()
        if provider:
            config.provider = LLMProvider(provider)
        return cls(config)
    
    async def chat(
        self, 
        message: str, 
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Send chat message and get response
        
        Args:
            message: User message
            system_prompt: Optional system prompt for context
            context: Optional context dictionary
            
        Returns:
            LLM response text
        """
        try:
            response = await asyncio.wait_for(
                self.provider.chat(message, system_prompt, context),
                timeout=self.config.timeout_seconds
            )
            return response
            
        except asyncio.TimeoutError:
            raise Exception(f"LLM request timeout after {self.config.timeout_seconds}s")
        except Exception as e:
            raise Exception(f"LLM error: {str(e)}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about current model configuration"""
        return {
            "provider": self.config.provider.value,
            "model": self.config.get_model_name(),
            "tier": self.config.model_tier,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature
        }