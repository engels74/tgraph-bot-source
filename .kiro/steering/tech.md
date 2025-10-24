---
inclusion: always
---

# Technology Stack

## Language & Runtime

- Python 3.14 (minimum required version)
- Type hints required throughout codebase
- PEP 695 type aliases used (`type StreamRecordList = list[StreamRecord]`)

## Build System

- **Package Manager**: `uv` (modern Python package manager)
- **Build Backend**: `uv_build` (specified in pyproject.toml)
- **Dependency Management**: uv.lock file for reproducible builds

## Core Dependencies

- **Discord**: nextcord (Discord API library)
- **Configuration**: pydantic (validation), ruamel.yaml (YAML parsing)
- **HTTP**: httpx (async HTTP client), aiohttp (async web server)
- **Visualization**: matplotlib, seaborn
- **Web UI**: aiohttp-jinja2 (templating)

## Development Tools

- **Linting/Formatting**: ruff (configured for line-length 88, Python 3.14)
- **Type Checking**: basedpyright (strict mode, failOnWarnings enabled)
- **Testing**: pytest, pytest-asyncio, pytest-cov

## Common Commands

```bash
# Install dependencies
uv sync

# Run the bot
uv run tgraph-bot

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=tgraph_bot

# Lint and format
uv run ruff check .
uv run ruff format .

# Type checking
uv run basedpyright
```

## Configuration

- Configuration via YAML file (config.yaml)
- Environment variable overrides supported for sensitive values
- Pydantic models for runtime validation
- Hot reload capability without restart
