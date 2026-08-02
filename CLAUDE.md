# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

Run everything from the repository root.

| Task | Command |
| --- | --- |
| Install dev environment | `uv sync --dev` |
| Run the bot | `uv run tgraph-bot` (accepts `--config-file`, `--data-folder`, `--log-folder`, `--version`) |
| Full test suite | `uv run pytest` |
| Single test file | `uv run pytest tests/unit/config/test_schema.py` |
| Single test case | `uv run pytest tests/unit/config/test_schema.py::TestTGraphBotConfig::test_valid_minimal_config` |
| Filtered tests | `uv run pytest -k "palette and not integration"` |
| Type check | `uvx basedpyright` |
| Lint / format | `uv run ruff check .` / `uv run ruff format .` |

`pytest` addopts in `pyproject.toml` always enable `--cov=src/tgraph_bot` with terminal and HTML reports, so every run writes `htmlcov/`. No coverage threshold is configured — do not treat a coverage percentage as a gate.

i18n workflows (each script's `--help` documents further flags):

```bash
uv run python scripts/i18n/dev-helpers.py full     # extract + update + compile
uv run python scripts/i18n/extract_strings.py --check --verbose
uv run python scripts/i18n/update_translations.py --verbose
uv run python scripts/i18n/compile_translations.py --check-only
uv run python scripts/weblate/validate_config.py   # validates .weblate against locale/
```

GitHub Actions only runs the two i18n workflows in `.github/workflows/`. Nothing in CI runs pytest, basedpyright, or ruff — local validation is the only gate before pushing.

## Architecture Overview

**Startup chain.** `pyproject.toml` maps `tgraph-bot` to `tgraph_bot:main` → `src/tgraph_bot/__init__.py` wraps the async `main()` in `src/tgraph_bot/main.py`. That function parses CLI args, populates the `PathConfig` singleton, configures logging, loads and validates the YAML config, then starts `TGraphBot` (a `discord.ext.commands.Bot`).

**Extension loading is dynamic.** `TGraphBot.setup_hook` calls `load_extensions`, and `ExtensionManager.discover_extensions` (`src/tgraph_bot/bot/extensions.py`) walks `src/tgraph_bot/bot/commands/` with `pkgutil`. Any non-underscore module there is loaded automatically, so new cogs need no registry entry — only a module-level `async def setup(bot)`.

**Graph pipeline.** `GraphManager` (`src/tgraph_bot/graphs/graph_manager.py`, an async context manager) fetches Tautulli data via `DataFetcher`, asks `GraphFactory` which types are enabled, and renders each one. `GraphFactory` resolves classes through `GraphTypeRegistry` (`graphs/graph_modules/core/graph_type_registry.py`) — the single source of truth mapping type names to `BaseGraph` subclasses. Rendered PNGs land in date-partitioned directories under the data folder (`data/graphs`), then `main.py` posts them to the configured Discord channel.

**Configuration.** `src/tgraph_bot/config/schema.py` defines one nested Pydantic tree (`TGraphBotConfig` → `services`/`automation`/`data_collection`/`system`/`graphs`/`rate_limiting`) with `extra="forbid"` and `validate_assignment=True`. `ConfigManager` loads, validates, saves atomically, and notifies change callbacks so `/config edit` can update settings at runtime.

**Paths.** `PathConfig` in `src/tgraph_bot/utils/cli/paths.py` is a singleton set once at startup. Read config/data/log locations from `get_path_config()`; do not hardcode `data/` paths.

**Matplotlib threading.** `main.py` calls `matplotlib.use("Agg")` before any other matplotlib import because graphs render off the event loop. Keep that ordering intact when editing `main.py`.

## Project Boundaries

- `src/tgraph_bot/` — production code. Layers: `bot/` (Discord cogs, scheduling), `config/`, `graphs/`, `utils/` (`cli`, `core`, `discord`, `i18n`, `time`).
- `tests/` — mirrors the source layout; `tests/utils/` holds shared helpers (not test cases).
- `scripts/i18n/`, `scripts/weblate/` — standalone CLIs. They insert the repo root on `sys.path` and import via `src.tgraph_bot.…`.
- `locale/` — generated. `messages.pot` and `*.po` are produced by the i18n scripts and auto-committed by the `i18n-sync` workflow on `main`; `.mo` files are compiled output. Do not hand-edit these; change the source strings instead.
- `data/` and `docs/` are gitignored — nothing there is part of the repo.

## Common Change Workflows

### Add a graph type

1. Create `src/tgraph_bot/graphs/graph_modules/implementations/tautulli/<name>_graph.py` subclassing `BaseGraph` (see `top_10_users_graph.py`).
2. Export it from `implementations/tautulli/__init__.py` (import + `__all__`).
3. Register it in `GraphTypeRegistry._ensure_initialized`:

```python
self._register_graph_type(
    type_name="play_count_by_source_resolution",
    graph_class=PlayCountBySourceResolutionGraph,
    default_enabled=True,
    description="Play count by source resolution (original file resolution)",
)
```

4. Add a `bool` field named **exactly** `type_name` to `EnabledTypesConfig` in `config/schema.py` — `ConfigAccessor.is_graph_type_enabled` builds the lookup path as `graphs.features.enabled_types.{type_name}`.
5. Add the same key to the `schema_graph_types` set in `graphs/graph_modules/config/config_accessor.py`, otherwise the type defaults to disabled when absent from a user's config.
6. Add the key to `config.yml.sample` under `graphs.features.enabled_types`.
7. Add tests under `tests/unit/graphs/graph_modules/`; `tests/utils/graph_helpers.py` provides `run_standard_graph_tests` and `run_standard_graph_error_tests`.

The re-exports in `implementations/__init__.py` and `graph_modules/__init__.py` currently list only the six original graph types; the newer stream-type graphs were added without touching them, so they are optional.

### Add a slash command

Create `src/tgraph_bot/bot/commands/<name>.py` with a cog and a module-level `async def setup(bot)` that calls `bot.add_cog(...)`. Discovery is automatic. Wrap the command body in try/except and route failures through `ErrorContext` + `handle_command_error` (`utils/core/error_handler.py`), as `uptime.py` does.

### Add a configuration option

Add the field to the right nested model in `config/schema.py`, then mirror it in `config.yml.sample`. Because the model sets `extra="forbid"`, any key present in a user's YAML but missing from the schema fails validation at startup.

### Change user-facing text

Wrap strings with `i18n.translate(...)` (or `_`, `t`, `ngettext`, `nt` — the set the AST extractor recognizes, see `TRANSLATION_FUNCTIONS` in `utils/i18n/i18n_utils.py`), then run `uv run python scripts/i18n/dev-helpers.py full`.

## Implementation Decisions

| Situation | Preferred approach | Avoid |
| --- | --- | --- |
| Reading config inside `graphs/` | `ConfigAccessor` dot-path helpers (`get_nested_value`, `get_bool_value`) | Walking `config.graphs.appearance…` attributes directly; the accessor raises a typed `ConfigurationError` and supports defaults |
| Per-graph media-type separation / stacked bars | `graphs.per_graph.<type>.*` | `graphs.features.media_type_separation` and `stacked_bar_charts`, both marked deprecated in the schema |
| New command cog | Subclass `BaseCommandCog` (`utils/discord/base_command_cog.py`) for config access, cooldowns, and ephemeral helpers | Plain `commands.Cog` — only `AboutCog` uses it, and it needs none of those facilities |
| Imports in tests | `from src.tgraph_bot.… import …` (71 test modules, plus `conftest.py`) | `from tgraph_bot.…` — 5 modules use it, but the majority convention and the scripts' `sys.path` setup assume the `src.` prefix |
| Imports in production code | Relative (`from ..utils.core.error_handler import …`) | Absolute `src.tgraph_bot.…`, which breaks the installed console script |
| Application paths | `get_path_config()` | Literal `Path("data/…")` |

## Testing and Validation

- `asyncio_mode = "auto"`, so async tests need no marker.
- An autouse `setup_test_paths` fixture in `tests/conftest.py` redirects `PathConfig` to temp directories; config fixtures (`base_config`, `minimal_config`, `comprehensive_config`, `edge_case_config`, `maximum_config`) are defined there.
- Use `tests/utils/` builders (`create_test_config`, `create_mock_interaction`, `create_graph_factory_with_config`, `matplotlib_cleanup`) rather than new ad-hoc mocks.
- Structural expectations are themselves tested — `tests/integration/test_project_structure.py` asserts that specific modules and command files exist, so renaming or moving them breaks that suite.
- Validation sequence before committing: `uv run pytest`, then `uvx basedpyright`. `.augment/rules/python-rules.md` requires **zero** basedpyright errors and warnings across source *and* tests.

## Critical Gotchas

- **Graph type names are duplicated in four places.** `GraphTypeRegistry`, `EnabledTypesConfig`, the `schema_graph_types` set in `config_accessor.py`, and the `class_to_graph_type` map in `BaseGraph._get_graph_type_key`. The last one silently falls back to `ClassName.lower()`, so a missing entry makes per-graph settings look up a key that does not exist instead of raising. Update all four when adding or renaming a type.
- **Two config templates exist and have already diverged.** The root `config.yml.sample` is what users copy (referenced by `README.md` and by `main.py`'s startup error). `ConfigManager._generate_sample_content()` embeds a second template that is missing the six stream-type graph keys. Treat `config.yml.sample` as canonical; only touch the embedded string when deliberately fixing `create_sample_config`.
- **Suppress type errors per-line.** Use `# pyright: ignore[specific-error]`; do not add rules to `[tool.basedpyright]` in `pyproject.toml` or use bare `# type: ignore`.
- **Never commit hand-edited `locale/` output.** The `i18n-sync` workflow regenerates and commits `messages.pot` and `.po` files on pushes to `main`, so manual edits will be overwritten.

## Additional Documentation

- `.augment/rules/python-rules.md` — Read before any Python change; defines the typing and basedpyright rules for this repository.
- `config.yml.sample` — Read when adding, renaming, or documenting a configuration key; it is the annotated reference for the full nested schema.
- `scripts/i18n/dev-helpers.py` — Read the module docstring when running any translation workflow; it lists every subcommand.
- `.weblate` — Read when changing locale layout or component paths; `scripts/weblate/validate_config.py` validates it against `locale/`.
- `README.md` — Read for the user-facing feature set and slash-command list.
