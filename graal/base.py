"""
Base Agent class and configuration for GRAAL agents
Provides common functionality and structure for all conversational agents
"""
import asyncio
import logging
import time
import os
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from abc import ABC, abstractmethod

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .models import (
    HealthResponse, 
    ChatRequest, 
    ChatResponse, 
    AgentStatusResponse,
    AgentStatus,
    AgentCapability
)
from .framework_manager import FrameworkManager, FrameworkVersion, UpdateResult


class AgentConfig(BaseModel):
    """Configuration for a GRAAL agent"""
    name: str = Field(..., description="Human-readable agent name")
    slug: str = Field(..., description="URL-safe agent identifier")
    description: str = Field(..., description="Agent description")
    port: int = Field(..., ge=1000, le=65535, description="Port to run the agent on")
    version: str = Field(default="1.0.0", description="Agent version")
    
    # Framework settings
    framework_version: str = Field(default="1.0.0", description="GRAAL framework version")
    log_level: str = Field(default="INFO", description="Logging level")
    cors_origins: List[str] = Field(default=["*"], description="CORS allowed origins")
    
    # Performance settings
    request_timeout_seconds: float = Field(default=30.0, description="Request timeout")
    max_message_length: int = Field(default=10000, description="Maximum message length")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Marketing Assistant",
                "slug": "marketing-assistant",
                "description": "AI assistant specialized in marketing and campaign analysis",
                "port": 5512,
                "version": "1.0.0"
            }
        }


