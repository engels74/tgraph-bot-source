---
type: "agent_requested"
description: "Python 3.14 coding guidelines"
---
# Python 3.14 Core: The Astral-Stack Coding Reference (uv · Ruff · basedpyright `recommended`)

This is the authoritative reference for writing Python on the modern Astral-managed stack: **CPython 3.14** (release date 7 October 2025, shepherded by release manager Hugo van Kemenade, with security support through October 2030), **uv** for environment and dependency management, **Ruff** for linting and formatting, and **basedpyright** in `recommended` mode for type checking. This stack optimizes for one thing above all: *code that is provably correct before it runs*. uv gives you a reproducible, universal lockfile and sub-second syncs; Ruff replaces an entire generation of tools (Flake8, isort, Black, pyupgrade, pydocstyle, autoflake, and much of Bandit) with one Rust binary; basedpyright's `recommended` mode makes untyped, `Any`-leaking, or unreachable code a hard CI failure. Optimize for: full static typing with zero implicit `Any`, PEP 695 generics, deferred annotations, structured concurrency, and immutable data by default.

The biggest ways an agent writes wrong-but-plausible code here come from importing habits from older Python or adjacent ecosystems: reaching for `from __future__ import annotations` (unnecessary in 3.14), `typing.List`/`Optional`/`Union` instead of `list`/`X | None`, `os.path` instead of `pathlib`, `pytz` instead of `zoneinfo`, `requirements.txt`+`pip` instead of `uv`, `# type: ignore` instead of `# pyright: ignore[rule]`, module-level `TypeVar` instead of `def f[T]()`, and `pip install`/`poetry`/`pyenv` commands inside a uv project. Don't. This document shows the one current, idiomatic way.

## Stack snapshot & versions

- **Research date:** 22 August 2026
- **Research basis:** current official docs, release notes, specifications, changelogs, and primary repositories.

| Component | Version target | Notes |
|---|---|---|
| CPython | 3.14.x (3.14.0 = 7 Oct 2025) | Free-threading officially supported (PEP 779); JIT still experimental |
| uv | 0.12.x | `uv_build` is the default build backend |
| Ruff | 0.16.x | 413 rules enabled by default as of 0.16.0 (23 Jul 2026) |
| basedpyright | 1.39.x | `recommended` is the default mode |
| pytest | 9.x | pytest-asyncio 1.x (requires pytest ≥ 8.4) |
| pydantic | 2.11+ | Rust core; use for validation at boundaries |

**Critical insight:** In Python 3.14, `python -VV` and `sys.version` report `free-threading build` for the `t` builds, and the standard build is unchanged. Target the standard GIL build unless you have measured a CPU-bound parallel workload.

## Project layout & pyproject.toml

Use a **src layout**. It prevents accidental imports of the un-built package and makes the `py.typed` marker meaningful.

```
myproject/
├── pyproject.toml
├── uv.lock                 # committed
├── .python-version         # committed, e.g. "3.14"
├── README.md
├── src/
│   └── myproject/
│       ├── __init__.py
│       ├── py.typed        # empty marker: ships your types to consumers
│       ├── core.py
│       └── cli.py
└── tests/
    ├── __init__.py
    └── test_core.py
```

`__init__.py` discipline: keep them near-empty. Use them to define the public API surface with explicit re-exports (`from myproject.core import Engine as Engine` — the redundant alias silences `reportUnusedImport` and marks intentional re-export). Do not run import-time side effects. The `py.typed` marker is a zero-byte file; without it, downstream basedpyright will not read your inline types.

One complete, copy-ready `pyproject.toml` combining every tool:

```toml
[project]
name = "myproject"
version = "0.1.0"
description = "A well-typed service."
readme = "README.md"
requires-python = ">=3.14"
dependencies = [
    "httpx>=0.28",
    "pydantic>=2.11",
]

[project.scripts]
myproject = "myproject.cli:main"

[build-system]
requires = ["uv_build>=0.12,<0.13"]
build-backend = "uv_build"

[dependency-groups]
dev = [
    "basedpyright>=1.39",
    "pytest>=9",
    "pytest-asyncio>=1",
    "ruff>=0.16",
]

[tool.uv]
# Nothing required for a standard project; add [tool.uv.sources] for git/path deps.

[tool.ruff]
line-length = 88
target-version = "py314"
src = ["src", "tests"]

[tool.ruff.lint]
select = [
    "E", "W",    # pycodestyle
    "F",         # Pyflakes
    "I",         # isort
    "UP",        # pyupgrade
    "B",         # flake8-bugbear
    "SIM",       # flake8-simplify
    "C4",        # flake8-comprehensions
    "PTH",       # flake8-use-pathlib
    "DTZ",       # flake8-datetimez
    "RET",       # flake8-return
    "PIE",       # flake8-pie
    "TID",       # flake8-tidy-imports
    "TC",        # flake8-type-checking
    "ARG",       # flake8-unused-arguments
    "ANN",       # flake8-annotations
    "RUF",       # Ruff-specific
]
ignore = [
    "E501",      # line length handled by the formatter
    "ANN401",    # allow explicit Any where genuinely needed (basedpyright also guards this)
]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["ANN", "ARG", "S101"]  # tests may skip annotations and use assert

[tool.ruff.lint.isort]
known-first-party = ["myproject"]

[tool.ruff.lint.flake8-type-checking]
runtime-evaluated-base-classes = ["pydantic.BaseModel"]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.format]
quote-style = "double"
docstring-code-format = true

[tool.basedpyright]
pythonVersion = "3.14"
typeCheckingMode = "recommended"
reportUnusedCallResult = false
reportMissingTypeStubs = false

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-ra --strict-markers --strict-config"
```

## uv: environment and dependency management

uv is the only supported way to manage environments, dependencies, Python versions, and builds on this stack. It is written in Rust and, per Astral's documentation, runs 10–100× faster than pip for installs and resolves, producing a universal (cross-platform) `uv.lock`.

**Do NOT use, in a uv project:** `pip install`, `python -m venv`, `poetry`, `pipenv`, `pyenv`, `virtualenv`, `pip-tools`/`pip-compile`, or `conda`. uv subsumes all of them. Never hand-edit `.venv`; never commit a `requirements.txt` as the source of truth.

Core workflow:

```bash
uv init --package myproject      # scaffold a src-layout package project
uv add httpx pydantic            # add runtime deps; updates pyproject.toml + uv.lock + .venv
uv add --dev pytest ruff basedpyright   # add to the [dependency-groups] dev group
uv remove httpx                  # remove a dependency
uv sync                          # make .venv exactly match uv.lock (default: main + dev groups)
uv lock                          # re-resolve and update uv.lock
uv run pytest                    # run a command inside the managed env (auto-syncs first)
uv run ruff check .              # anything after `uv run` sees the locked deps
```

Python version management is uv's job, not pyenv's:

```bash
uv python install 3.14           # install the standard CPython 3.14 build
uv python install 3.14t          # install the free-threaded build (the "t" suffix)
uv python pin 3.14               # writes .python-version
```

**Lockfile semantics.** `uv.lock` is universal: it encodes resolutions for all platforms and Python versions permitted by `requires-python`. Commit it. In CI and Docker, use `--frozen` (never touch the lockfile, fail if it would change) or `--locked` (verify the lockfile is up to date, fail if stale):

```bash
uv sync --frozen --no-dev        # production install: exact locked versions, no dev group
```

**Dependency groups vs. extras (PEP 735).** Use `[dependency-groups]` for developer-only tooling (test, lint, type-check, docs) — these are never installed by consumers of your package. Use `[project.optional-dependencies]` (extras) for optional *features* your users can opt into.

| Need | Table | Installed by consumers? |
|---|---|---|
| Runtime requirement | `[project].dependencies` | Yes, always |
| Optional user feature | `[project.optional-dependencies]` | Only with `pip install pkg[extra]` |
| Dev/test/lint tooling | `[dependency-groups]` | Never |

**Build backend.** Default to `uv_build` (fast, first-party, zero-config for src layout). Choose `hatchling` only if you need its plugin ecosystem (dynamic versioning, custom build hooks). Both are declared in `[build-system]`.

**Workspaces** for multi-package monorepos:

```toml
[tool.uv.workspace]
members = ["packages/*"]

[tool.uv.sources]
mylib = { workspace = true }
internal-tool = { git = "https://github.com/acme/tool", tag = "v1.2.0" }
local-pkg = { path = "../local-pkg", editable = true }
```

**PEP 723 inline script metadata** for standalone scripts — no project, no manual venv:

```python
# /// script
# requires-python = ">=3.14"
# dependencies = ["httpx", "rich"]
# ///
import httpx
from rich import print

resp = httpx.get("https://example.org")
print(resp.status_code)
```

Run with `uv run script.py`; uv creates an ephemeral environment, installs the deps, runs it, and discards. Add deps with `uv add --script script.py rich`.

`uvx` (alias for `uv tool run`) runs published tools without installing them into your project; `uv tool install ruff` installs a tool globally. Build and publish with `uv build` and `uv publish`.

## Modern typing (write code that passes `recommended`)

### PEP 695 type parameters (3.12) — the only correct generic syntax

Never declare a module-level `TypeVar` or inherit `Generic[T]` in new code. Write the type parameter inline:

```python
from collections.abc import Iterable

def first[T](items: Iterable[T]) -> T | None:
    for item in items:
        return item
    return None

class Box[T]:
    def __init__(self, value: T) -> None:
        self._value = value

    def get(self) -> T:
        return self._value

# Lazy type alias (the `type` statement, PEP 695)
type Json = None | bool | int | float | str | list["Json"] | dict[str, "Json"]

# Bounds and constraints
def clamp[T: (int, float)](value: T, lo: T, hi: T) -> T:
    return max(lo, min(value, hi))

class Repository[T: "Entity"]:  # upper bound
    ...
```

PEP 696 type parameter defaults (3.13) let a parameter fall back to a default:

```python
class Response[T = dict[str, object]]:
    body: T
```

### Built-in generics and unions only

Use `list[int]`, `dict[str, int]`, `tuple[int, ...]`, `set[str]`, and `X | None` — never `typing.List`, `typing.Dict`, `typing.Optional`, or `typing.Union`. Ruff's `UP` rules auto-fix the legacy forms.

```python
def load(path: str) -> dict[str, int] | None: ...
```

### Deferred annotations (PEP 649/749, 3.14) — drop `from __future__ import annotations`

As of Python 3.14, all annotations are evaluated lazily by default. You **no longer need** `from __future__ import annotations`, and forward references no longer require string quotes in most positions. Introspect annotations with the new `annotationlib` module rather than reading `__annotations__` directly:

```python
from annotationlib import get_annotations, Format

def process(order: "Order") -> None: ...

get_annotations(process, format=Format.VALUE)      # real runtime objects
get_annotations(process, format=Format.FORWARDREF) # undefined names -> ForwardRef markers
get_annotations(process, format=Format.STRING)     # annotations as strings
```

**Critical gotcha:** Even with deferred annotations, libraries like Pydantic and SQLAlchemy evaluate annotations at runtime to build their schemas. This interacts with Ruff's `TC` (flake8-type-checking) rules, which try to move imports into `if TYPE_CHECKING:` blocks — see the Ruff section.

### `Self`, `override`, narrowing, and `assert_never`

```python
from typing import Self, override

class Builder:
    def with_name(self, name: str) -> Self:   # returns the correct subclass type
        self._name = name
        return self

class Base:
    def run(self) -> int: ...

class Child(Base):
    @override                                  # (3.12) errors if it doesn't override
    def run(self) -> int:
        return 1
```

Use `TypeIs` (3.13) over `TypeGuard` for custom narrowing — `TypeIs` narrows in *both* the `if` and `else` branches and is almost always what you want:

```python
from typing import TypeIs

def is_str_list(val: list[object]) -> TypeIs[list[str]]:
    return all(isinstance(x, str) for x in val)

def handle(items: list[object]) -> None:
    if is_str_list(items):
        # items is list[str] here
        print(" ".join(items))
    # in the else branch, the checker knows it is NOT list[str]
```

Exhaustiveness checks with `assert_never` — basedpyright verifies every case is handled:

```python
from typing import assert_never
from enum import StrEnum

class Color(StrEnum):
    RED = "red"
    GREEN = "green"

def describe(c: Color) -> str:
    match c:
        case Color.RED:
            return "warm"
        case Color.GREEN:
            return "cool"
        case _ as unreachable:
            assert_never(unreachable)  # compile error if a Color is unhandled
```

