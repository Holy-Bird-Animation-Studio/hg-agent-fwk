# GRAAL Agent Framework

🤖 A powerful framework for building conversational agents in the GRAAL ecosystem.

## Features

- **FastAPI Integration**: Built on FastAPI with automatic OpenAPI documentation
- **Multi-LLM Support**: Unified interface for Anthropic Claude and OpenAI GPT models  
- **Standardized APIs**: Common endpoints and response formats across all agents
- **Health Monitoring**: Built-in health checks and performance metrics
- **Type Safety**: Full Pydantic model validation and type hints
- **Hot Reload**: Development-friendly with automatic reloading
- **Extensible**: Easy to extend with custom capabilities and middleware

## Quick Start

### Basic Agent (Template)

```python
from graal import BaseAgent, AgentConfig

class MyAgent(BaseAgent):
    async def process_message(self, message: str, context: dict, **kwargs) -> str:
        return f"Hello! You said: {message}"

# Configuration
config = AgentConfig(
    name="My Assistant",
    slug="my-assistant", 
    description="A helpful AI assistant",
    port=5500
)

# Run agent
agent = MyAgent(config)
agent.run()
```

### LLM-Enabled Agent

```python
from graal import BaseLLMAgent, AgentConfig
from graal.llm import LLMConfig

class SmartAgent(BaseLLMAgent):
    def get_system_prompt(self) -> str:
        return "You are a helpful AI assistant specialized in customer service."

# Configuration  
config = AgentConfig(
    name="Smart Assistant",
    slug="smart-assistant",
    description="AI assistant with LLM capabilities", 
    port=5501
)

llm_config = LLMConfig.from_env()  # Uses environment variables

# Run LLM agent
agent = SmartAgent(config, llm_config)
agent.run()
```

## Installation

```bash
# Basic framework
pip install graal-agent-framework

# With LLM support
pip install graal-agent-framework[llm]

# Development tools
pip install graal-agent-framework[dev]
```

## Environment Variables

```bash
# LLM Configuration
LLM_PROVIDER=anthropic          # or "openai"
LLM_MODEL_TIER=fast            # fast, smart, premium
LLM_MAX_TOKENS=1000
LLM_TEMPERATURE=0.7

# API Keys
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here

# Agent Settings
LOG_LEVEL=INFO
CORS_ORIGINS=*
```

## Standard API Endpoints

All GRAAL agents provide these endpoints:

- `GET /` - Basic agent info
- `GET /healthz` - Health check for monitoring
- `POST /chat` - Main conversation endpoint
- `GET /status` - Detailed agent status and capabilities

## Framework Versions

- **v1.0.0**: Base template with FastAPI, health checks, basic chat
- **v1.1.0**: + LLM integration (Anthropic/OpenAI), system prompts
- **v2.0.0**: + Advanced capabilities (memory, RAG, tools) *(planned)*

## Architecture

```
graal/
├── __init__.py          # Main exports
├── base.py             # BaseAgent class
├── models.py           # Pydantic models  
└── llm/                # LLM integration
    ├── __init__.py
    ├── client.py       # LLMClient abstraction
    └── base.py         # BaseLLMAgent
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

- GitHub Issues: [Report bugs and feature requests](https://github.com/your-org/graal-agent-framework/issues)
- Documentation: [Framework docs](https://github.com/your-org/graal-agent-framework#readme)
- GRAAL Ecosystem: [Main project](https://github.com/your-org/graal-v4)

---

Built with ❤️ for the GRAAL conversational AI ecosystem.