class BaseAgent(ABC):
    """
    Base class for all GRAAL conversational agents
    
    Provides:
    - Standard FastAPI application setup
    - Common endpoints (health, status, chat)
    - Request/response logging
    - Error handling
    - Performance monitoring
    """
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.start_time = time.time()
        self.last_request_time: Optional[datetime] = None
        self.request_count = 0
        
        # Setup logging
        logging.basicConfig(level=getattr(logging, config.log_level.upper()))
        self.logger = logging.getLogger(f"graal.agent.{config.slug}")
        
        # Create FastAPI app
        self.app = self._create_app()
        
        # Register capabilities
        self.capabilities: List[AgentCapability] = []
        self._register_base_capabilities()
        
        # Framework manager for self-update capabilities
        self.framework_manager = FrameworkManager(config)
    
    def _create_app(self) -> FastAPI:
        """Create and configure FastAPI application"""
        
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Application lifespan management"""
            self.logger.info(f"🚀 Starting {self.config.name} agent on port {self.config.port}")
            await self.on_startup()
            yield
            await self.on_shutdown()
            self.logger.info(f"🛑 Shutting down {self.config.name} agent")
        
        app = FastAPI(
            title=f"{self.config.name} Agent",
            description=self.config.description,
            version=self.config.version,
            lifespan=lifespan,
        )
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Register routes
        self._register_routes(app)
        
        return app
    
    def _register_routes(self, app: FastAPI):
        """Register standard routes"""
        
        @app.get("/", response_model=HealthResponse)
        async def root():
            """Root endpoint with basic agent info"""
            return await self._get_health_response()
        
        @app.get("/healthz", response_model=HealthResponse)
        async def health_check():
            """Health check endpoint for monitoring"""
            return await self._get_health_response()
        
        @app.post("/chat", response_model=ChatResponse)
        async def chat(request: ChatRequest):
            """Main chat endpoint"""
            start_time = time.time()
            self.last_request_time = datetime.utcnow()
            self.request_count += 1
            
            try:
                # Process the message
                response_text = await self.process_message(
                    message=request.message,
                    context=request.context,
                    user_id=request.user_id,
                    conversation_id=request.conversation_id
                )
                
                processing_time = (time.time() - start_time) * 1000
                
                return ChatResponse(
                    response=response_text,
                    agent_name=self.config.name,
                    context={
                        "original_message": request.message,
                        "processed_at": datetime.utcnow().isoformat(),
                        "request_id": f"{self.config.slug}-{int(time.time())}"
                    },
                    processing_time_ms=processing_time
                )
                
            except Exception as e:
                self.logger.error(f"Error processing message: {e}")
                raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
        
        @app.get("/status", response_model=AgentStatusResponse)
        async def get_status():
            """Detailed status endpoint"""
            return await self._get_detailed_status()
        
        # Framework management endpoints
        @app.get("/fwk/version")
        async def get_framework_version():
            """Get current framework version"""
            return {
                "current_version": self.framework_manager.get_current_version(),
                "framework_version": self.config.framework_version,
                "agent_version": self.config.version
            }
        
        @app.get("/fwk/available", response_model=List[FrameworkVersion])
        async def get_available_versions():
            """Get available framework versions"""
            return await self.framework_manager.get_available_versions()
        
        @app.post("/fwk/update", response_model=UpdateResult)
        async def update_framework(target_version: str, run_tests: bool = True):
            """Update framework to target version"""
            return await self.framework_manager.update_framework(target_version, run_tests)
        
        @app.post("/fwk/clone-test")
        async def clone_for_testing(clone_name: Optional[str] = None):
            """Create a test clone of this agent"""
            clone_path = await self.framework_manager.create_test_clone(clone_name)
            return {
                "success": True,
                "clone_path": str(clone_path),
                "clone_name": clone_path.name
            }
        
        @app.get("/fwk/migration-info")
        async def get_migration_info(target_version: str):
            """Get migration information for target version without applying it"""
            current_version = self.framework_manager.get_current_version()
            return self.framework_manager.migration_manager.get_migration_info(current_version, target_version.lstrip('v'))
        
        @app.get("/fwk/changelog")
        async def get_framework_changelog():
            """Get framework changelog with breaking changes info"""
            current_version = self.framework_manager.get_current_version()
            available_versions = await self.framework_manager.get_available_versions()
            
            changelog_info = []
            for version in available_versions:
                migration_info = self.framework_manager.migration_manager.get_migration_info(
                    current_version, version.version
                )
                if migration_info["migration_available"]:
                    changelog_info.append({
                        "version": version.version,
                        "tag": version.tag,
                        "has_breaking_changes": migration_info["has_code_changes"],
                        "breaking_changes": migration_info.get("breaking_changes", []),
                        "changelog": migration_info.get("changelog", ""),
                        "migration_steps": len(migration_info.get("migration_steps", []))
                    })
            
            return {
                "current_version": current_version,
                "available_updates": changelog_info
            }
    
    def _register_base_capabilities(self):
        """Register base framework capabilities"""
        self.capabilities.extend([
            AgentCapability(
                name="chat",
                version="1.0.0",
                description="Basic conversational capabilities"
            ),
            AgentCapability(
                name="health_check", 
                version="1.0.0",
                description="Health monitoring and status reporting"
            ),
            AgentCapability(
                name="status_reporting",
                version="1.0.0", 
                description="Detailed agent introspection"
            ),
            AgentCapability(
                name="framework_management",
                version="1.1.0",
                description="Self-update and framework version management"
            ),
            AgentCapability(
                name="test_cloning",
                version="1.1.0", 
                description="Create test clones for safe framework updates"
            )
        ])
    
    async def _get_health_response(self) -> HealthResponse:
        """Generate health response"""
        return HealthResponse(
            status=await self.get_health_status(),
            agent_name=self.config.name,
            agent_slug=self.config.slug,
            version=self.config.version,
            framework_version=self.config.framework_version,
            uptime_seconds=time.time() - self.start_time
        )
    
    async def _get_detailed_status(self) -> AgentStatusResponse:
        """Generate detailed status response"""
        memory_mb = None
        if HAS_PSUTIL:
            try:
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
            except:
                pass
        
        return AgentStatusResponse(
            agent_name=self.config.name,
            agent_slug=self.config.slug,
            status=await self.get_health_status(),
            port=self.config.port,
            capabilities=self.capabilities,
            version=self.config.version,
            framework_version=self.config.framework_version,
            description=self.config.description,
            uptime_seconds=time.time() - self.start_time,
            memory_usage_mb=memory_mb,
            last_request=self.last_request_time
        )
    
    # Abstract methods that agents must implement
    
    @abstractmethod
    async def process_message(
        self, 
        message: str, 
        context: Dict[str, Any],
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> str:
        """
        Process a chat message and return response
        This is the main method agents must implement
        """
        pass
    
    # Optional hooks for lifecycle management
    
    async def on_startup(self):
        """Called when agent starts up"""
        pass
    
    async def on_shutdown(self):
        """Called when agent shuts down"""
        pass
    
    async def get_health_status(self) -> AgentStatus:
        """
        Determine agent health status
        Override for custom health checks
        """
        return AgentStatus.HEALTHY
    
    def add_capability(self, capability: AgentCapability):
        """Add a capability to this agent"""
        self.capabilities.append(capability)
    
    def run(self, **uvicorn_kwargs):
        """Run the agent with uvicorn"""
        import uvicorn
        
        default_kwargs = {
            "host": "0.0.0.0",
            "port": self.config.port,
            "app": self.app
        }
        default_kwargs.update(uvicorn_kwargs)
        
        uvicorn.run(**default_kwargs)