### Protocols over ABCs for structural typing

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Closeable(Protocol):
    def close(self) -> None: ...

def shutdown(resource: Closeable) -> None:
    resource.close()
```

Prefer `Protocol` for duck-typed interfaces (no inheritance required at the call site). Use ABCs only when you need shared implementation or explicit registration. `ParamSpec`, `Concatenate`, and `TypeVarTuple`/`Unpack` remain available for decorator and variadic-generic signatures, now via the inline PEP 695 syntax where possible.

## Dataclasses and data modeling

For internal, trusted data, prefer a modern dataclass — `slots=True` for memory and attribute-typo safety, `frozen=True` for immutability, `kw_only=True` for call-site clarity:

```python
from dataclasses import dataclass, field

@dataclass(slots=True, frozen=True, kw_only=True)
class Point:
    x: float
    y: float
    tags: list[str] = field(default_factory=list)  # never a mutable default literal
```

Never write `tags: list[str] = []` — always `field(default_factory=list)`. `slots=True` blocks accidental attribute creation; `frozen=True` makes instances hashable and thread-safe.

**Choosing a data model:**

| Use case | Choose | Why |
|---|---|---|
| Internal trusted data, config objects | `@dataclass(slots=True, frozen=True)` | Stdlib, fast, zero deps |
| Validating untrusted input (HTTP, config files, env) | **pydantic v2** | Rust-core validation, JSON schema, coercion |
| Max-throughput (de)serialization of JSON/MsgPack | **msgspec** | Per msgspec.dev's benchmarks, ~12× faster than pydantic v2 on decode, and its `Struct` is 5–60× faster than dataclasses/attrs/pydantic for common operations |
| Rich class behavior without validation | **attrs** | Converters, validators, mature |

Do not use pydantic as a glorified dataclass — its validation cost is only worth paying at trust boundaries. For hot serialization paths inside a service, use msgspec.

```python
from pydantic import BaseModel, Field

class CreateUser(BaseModel):
    email: str
    age: int = Field(ge=0, le=130)
    # Validates and coerces at construction; raises ValidationError on bad input.
```

## Template strings (t-strings, PEP 750, 3.14)

t-strings look like f-strings but return a `Template` object instead of a `str`, keeping the static parts and interpolated values *separate* until a processor combines them. This makes injection-safe SQL/HTML/shell construction possible by design. Use f-strings for ordinary display text; reach for t-strings when an untrusted value crosses into another language.

```python
from string.templatelib import Template, Interpolation

def render_html(template: Template) -> str:
    """Escape every interpolated value; leave static parts untouched."""
    from html import escape
    parts: list[str] = []
    for part in template:
        if isinstance(part, Interpolation):
            parts.append(escape(str(part.value)))
        else:
            parts.append(part)
    return "".join(parts)

user_input = "<script>alert('xss')</script>"
safe = render_html(t"<p>{user_input}</p>")
# -> "<p>&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;</p>"
```

A `Template` iterates into an alternating sequence of `str` static parts and `Interpolation` objects; each `Interpolation` exposes `.value`, `.expression`, `.conversion`, and `.format_spec`. **Critical insight:** t-strings shift escaping from developer discipline (remembering to escape every value) to library design (the processor cannot forget). There is no stdlib `html()`/`sql()` yet — you write or import the processor.

## Structured concurrency & parallelism

Choose the right tool:

| Workload | Tool | Version |
|---|---|---|
| I/O-bound concurrency (network, disk) | `asyncio` + `TaskGroup` | 3.11+ |
| CPU-bound parallelism, isolated | `InterpreterPoolExecutor` (subinterpreters) | 3.14 |
| CPU-bound parallelism, shared memory | free-threaded build + `threading`/`ThreadPoolExecutor` | 3.14 (opt-in) |
| CPU-bound, process isolation, mature | `ProcessPoolExecutor` | any |

### asyncio: TaskGroup and timeout (3.11) are the default idioms

Use `asyncio.TaskGroup` instead of `asyncio.gather`. If any task raises, the group cancels the remaining tasks and raises an `ExceptionGroup` — no orphaned background tasks:

```python
import asyncio

