# Project Structure

## Directory Layout

```
tgraph-bot/
├── .kiro/
│   ├── specs/tgraph-bot/     # Spec files (requirements, design, tasks)
│   └── steering/             # AI assistant steering rules
├── .claude/
│   └── rules/                # Python development guidelines
├── assets/
│   └── svg/                  # SVG graphics (logo)
├── src/tgraph_bot/           # Main source (src layout)
│   ├── __init__.py           # Package entry with main()
│   ├── __main__.py           # Application entry point
│   ├── config/               # Configuration system
│   │   ├── models.py         # Pydantic config models
│   │   └── loader.py         # YAML loading/saving
│   ├── api/                  # External API clients
│   │   └── tautulli.py       # Tautulli API client
│   ├── commands/             # Discord command handlers
│   │   └── graph_commands.py # Slash command implementations
│   ├── graphs/               # Graph generation engine
│   │   ├── generators/       # Individual graph type implementations
│   │   ├── styling.py        # Seaborn styling and themes
│   │   └── renderer.py       # Graph orchestration
│   ├── scheduler/            # Automated task scheduling
│   │   └── task_scheduler.py
│   ├── rate_limiting/        # Command rate limiting
│   │   └── rate_limiter.py
│   ├── web/                  # Web UI server
│   │   ├── server.py         # aiohttp server
│   │   ├── templates/        # Jinja2 HTML templates
│   │   └── static/           # CSS/JS assets
│   ├── localization/         # Multi-language support
│   │   └── locales/          # JSON language files (en, da)
│   └── utils/                # Shared utilities
│       ├── errors.py         # Exception hierarchy
│       └── logging.py        # Structured logging
├── tests/                    # Test suite (mirrors src/)
│   ├── test_config.py
│   ├── test_tautulli.py
│   ├── test_graphs.py
│   └── ...
├── templates/                # Web UI templates (if not in src/)
├── static/                   # Web UI static files (if not in src/)
├── locales/                  # Localization files (if not in src/)
├── config.yaml               # Default configuration file
├── pyproject.toml            # Project metadata (PEP 621)
├── .python-version           # Python 3.14
├── README.md
└── LICENSE                   # AGPLv3
```

## Architecture Layers

### Presentation Layer
- `commands/` - Discord slash command handlers
- `web/` - Web UI HTTP handlers and templates
- Response formatting, ephemeral messages

### Application Layer
- `scheduler/` - Automated task orchestration
- `rate_limiting/` - Command cooldown management
- Graph generation coordination
- Configuration validation

### Domain Layer
- `graphs/` - Graph generation logic and styling
- Data transformation and aggregation
- Privacy/anonymization logic
- `localization/` - Multi-language string management

### Infrastructure Layer
- `api/` - Tautulli API client (httpx)
- `config/` - YAML persistence (ruamel.yaml)
- Discord API (nextcord)
- File system operations

## Key Design Patterns

### Configuration
- Pydantic models at API boundaries (validation)
- dataclasses with slots for internal data (performance)
- YAML as single source of truth
- Environment variable overrides for secrets

### Async Concurrency
- TaskGroup for structured concurrency
- Context variables for task-local state
- asynccontextmanager for resource lifecycle
- Exception groups for multi-error handling

### Graph Generation
- Protocol-based graph generators
- Factory pattern for graph type creation
- Seaborn integration for professional aesthetics
- Configurable styling system (palettes, themes, dimensions)

### Error Handling
- Custom exception hierarchy (TGraphBotError base)
- Specific exceptions: ConfigurationError, TautulliAPIError, GraphGenerationError, RateLimitError
- Comprehensive logging with sensitive value masking

## Naming Conventions
- Modules: `snake_case.py`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Type parameters: `T`, `K`, `V` or `PascalCase` (PEP 695)
- Private: `_leading_underscore`

## Module Organization Principles
- One primary class per file (exceptions for small related classes)
- Group related functionality in subdirectories
- Keep `__init__.py` minimal (re-exports only)
- Protocol definitions in separate files or with implementations
- Test files mirror source structure: `test_<module>.py`
