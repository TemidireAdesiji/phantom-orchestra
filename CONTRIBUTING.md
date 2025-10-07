# Contributing to PhantomOrchestra

Thank you for your interest in contributing! This guide covers
everything you need to get started.

## Table of Contents

- [Development Environment](#development-environment)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Adding a Custom Performer](#adding-a-custom-performer)
- [Adding a Custom Stage](#adding-a-custom-stage)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)

## Development Environment

### Prerequisites

- Python 3.11 or 3.12
- [Poetry](https://python-poetry.org/docs/#installation)
- Docker (for container stage tests)
- Git

### Setup

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR-USERNAME/phantom-orchestra.git
cd phantom-orchestra

# Install all dependencies including dev tools
poetry install --with dev

# Install pre-commit hooks
pre-commit install

# Copy and edit the configuration
cp config.template.toml config.toml
# Set PHANTOM_API_KEY in your environment or config.toml

# Verify your setup
make test
```

## Code Standards

All contributions must meet these standards (enforced by CI):

- **Python 3.11+** with complete type hints on all public APIs
- **Line length ≤ 79 characters** (enforced by ruff)
- **No TODOs** in final code — resolve before submitting
- **No debug print statements** — use `structlog` for all output
- **No hardcoded credentials** — all secrets via environment variables
- **Docstrings** on all public classes and methods
- **Ruff-compliant** — run `make lint` before pushing

```bash
# Auto-fix common issues
make format

# Check for remaining issues
make lint

# Type checking
make type-check
```

## Testing

### Running Tests

```bash
# All unit tests with coverage
make test-cov

# Fast run (no coverage)
make test

# Integration tests (requires network/Docker)
poetry run pytest tests/integration -v

# Single module
poetry run pytest tests/unit/signal/ -v
```

### Writing Tests

- Test file: `tests/unit/<module>/test_<file>.py`
- Name pattern: `test_<what>_<when>_<expected_outcome>`
- Use `pytest-asyncio` for async tests (`asyncio_mode = "auto"`)
- Mock external services — never make real LLM API calls in tests
- Target: 80%+ coverage for new modules

```python
# Good test name
async def test_local_stage_execute_command_returns_exit_code():
    ...

# Good async test
async def test_signal_channel_broadcasts_to_all_subscribers():
    channel = SignalChannel(...)
    received = []
    channel.subscribe(ChannelSubscriber.TEST, received.append, "t")
    channel.broadcast(signal, SignalSource.USER)
    await asyncio.sleep(0.05)
    assert len(received) == 1
```

## Adding a Custom Performer

1. Create `phantom/performer/my_performer.py`:

```python
from phantom.performer.base import Performer
from phantom.performer.scene import Scene
from phantom.signal.directive.base import Directive
from phantom.signal.directive.control import CompleteDirective


class MyPerformer(Performer):
    """Short description of what this performer does."""

    def decide(self, scene: Scene) -> Directive:
        """Return next directive based on current scene."""
        # Your LLM or logic here
        return CompleteDirective()

    def get_available_tools(self) -> list[dict]:
        """Return OpenAI-format tool definitions."""
        return []

    def build_system_prompt(self) -> str:
        return "You are a specialized assistant for..."


Performer.register("MyPerformer", MyPerformer)
```

2. Import in `phantom/performer/__init__.py` for auto-registration.
3. Add tests in `tests/unit/performer/test_my_performer.py`.
4. Document in `docs/architecture.md`.

## Adding a Custom Stage

1. Subclass `phantom.stage.base.Stage`:

```python
from phantom.stage.base import Stage, StageStatus
from phantom.signal.report.terminal import CommandOutputReport


class MyStage(Stage):
    """Executes directives on a custom runtime."""

    async def initialize(self) -> None:
        # Provision resources
        self._status = StageStatus.READY

    async def teardown(self) -> None:
        # Release resources
        self._status = StageStatus.CLOSED

    async def execute_command(
        self, command: str, **kwargs
    ) -> CommandOutputReport:
        # Execute and return result
        ...
```

2. Register in `phantom/stage/factory.py`.
3. Add `StageConfig` fields if needed in `phantom/score/stage_config.py`.
4. Add tests in `tests/unit/stage/`.

## Pull Request Process

### Branch Naming

```
feature/short-description
fix/what-was-broken
refactor/module-being-changed
docs/what-is-being-documented
test/what-is-being-tested
```

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) spec:

```
feat(performer): add BrowserActPerformer with Playwright support
fix(stage): handle Unicode in Docker container file writes
refactor(channel): replace threading.Lock with asyncio.Lock
test(vault): add concurrent write race condition tests
docs(api): add WebSocket message format examples
chore(deps): update litellm to 1.45.0
```

### Checklist Before Submitting

- [ ] All tests pass: `make test`
- [ ] No lint errors: `make lint`
- [ ] Coverage maintained or improved
- [ ] New public APIs have docstrings
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] PR description explains the change and motivation

## Issue Reporting

Please include:

- PhantomOrchestra version (`phantom --version`)
- Python version (`python --version`)
- Operating system and version
- Minimal reproduction case (fewest steps to trigger the bug)
- Expected behavior
- Actual behavior with full error output

Security vulnerabilities: please email maintainers directly rather
than opening a public issue.