async def fetch(client: object, url: str) -> str: ...

async def fetch_all(client: object, urls: list[str]) -> list[str]:
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(fetch(client, u)) for u in urls]
    return [t.result() for t in tasks]  # all done here; exceptions already raised

async def with_deadline() -> None:
    async with asyncio.timeout(5.0):     # raises TimeoutError if the block overruns
        await slow_operation()
```

Enter asyncio through `asyncio.run(main())` (or `asyncio.Runner` for advanced control). Never call the deprecated `asyncio.get_event_loop()` to create loops. New in 3.14: introspect a running process with `python -m asyncio ps PID` and `python -m asyncio pstree PID` to see the live task tree — invaluable for debugging stuck coroutines.

### Subinterpreters (PEP 734, 3.14)

`InterpreterPoolExecutor` gives you true multi-core parallelism with process-like isolation but lower overhead than `multiprocessing`. Objects are copied (via pickle) across the boundary — no shared mutable state:

```python
from concurrent.futures import InterpreterPoolExecutor

def cpu_work(n: int) -> int:
    return sum(i * i for i in range(n))

with InterpreterPoolExecutor() as executor:
    results = list(executor.map(cpu_work, [1_000_000, 2_000_000, 3_000_000]))
```

Or the lower-level API in `concurrent.interpreters`: `interp = interpreters.create(); interp.call(fn, arg)`, plus `interpreters.create_queue()` for cross-interpreter communication.

### Free-threading (PEP 779, 3.14)

The free-threaded build is *officially supported* in 3.14 (no longer experimental), but remains an **opt-in separate build** (`3.14t`). Use it only for measured CPU-bound, thread-parallel workloads. Per the official CPython free-threading docs, single-threaded overhead on the pyperformance suite ranges from about 1% on macOS aarch64 to 8% on x86-64 Linux (PEP 779 set a 15% single-thread regression as the hard acceptance ceiling, and free-threaded runs can use up to ~20% more memory on the pyperformance geometric mean). C-extension packages may re-enable the GIL silently — always verify:

```python
import sys
print(sys._is_gil_enabled())   # False on 3.14t when GIL is actually off
```

Control it with the `PYTHON_GIL` env var or `-X gil=0/1`. Install via `uv python install 3.14t`. Note: `sys._is_gil_enabled()` returns `True` (not an error) if an imported C extension forced the GIL back on — check it *after* imports.

## Error handling & exceptions

Custom exceptions inherit from a package-level base so callers can catch broadly or narrowly:

```python
class MyProjectError(Exception):
    """Base for all errors raised by this package."""

class ConfigError(MyProjectError): ...
class RetryableError(MyProjectError): ...
```

**PEP 758 (3.14):** parentheses are optional when catching multiple types (without `as`):

```python
try:
    connect()
except TimeoutError, ConnectionRefusedError:   # no parentheses needed
    handle_network_failure()
```

**Exception groups & `except*`** for concurrent failures (a `TaskGroup` raises `ExceptionGroup`):

```python
try:
    async with asyncio.TaskGroup() as tg:
        tg.create_task(a())
        tg.create_task(b())
except* ValueError as eg:
    for exc in eg.exceptions:
        log.warning("value error: %s", exc)
except* KeyError as eg:
    ...
```

**PEP 765 (3.14):** the compiler now emits a `SyntaxWarning` for `return`/`break`/`continue` that exits a `finally` block — such control flow silently swallows exceptions. Never do it; restructure the code.

## Logging

Get a module-level logger with `logging.getLogger(__name__)`; never log through the root logger, never configure logging at import time in library code. Configure once at application entry. Use `%`-style lazy args, not f-strings, in log calls so formatting is skipped when the level is disabled:

```python
import logging

log = logging.getLogger(__name__)

def charge(amount: int, user_id: str) -> None:
    log.info("charging %d cents for user %s", amount, user_id)  # lazy, not f-string
```

For structured/JSON logging in services, use **structlog**. Configure application logging in `main()` with `logging.dictConfig`. Avoid rolling your own handler stack.

## Pathlib, zoneinfo, and stdlib currency

Use `pathlib.Path`, never `os.path`. Ruff's `PTH` rules flag the legacy calls.

```python
from pathlib import Path

