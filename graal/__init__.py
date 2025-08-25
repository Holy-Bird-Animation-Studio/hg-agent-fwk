"""
GRAAL Agent Framework
A framework for building conversational agents in the GRAAL ecosystem
"""

__version__ = "1.1.0"
__author__ = "GRAAL Team"
__email__ = "contact@holygraal.io"

from .base import BaseAgent, AgentConfig
from .models import HealthResponse, ChatRequest, ChatResponse, AgentStatus
from .llm import LLMClient, LLMConfig, LLMProvider, BaseLLMAgent
from .framework_manager import FrameworkManager, FrameworkVersion, UpdateResult
from .migration_manager import MigrationManager, FrameworkMigration, MigrationStep

__all__ = [
    "BaseAgent",
    "AgentConfig", 
    "HealthResponse",
    "ChatRequest", 
    "ChatResponse",
    "AgentStatus",
    "LLMClient",
    "LLMConfig",
    "LLMProvider", 
    "BaseLLMAgent",
    "FrameworkManager",
    "FrameworkVersion",
    "UpdateResult",
    "MigrationManager",
    "FrameworkMigration", 
    "MigrationStep",
]