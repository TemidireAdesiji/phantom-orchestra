# Changelog

All notable changes to PhantomOrchestra are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.0] - 2024-12-01

### Added
- Core event system with `SignalChannel` pub/sub architecture
- `SignalDepot` for persistent signal storage
- `VoiceProvider` with multi-model LLM support via LiteLLM
- `VoiceRegistry` for managing multiple LLM configurations
- `CodeActPerformer` implementing the CodeAct agent paradigm
- `Director` orchestration engine for managing performer sessions
- `LocalStage` for executing directives on the host filesystem
- `ContainerStage` for isolated Docker-based execution
- `LocalRepository` and `MemoryRepository` storage backends
- FastAPI REST API with session management endpoints
- WebSocket relay for real-time signal streaming
- Hierarchical Pydantic configuration (`OrchestraConfig`)
- CLI with `phantom run` and `phantom serve` commands
- Docker Compose setup for single-command deployment
- Comprehensive CI/CD with GitHub Actions
- 80%+ test coverage for core modules

### Security
- Path traversal protection in `LocalStage` and `LocalRepository`
- Secret masking in `SignalChannel` broadcasts
- Non-root Docker container execution
- Input validation on all public API endpoints