config = Path("~/.config/app.toml").expanduser()
if config.exists():
    data = config.read_text(encoding="utf-8")
for py_file in Path("src").rglob("*.py"):
    ...
```

Use `zoneinfo.ZoneInfo` (stdlib), never `pytz`. Always attach a timezone — Ruff's `DTZ` rules flag naive `datetime.now()`:

```python
from datetime import datetime
from zoneinfo import ZoneInfo

now = datetime.now(tz=ZoneInfo("America/New_York"))
```

Prefer `enum.StrEnum`/`IntEnum` (3.11) for string/int enums, `functools.cached_property` for lazy computed attributes, and `contextlib` (`contextmanager`, `suppress`, `ExitStack`) for resource management. New in 3.14: `compression.zstd` provides Zstandard compression in the stdlib:

```python
from compression import zstd

blob = zstd.compress(b"large payload" * 1000)
original = zstd.decompress(blob)
```

## Ruff: linting and formatting

Ruff is the single linter *and* formatter for this stack. It replaces **Flake8 (and its plugins), isort, Black, pyupgrade, pydocstyle, autoflake, and much of Bandit** — do not install or configure any of those separately. As of Ruff 0.16.0 it enables 413 rules by default, but pin your rule set explicitly with `select` (as in the `pyproject.toml` above) so upgrades don't silently change behavior.

Daily commands:

```bash
ruff check .                    # lint
ruff check --fix .              # lint + apply safe autofixes
ruff check --fix --unsafe-fixes .   # also apply fixes that may change behavior — review the diff
ruff format .                   # format (Black-compatible)
ruff format --check .           # verify formatting in CI (no writes)
ruff check --select I --fix .   # sort imports only
ruff rule RUF100                # explain a rule
```

**Recommended rule selection and rationale:**

| Prefix | Source | Why enable |
|---|---|---|
| `E`,`W`,`F` | pycodestyle, Pyflakes | Baseline errors and undefined names |
| `I` | isort | Import sorting (no separate isort) |
| `UP` | pyupgrade | Auto-modernize to current-Python syntax |
| `B` | flake8-bugbear | Real bug patterns (mutable defaults, etc.) |
| `SIM` | flake8-simplify | Simplify redundant constructs |
| `C4` | comprehensions | Faster/cleaner comprehensions |
| `PTH` | use-pathlib | Force `pathlib` over `os.path` |
| `DTZ` | datetimez | Force timezone-aware datetimes |
| `TC` | type-checking | Move type-only imports into `TYPE_CHECKING` |
| `ANN` | annotations | Require annotations (belt-and-suspenders with basedpyright) |
| `RET`,`PIE`,`TID`,`ARG`,`RUF` | assorted | Return hygiene, misc lint, banned imports, unused args, Ruff-specific |

Ignore `E501` (the formatter handles line length) and typically `ANN401` (explicit `Any` where genuinely unavoidable).

**`TC` rules + runtime annotations — the Pydantic/FastAPI gotcha.** `TC001`/`TC002`/`TC003` move imports used *only* in annotations into an `if TYPE_CHECKING:` block. That breaks Pydantic and FastAPI, which read annotations at runtime to build validators. Register your runtime-annotation base classes so Ruff leaves those imports alone:

```toml
[tool.ruff.lint.flake8-type-checking]
runtime-evaluated-base-classes = ["pydantic.BaseModel"]
runtime-evaluated-decorators = ["fastapi.APIRouter.get", "fastapi.APIRouter.post"]
```

(Note a known limitation: Ruff does not do cross-file analysis, so a field whose type is a Pydantic model imported from another module can still trip `TC001` — scope a `# noqa: TC001` in those spots.)

**`# noqa` discipline:** always scope it — `# noqa: F401`, never a bare `# noqa`. Ruff also supports `# ruff: ignore[F401]` line comments. Prefer fixing over suppressing.

**pre-commit integration:**

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.16.3
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format
```

## basedpyright with `recommended`

basedpyright is a fork of pyright with additional strict diagnostic rules, baseline support for incremental adoption, and improved CI/LSP integration. It is the type checker for this stack. **Do not use mypy, and do not mix mypy config or `# type: ignore` directives into this project** — basedpyright uses `# pyright: ignore[rule]` instead.

