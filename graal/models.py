"""
Common Pydantic models for GRAAL agents
Standardized request/response models used across all agents
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    """Status enum for agents"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthResponse(BaseModel):
    """Standard health check response for all GRAAL agents"""
    status: AgentStatus = AgentStatus.HEALTHY
    agent_name: str
    agent_slug: str
    version: str = "1.0.0"
    framework_version: str = Field(default="1.0.0", description="GRAAL framework version")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    uptime_seconds: Optional[float] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ChatRequest(BaseModel):
    """Standard chat request for all GRAAL agents"""
    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    context: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Optional context for the conversation"
    )
    user_id: Optional[str] = Field(None, description="Optional user identifier")
    conversation_id: Optional[str] = Field(None, description="Optional conversation identifier")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Hello, how can you help me?",
                "context": {"source": "web", "locale": "en"},
                "user_id": "user123",
                "conversation_id": "conv456"
            }
        }


class ChatResponse(BaseModel):
    """Standard chat response from all GRAAL agents"""
    response: str = Field(..., description="Agent response message")
    agent_name: str = Field(..., description="Name of the responding agent")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Response context and metadata"
    )
    processing_time_ms: Optional[float] = Field(None, description="Processing time in milliseconds")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AgentCapability(BaseModel):
    """Represents a capability of an agent"""
    name: str = Field(..., description="Capability name")
    version: str = Field(..., description="Capability version")
    description: Optional[str] = Field(None, description="Capability description")
    enabled: bool = Field(True, description="Whether capability is enabled")


class AgentStatusResponse(BaseModel):
    """Detailed status response for agent introspection"""
    agent_name: str
    agent_slug: str
    status: AgentStatus
    port: int
    capabilities: List[AgentCapability] = Field(default_factory=list)
    version: str = "1.0.0"
    framework_version: str = "1.0.0"
    description: str
    uptime_seconds: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    last_request: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }