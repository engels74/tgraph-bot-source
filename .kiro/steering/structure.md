---
inclusion: always
---

# Project Structure

## Directory Layout

```
src/tgraph_bot/          # Main application package
├── api/                 # External API clients (Tautulli)
├── commands/            # Discord slash commands
├── config/              # Configuration loading and models
├── graphs/              # Graph generation system
│   └── generators/      # Individual graph type implementations
├── localization/        # i18n support
│   └── locales/         # Translation files (JSON)
├── rate_limiting/       # Command cooldown management
├── scheduler/           # Automated task scheduling
├── utils/               # Shared utilities (logging, errors, retention)
└── web/                 # Web UI for configuration
    ├── static/          # CSS and JavaScript
    └── templates/       # HTML templates

tests/                   # Test suite (pytest)
assets/                  # Static assets (SVG logo)
```

## Architecture Patterns

### Protocol-Based Design

- Use `typing.Protocol` for structural subtyping (duck typing)
- Example: `GraphGenerator` protocol defines interface for all graph generators
- Protocols should be small (1-3 methods) and composable

### Configuration Management

- Pydantic models in `config/models.py` for validation
- Nested configuration structure (services, automation, graphs, etc.)
- Field validation with constraints (ranges, patterns, min/max)
- ConfigLoader handles YAML parsing and validation

### Graph Generation

- Factory pattern in `graphs/factory.py` for graph type selection
- Individual generators in `graphs/generators/` implement GraphGenerator protocol
- Shared styling in `graphs/styling.py`
- Data transformation in `graphs/data.py`
- Rendering utilities in `graphs/renderer.py`

### Async/Await

- Bot uses async/await throughout (nextcord, httpx, aiohttp)
- Event handlers are async methods
- Scheduler runs tasks asynchronously

### Error Handling

- Custom exceptions in `utils/errors.py`
- Structured logging with context (extra fields)
- Operation logging with start/complete tracking

## Code Conventions

### Type Hints

- All functions must have type hints for parameters and return values
- Use PEP 695 type aliases for complex types
- Use `| None` instead of `Optional[T]`
- Use `list[T]`, `dict[K, V]` instead of `List[T]`, `Dict[K, V]`

### Docstrings

- All modules, classes, and public functions require docstrings
- Format: Google-style docstrings
- Include Requirements references when applicable

### Imports

- Absolute imports from package root
- Group imports: stdlib, third-party, local
- Use `from typing import Protocol` for protocols

### Naming

- Classes: PascalCase
- Functions/methods: snake_case
- Constants: UPPER_SNAKE_CASE
- Private members: prefix with underscore

### Method Overrides

- Use `@override` decorator when overriding parent methods
- Explicitly import from `typing` module

## Testing

- Tests mirror source structure in `tests/` directory
- Test files named `test_*.py`
- Use pytest fixtures for common setup
- Async tests use `pytest-asyncio`
- Coverage tracking enabled by default