**What `recommended` means.** basedpyright's default mode is `recommended`. Per the official docs, it "enables all diagnostic rules as either 'warning' or 'error', but sets failOnWarnings to true so that all diagnostics will still cause a non-zero exit code when run in the CLI" — "essentially the same as 'all', but makes it easier to differentiate errors that are likely to cause a runtime crash like an undefined variable from less serious warnings such as a missing type annotation." This is stricter than pyright's `strict`. `recommended` also enables basedpyright-only rules that catch what pyright ignores: `reportAny`, `reportExplicitAny`, `reportUnusedCallResult`, `reportImplicitStringConcatenation`, `reportImplicitRelativeImport` (an *error* in recommended), `reportUnannotatedClassAttribute`, `reportIgnoreCommentWithoutRule`, and more. It also defaults `pythonPlatform` to `All` (assume your code runs on any OS) and auto-detects `./.venv` as the interpreter.

**Pragmatic relaxations teams actually make.** A pure `recommended` run is noisy on real projects. The common, defensible relaxations:

```toml
[tool.basedpyright]
pythonVersion = "3.14"
typeCheckingMode = "recommended"
# Relax the highest-friction rules:
reportUnusedCallResult = false      # firing on every un-assigned function call is too noisy
reportMissingTypeStubs = false      # don't fail because a third-party lib ships no stubs
reportAny = false                   # optional: allow Any-typed expressions from untyped libs
# reportExplicitAny = false         # optional: allow explicit Any in annotations
```

Each `reportXxx` accepts a boolean or a severity string (`"none"`, `"warning"`, `"information"`, `"error"`).

- `reportUnusedCallResult` — "call statements whose return value is not used in any way and is not None." Extremely noisy; almost everyone disables it.
- `reportMissingTypeStubs` — fails when an imported library ships no stubs; disable it or use `allowedUntypedLibraries` per-module.
- `reportAny` / `reportExplicitAny` — the two `Any` bans (`reportAny` bans *expressions* typed `Any`; `reportExplicitAny` bans the `Any` type *in annotations*). Keep them on if you can; relax per-file when wrapping untyped third-party code.

**Writing code that passes `recommended`:**

- Annotate every function parameter and return type. No implicit `Any`, no untyped `def`.
- Narrow before use; the checker tracks `reportUnreachable` and will flag dead branches.
- Use `cast()` sparingly and only when you know more than the checker — never to paper over a real type error.
- Suppress with a **scoped** `# pyright: ignore[rule]` — never `# type: ignore`. `reportIgnoreCommentWithoutRule` requires the bracketed rule code, and `# type: ignore` comments are disabled by default in recommended mode (`enableTypeIgnoreComments = false`) because they silence *all* errors on the line.

```python
from typing import cast

value = cast(int, untyped_lib.get_count())      # you guarantee it's an int
result = risky()  # pyright: ignore[reportUnknownMemberType]   # scoped, documented
```

**Adopting on an existing codebase — baseline.** Rather than fixing thousands of errors at once, snapshot the current errors and fail only on *new* ones:

```bash
basedpyright --writebaseline     # writes ./.basedpyright/baseline.json — commit it
```

Commit the generated baseline; subsequent runs only report regressions on new or modified code. In CI, basedpyright defaults baseline handling to lock mode (fails if the baseline is stale).

**Commands & CI:**

```bash
basedpyright                     # check the project using pyproject.toml config
basedpyright src/                # check a path
basedpyright --outputjson        # machine-readable diagnostics for tooling
basedpyright --watch             # re-check on change during development
uvx basedpyright                 # run without adding to the project
```

In `recommended` mode no extra flag is needed for CI strictness — `failOnWarnings` already makes warnings fail the build. The PyPI wheel bundles Node.js (via `nodejs-wheel-binaries`), so no separate Node install is required.

## Testing with pytest

Use pytest 9.x. Type your test helpers and fixtures so they pass basedpyright; per-file-ignore `ANN` for the test tree if full annotation of test bodies is too heavy.

