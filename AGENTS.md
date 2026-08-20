# AGENTS.md

This file provides guidance to AI coding agents when working with code in this
repository.

## Commands

Run from the repository root.

| Task | Command |
| --- | --- |
| Install dev environment | `uv sync --dev` |
| Run the bot | `uv run tgraph-bot` (`--config-file`, `--data-folder`, `--log-folder`, `--version`) |
| All tests | `uv run pytest` |
| One test file | `uv run pytest tests/unit/config/test_schema.py` |
| One test case | `uv run pytest tests/unit/config/test_schema.py::TestTGraphBotConfig::test_valid_minimal_config` |
| Type check | `uvx basedpyright` |
| Lint / format | `uv run ruff check .` / `uv run ruff format .` |

- `pyproject.toml` forces `--cov=src/tgraph_bot` on every pytest run (writes `htmlcov/`). No `fail_under` is configured — coverage percentage is not a gate.
- `asyncio_mode = "auto"`; async tests need no marker. An autouse `setup_test_paths` fixture in `tests/conftest.py` redirects `PathConfig` to temp dirs.
- `.github/workflows/` holds only the two i18n workflows. CI never runs pytest, basedpyright, or ruff, so running them locally is the only gate before pushing.
- Target Python 3.12 (`requires-python`, `.python-version`, ruff `target-version`, basedpyright `pythonVersion`). README's "Python 3.13+" is stale — do not use 3.13-only syntax.

## Layout

- `src/tgraph_bot/` — production code: `bot/` (cogs, scheduling), `config/`, `graphs/`, `utils/{cli,core,discord,i18n,time}`.
- `tests/` mirrors `src/`. `tests/utils/` holds shared builders (`test_helpers.py`, `graph_helpers.py`, `cog_helpers.py`, `async_helpers.py`) — use these instead of ad-hoc mocks; it is not a test package.
- `scripts/i18n/`, `scripts/weblate/` — standalone CLIs; each does `sys.path.insert` of the repo root and imports as `src.tgraph_bot.…`.
- `locale/` is generated output; `/data/` and `docs/` are gitignored.

## Imports

- Production code uses relative imports only (`from ..utils.core.error_handler import …`). Absolute `src.tgraph_bot.…` breaks the installed console script — `src/` currently contains zero such imports.
- Tests use `from src.tgraph_bot.… import …` (71 modules). Six modules use bare `tgraph_bot.…`; follow the majority.
- `ExtensionManager` loads cogs as `tgraph_bot.bot.commands.<module>` (`bot/extensions.py`) — the installed package name, not the `src.`-prefixed one.

## Adding a graph type

The type-name string is duplicated across four files (steps 3–6). Missing any one of them fails silently rather than raising.

1. Add `graphs/graph_modules/implementations/tautulli/<name>_graph.py` subclassing `BaseGraph`.
2. Export it from `implementations/tautulli/__init__.py` (import + `__all__`).
3. Register it in `GraphTypeRegistry._ensure_initialized` (`graph_modules/core/graph_type_registry.py`) via `_register_graph_type(type_name=…, graph_class=…, default_enabled=…, description=…)`. This registry is the only name→class map; `GraphFactory` resolves everything through it.
4. Add a `bool` field named exactly `type_name` to `EnabledTypesConfig` (`config/schema.py`) — `ConfigAccessor.is_graph_type_enabled` builds the path `graphs.features.enabled_types.{type_name}`.
5. Add the same key to the `schema_graph_types` set in `graph_modules/config/config_accessor.py`. A type absent from that set defaults to *disabled* whenever the user's config omits the key.
6. Add `"ClassName": "type_name"` to `class_to_graph_type` in `BaseGraph._get_graph_type_key` (`core/base_graph.py`). It falls back to `ClassName.lower()`, so a missing entry silently resolves per-graph settings under a `graphs.per_graph.<wrong-key>` path that never exists. It currently lists only the six original types.
7. Add the key to `config.yml.sample` under `graphs.features.enabled_types`, and add tests using `run_standard_graph_tests` / `run_standard_graph_error_tests` from `tests/utils/graph_helpers.py`.

## Adding a slash command

Drop a module in `src/tgraph_bot/bot/commands/` with a module-level `async def setup(bot)`; `pkgutil` discovery loads every non-underscore module there, so there is no registry to update. Subclass `BaseCommandCog` (`utils/discord/base_command_cog.py`) for config access, cooldowns, and ephemeral helpers — plain `commands.Cog` is used only by `AboutCog`, which needs none of them. Note that `bot/commands/test_scheduler.py` is a command cog, not a test module.

## Adding a config option

Add the field to the right nested model in `config/schema.py` **and** mirror it in `config.yml.sample`. `TGraphBotConfig` sets `extra="forbid"`, so a key present in a user's YAML but missing from the schema aborts startup.

## User-facing text and i18n

Wrap strings with `translate(...)`; the AST extractor recognizes only `_`, `translate`, `t`, `ngettext`, `nt` (`TRANSLATION_FUNCTIONS` in `utils/i18n/i18n_utils.py`). Then:

```bash
uv run python scripts/i18n/dev-helpers.py full    # extract + update + compile
uv run python scripts/weblate/validate_config.py  # validate .weblate against locale/
```

Never hand-edit `locale/messages.pot` or `locale/*/LC_MESSAGES/messages.po`. The `i18n-sync` workflow regenerates and auto-commits them on every push to `main` touching `src/**/*.py` or `scripts/**/*.py`, so manual edits are overwritten — change the source string instead.

## Other invariants

- `main.py` calls `matplotlib.use("Agg")` after its stdlib imports and before every other import, because graphs render off the event loop. Preserve that ordering when editing the import block.
- Read application paths from `get_path_config()` (`utils/cli/paths.py`, a singleton populated once at startup), never a literal `Path("data/…")`.
- Inside `graphs/`, read config through the `ConfigAccessor` dot-path helpers (`get_nested_value`, `get_bool_value`) rather than walking `config.graphs.appearance.…` attributes — the accessor supports defaults and raises a typed `ConfigurationError`.
- Put per-graph behaviour under `graphs.per_graph.<type>.*`; `graphs.features.media_type_separation` and `graphs.features.stacked_bar_charts` are marked deprecated in the schema.
- Two sample-config templates exist and have diverged: root `config.yml.sample` is canonical (what users copy), while the string embedded in `ConfigManager._generate_sample_content()` still lists only the six original graph types. Edit the embedded copy only when deliberately fixing `create_sample_config`.
- `tests/integration/test_project_structure.py` asserts that specific modules and command files exist, so moving or renaming them breaks that suite.

## Reference

- `.agents/rules/python-rules.md` — typing and basedpyright policy (zero errors *and* warnings across source and tests; targeted `# pyright: ignore[code]` instead of global config ignores). Read before any Python change.
- `config.yml.sample` — annotated reference for the full nested config tree. Read when adding, renaming, or documenting a config key.
- `.weblate` — Weblate component and locale layout. Read when changing locale paths or adding a language.
- `README.md` — user-facing feature list and slash-command inventory.
