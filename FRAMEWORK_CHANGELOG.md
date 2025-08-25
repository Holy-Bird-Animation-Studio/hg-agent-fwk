# GRAAL Agent Framework - Changelog

All notable changes to the GRAAL Agent Framework will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Automatic code migration system for breaking changes
- New endpoints `/fwk/migration-info` and `/fwk/changelog` 
- Migration rollback capability on failed updates

## [1.2.0] - 2025-08-25

### Added
- **Framework Self-Update System** 🚀
  - `/fwk/version` - Get current framework version
  - `/fwk/available` - List available framework versions
  - `/fwk/update` - Update framework to target version with automatic testing
  - `/fwk/clone-test` - Create test clone for safe migration testing
- **FrameworkManager** class for version management
- **GitHub API integration** for version discovery
- **Automatic rollback** on failed updates
- **Test execution** after framework updates
- **Agent cloning** for safe testing

### Enhanced
- **BaseAgent** now includes framework management capabilities
- **Development mode** support with local framework mounting
- **Agent scaffold generator** supports dev/prod modes

### Migration Notes
- ✅ **No breaking changes** - existing agents work without modification
- ✅ **New endpoints** automatically available on all agents using v1.2.0+
- ✅ **Backward compatible** with all v1.1.0 agents

---

## [1.1.0] - 2025-08-20

### Added
- **LLM Integration** with Anthropic and OpenAI support
- `BaseLLMAgent` for AI-powered conversational agents
- `LLMClient` with provider abstraction
- Enhanced status reporting with memory usage

### Changed
- **BREAKING**: `BaseAgent.process()` renamed to `BaseAgent.process_message()`
- **BREAKING**: Added required `user_id` and `conversation_id` parameters to `process_message()`

### Migration Guide v1.0.0 → v1.1.0
```python
# Before (v1.0.0)
async def process(self, message: str, context: Dict[str, Any]) -> str:
    return "response"

# After (v1.1.0)
async def process_message(self, message: str, context: Dict[str, Any], 
                         user_id: Optional[str] = None, 
                         conversation_id: Optional[str] = None) -> str:
    return "response"
```

### Auto-Migration Available
- ✅ Automatic code transformation available via `/fwk/update`
- ✅ Method rename: `process()` → `process_message()`  
- ✅ Parameter addition: `user_id`, `conversation_id` with defaults

---

## [1.0.0] - 2025-08-15

### Added
- **BaseAgent** class with FastAPI integration
- **Standard endpoints**: `/`, `/healthz`, `/status`, `/chat`
- **AgentConfig** for agent configuration
- **Health monitoring** with status reporting
- **Docker support** with health checks
- **CORS middleware** configuration
- **Request/response logging**
- **Performance monitoring** with timing

### Core Features
- FastAPI application factory
- Async/await support throughout
- Pydantic models for type safety
- Comprehensive error handling
- Lifecycle management (startup/shutdown hooks)

---

## Framework Development Guidelines

### Version Types
- **Major (X.y.z)**: Breaking changes requiring agent code modifications
- **Minor (x.Y.z)**: New features, backward compatible  
- **Patch (x.y.Z)**: Bug fixes, fully backward compatible

### Breaking Changes Policy
- All breaking changes MUST include automatic migration scripts
- Migration scripts MUST be tested on existing agents
- Rollback capability MUST be available for all migrations
- Breaking changes MUST be documented with before/after examples

### Release Process
1. **Development**: Work in `framework/` directory
2. **Testing**: Test with agents in development mode  
3. **Migration Scripts**: Create migration for breaking changes
4. **Documentation**: Update changelog with migration guides
5. **Tagging**: Create Git tag with semantic version
6. **Validation**: Test auto-migration on sample agents

### Changelog Format
Each release must include:
- **Added**: New features
- **Changed**: Modifications to existing features  
- **Deprecated**: Features marked for removal
- **Removed**: Features removed in this version
- **Fixed**: Bug fixes
- **Security**: Security improvements
- **BREAKING**: Breaking changes with migration guide
- **Migration Notes**: Auto-migration availability and steps