```python
import pytest

@pytest.fixture
def engine() -> Engine:
    return Engine(config="test")

@pytest.mark.parametrize(
    ("value", "expected"),
    [(1, 2), (2, 4), (3, 6)],
)
def test_double(value: int, expected: int) -> None:
    assert double(value) == expected
```

**Async tests.** For an asyncio-only app, use **pytest-asyncio** (1.x, which requires pytest ≥ 8.4) with `asyncio_mode = "auto"` (set in `pyproject.toml`) so `async def test_*` functions run without per-test markers. If your library must support both asyncio and Trio, use **anyio**'s pytest plugin instead. Don't mix both plugins in one suite.

```python
import pytest

@pytest.mark.asyncio      # unnecessary in "auto" mode, shown for explicitness
async def test_fetch() -> None:
    result = await fetch("https://example.org")
    assert result.status_code == 200
```

## Ecosystem currency

| Job | Use | Avoid / note |
|---|---|---|
| HTTP client | `httpx` | `requests` is maintenance-mode and sync-only |
| DataFrames | `polars` | `pandas` for legacy/interop only |
| Data validation | `pydantic` v2 | pydantic v1 patterns are dead |
| Fast serialization | `msgspec` | when pydantic's validation cost isn't needed |
| Structured logging | `structlog` | hand-rolled JSON handlers |
| CLI | `typer` (or `click`) | `argparse` only for zero-dep scripts |
| Timezones | `zoneinfo` (stdlib) | `pytz` |
| Env/venv/deps/build | `uv` | pip, poetry, pipenv, pyenv, conda |
| Lint + format | `ruff` | Flake8, isort, Black, pyupgrade |
| Type check | `basedpyright` | mypy |

`uvloop` is a drop-in faster event loop for asyncio on Linux/macOS (not Windows); verify 3.14 wheel availability before adopting, and it is unrelated to the free-threaded build.

## CI: GitHub Actions

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - name: Install uv
        uses: astral-sh/setup-uv@v10
        with:
          enable-cache: true
      - name: Sync (locked, with dev tools)
        run: uv sync --locked --all-extras --dev
      - name: Lint
        run: uv run ruff check .
      - name: Format check
        run: uv run ruff format --check .
      - name: Type check
        run: uv run basedpyright
      - name: Test
        run: uv run pytest
```

For Docker, install with `uv sync --frozen --no-dev` in a builder stage and copy the resulting `.venv` into a slim runtime image. Pin `setup-uv` to a full version tag (moving major tags are no longer published; use a version like `@v10` or a pinned SHA).

## Anti-patterns to avoid

- **`from __future__ import annotations`** — unnecessary in 3.14; annotations are deferred by default.
- **`typing.List` / `Optional[X]` / `Union[A, B]`** — use `list[...]`, `X | None`, `A | B`.
- **Module-level `TypeVar("T")` and `Generic[T]`** — use `def f[T]()` / `class C[T]` (PEP 695).
- **`# type: ignore`** — use scoped `# pyright: ignore[rule]`; bare `# type: ignore` is disabled by default and silences everything.
- **`os.path`** — use `pathlib.Path` (`PTH` rules enforce this).
- **`pytz`** — use `zoneinfo.ZoneInfo`; always pass `tz=` to `datetime.now()`.
- **`pip install` / `poetry` / `pyenv` / `python -m venv` inside a uv project** — use `uv add` / `uv sync` / `uv python install`.
- **Mutable default arguments / dataclass fields** — `field(default_factory=list)`, never `= []`.
- **f-strings for SQL/HTML/shell with untrusted input** — use t-strings with an escaping processor, or parameterized APIs.
- **`asyncio.gather` for fallible concurrent work** — use `TaskGroup` so failures cancel siblings.
- **`asyncio.get_event_loop()`** — use `asyncio.run()` / `asyncio.Runner`.
- **f-strings inside `log.info(...)`** — use `%`-style lazy args.
- **Installing Flake8/isort/Black/mypy alongside** — Ruff and basedpyright already cover these; mixing them causes conflicting fixes.
- **Committing `requirements.txt` as source of truth** — `pyproject.toml` + `uv.lock` are canonical.
- **Relying on the experimental JIT or the free-threaded build in production** without measuring — the JIT is experimental in 3.14 (do not depend on it); the free-threaded build is supported but opt-in and carries single-threaded overhead.