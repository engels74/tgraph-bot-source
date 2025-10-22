# Technology Stack

## Language & Runtime
- Python 3.14 (modern type system, structured concurrency)
- Target version: `py314`
- Async-first architecture with asyncio

## Core Dependencies
- **nextcord**: Discord bot framework (slash commands, API interactions)
- **pydantic**: Configuration validation and data modeling at API boundaries
- **httpx**: Async HTTP client for Tautulli API
- **matplotlib**: Graph generation and visualization
- **seaborn**: Enhanced graph aesthetics and color palettes
- **aiohttp**: Async web server for configuration UI
- **aiohttp-jinja2**: Template rendering for web UI
- **ruamel.yaml**: Format-preserving YAML configuration editing
- **python-dotenv**: Environment variable management

## Build System & Tooling
- **Package Manager**: uv (unified package management, 10-100x faster than pip)
- **Build Backend**: uv_build (version constraint: `>=0.9.5,<0.10.0`)
- **Linter/Formatter**: ruff (target-version: py314, line-length: 88)
- **Type Checker**: basedpyright (pythonVersion: 3.14, typeCheckingMode: recommended, failOnWarnings: true)
- **Testing**: pytest, pytest-asyncio, pytest-cov

## Project Structure
- Source layout: `src/tgraph_bot/`
- Entry point: `tgraph_bot:main` (console script)
- Configuration: `pyproject.toml` (PEP 621 compliant)
- Config file: `config.yaml` (YAML with comprehensive comments)

## Common Commands

### Development Setup
```bash
# Install dependencies
uv sync

# Run the bot
uv run tgraph-bot

# Run with environment variables
DISCORD_TOKEN=xxx TAUTULLI_API_KEY=yyy uv run tgraph-bot
```

### Code Quality
```bash
# Format code
ruff format .

# Lint and auto-fix
ruff check . --fix

# Type checking
basedpyright

# Run all quality checks
ruff format . && ruff check . --fix && basedpyright
```

### Testing
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=tgraph_bot

# Run specific test file
uv run pytest tests/test_config.py

# Run with verbose output
uv run pytest -v
```

### Package Management
```bash
# Add runtime dependency
uv add <package>

# Add dev dependency
uv add --dev <package>

# Update dependencies
uv lock --upgrade
```

## Code Style Guidelines (per .claude/rules/python-pro.md)

### Type System
- Use PEP 695 syntax: `class[T]`, `def[T]`, `type Alias = ...`
- Use `TypeIs[T]` for type narrowing (not TypeGuard)
- Use built-in generics: `list[str]`, `dict[str, int]`, `str | int | None`
- Use `ReadOnly[type]` for immutable TypedDict fields
- Define small composable Protocols (1-3 methods)

### Data Modeling
- **dataclasses** with `slots=True` for internal DTOs (40% memory savings)
- **Pydantic** models only at API boundaries (config, web UI)
- Use `frozen=True` for immutable structures

### Async Patterns
- Use `asyncio.TaskGroup` for structured concurrency (not gather/create_task)
- Use `@asynccontextmanager` for async resource management
- Use `asyncio.timeout()` for timeouts (not wait_for)
- Use `except*` for ExceptionGroup handling

### Function Design
- Make boolean flags and options keyword-only (after `*`)
- Use explicit type ignore comments: `# pyright: ignore[rule]`
- Include type hints for all parameters and returns

### Error Handling
- Use specific exception types (never bare except)
- Preserve all exception details in concurrent operations
- Include operation context in error messages
