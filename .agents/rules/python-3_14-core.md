---
type: "agent_requested"
description: "Python 3.14 + uv + Ruff + basedpyright coding guidelines"
---
# Python 3.14 with uv, Ruff, and basedpyright: The Strict-Typed Toolchain Reference

This stack is modern Python at its most rigorous: CPython 3.14 as the runtime, uv as the single tool for interpreters, environments, locking, and builds, Ruff as the linter and formatter, and basedpyright in `recommended` mode as a near-maximal static type checker. It is exceptional at producing reproducible, fully typed, fast-to-check code where the toolchain — not code review — catches undefined names, missing annotations, unhandled `Any`, and unawaited coroutines before they ship. Optimize for code that passes `basedpyright` with zero suppressions, formats identically under `ruff format`, and resolves from a committed `uv.lock`.

The biggest way agents write wrong-but-plausible code here is importing habits from older Python and adjacent ecosystems: reaching for `typing.List`/`Optional[X]` instead of `list`/`X | None`, writing `from __future__ import annotations` (unnecessary and counterproductive on 3.14), declaring `TypeVar`/`Generic[T]` instead of PEP 695 `class Box[T]`, leaving return values and `Any` untyped (which `recommended` mode rejects), calling `pip`/`python -m venv`/`poetry` instead of `uv`, and adding `flake8`/`black`/`isort`/`mypy` as separate tools when Ruff and basedpyright already own those roles. Treat basedpyright's warnings as build failures — in `recommended` mode they are.

## Project layout and uv

uv is the entry point for everything: it installs and pins the interpreter, creates the virtual environment, resolves and locks dependencies, runs commands, and builds wheels. Never invoke `pip`, `python -m venv`, `pip-tools`, `pipx`, `poetry`, or `pyenv` directly; uv subsumes all of them.

Create a packaged project (the default since uv 0.12 — a `src/` layout with a build system and entry point):

```console
$ uv init --package myservice
$ cd myservice
$ uv add httpx
$ uv add --dev basedpyright ruff pytest
```

This produces a `pyproject.toml` whose `[build-system]` uses uv's own build backend. A complete, current manifest for this stack:

```toml
[project]
name = "myservice"
version = "0.1.0"
description = "Example service on the strict-typed stack"
readme = "README.md"
requires-python = ">=3.14"
dependencies = [
    "httpx>=0.28",
]

[project.scripts]
myservice = "myservice:main"

[dependency-groups]
dev = [
    "basedpyright>=1.39",
    "ruff>=0.16",
    "pytest>=9",
]

[build-system]
requires = ["uv_build>=0.12.10,<0.13"]
build-backend = "uv_build"

[tool.uv]
required-version = ">=0.12"
```

Key rules:

- **`requires-python` is the single source of truth for the minimum runtime.** Ruff infers its `target-version` from it when unset, and it constrains resolution. Set it to `>=3.14` for this stack; do not raise it casually — a newer SDK does not raise your deployment floor.
- **Development tools go in the PEP 735 `[dependency-groups]` `dev` group**, not in `[project.optional-dependencies]` and never in the runtime `dependencies`. `uv sync` installs the `dev` group by default; `uv sync --no-dev` gives a production environment. Add them with `uv add --dev <pkg>`.
- **Commit `uv.lock`.** It is the reproducibility contract. `uv run` and `uv sync` verify the lock is current with `pyproject.toml` before every invocation, so the environment is never silently stale.
- **Pin the build backend with an upper bound** (`uv_build>=0.12.10,<0.13`); the backend follows uv's versioning and the bound keeps builds reproducible. `uv_build` is for pure-Python packages; a project with C, Rust, or Cython extensions needs `maturin`, `scikit-build-core`, or `setuptools` instead.

Daily commands — always through `uv run` so the locked environment is used without manual activation:

```console
$ uv run ruff format .
$ uv run ruff check --fix .
$ uv run basedpyright
$ uv run pytest
$ uv sync --frozen          # CI: install exactly the lockfile, never re-resolve
$ uv build                  # produce sdist + wheel in dist/
$ uv python install 3.14    # install the interpreter itself
```

Pin the interpreter with a `.python-version` file (`uv python pin 3.14`); uv reads it automatically and downloads the interpreter if absent. In CI, `uv sync --frozen` fails rather than silently updating the lock — that is the behavior you want.

For a monorepo, use a workspace: a root `pyproject.toml` with `[tool.uv.workspace]` `members = [...]`, one shared `uv.lock`, and inter-member dependencies expressed through `[tool.uv.sources]` with `{ workspace = true }`. Workspace-level `[tool.uv]` config is read only from the root.

For private indexes, prefer named `[[tool.uv.index]]` entries with `explicit = true` and `[tool.uv.sources]` pinning specific packages to them, rather than a global `index-url`, so only the intended packages come from the private index:

```toml
[[tool.uv.index]]
name = "internal"
url = "https://pypi.internal.example.com/simple"
explicit = true

[tool.uv.sources]
mylib = { index = "internal" }
```

## Language: annotations, generics, and modern syntax

Target the 3.14 language mode. The defining change for typed code is **deferred annotation evaluation (PEP 649/749)**: annotations are no longer evaluated at definition time but lazily on access. Two practical consequences:

- **Never write `from __future__ import annotations`.** It was the workaround for forward references and is now redundant; on 3.14 it changes annotations to plain strings and defeats the runtime-introspection tools. Forward references now just work without quoting.
- **Introspect annotations with `annotationlib`, not raw `__annotations__` or `typing.get_type_hints` where laziness matters.** `annotationlib.get_annotations(obj, format=Format.VALUE)` evaluates them; `Format.FORWARDREF` returns `ForwardRef` placeholders for names not yet defined; `Format.STRING` returns source strings. This is the correct API for libraries (dataclass-likes, serializers, DI) that read annotations at runtime.

```python
from annotationlib import Format, get_annotations


class Node:
    value: int
    next: Node | None  # forward reference resolves with no quotes, no __future__


# Safe even when a referenced name is not importable at call time:
hints = get_annotations(Node, format=Format.FORWARDREF)
# {'value': int, 'next': ForwardRef('Node | None')}
```

Use **PEP 695 syntax for all generics and type aliases** — no `TypeVar`, `Generic`, or `typing.TypeAlias` imports:

```python
from collections.abc import Callable, Iterable


type Predicate[T] = Callable[[T], bool]


def first_match[T](items: Iterable[T], pred: Predicate[T]) -> T | None:
    for item in items:
        if pred(item):
            return item
    return None


class Repository[T]:
    def __init__(self) -> None:
        self._items: list[T] = []

    def add(self, item: T) -> None:
        self._items.append(item)

    def all(self) -> list[T]:
        return list(self._items)
```

The `type` statement is lazily evaluated, so aliases can reference names defined later in the module. Type parameter variance is inferred — do not hand-declare `covariant=`/`contravariant=`.

Use built-in generics and union syntax everywhere: `list[str]`, `dict[str, int]`, `str | None`, `int | str`. Ruff's `UP` rules rewrite `Optional[X]`, `Union[X, Y]`, and `typing.List` to the modern forms automatically. Prefer `collections.abc` for abstract types (`Callable`, `Iterable`, `Sequence`, `Mapping`) over the deprecated `typing` aliases.

Other 3.14 syntax worth using where it fits:

- **Bracketless `except` (PEP 758):** `except ValueError, TypeError:` and `except* ValueError, TypeError:` no longer need parentheses. Ruff's formatter adopts this when `target-version` is 3.14+.
- **PEP 765:** `return`/`break`/`continue` that exit a `finally` block is now a syntax warning; never write one — control flow escaping `finally` swallows exceptions.

## Type-safe code for `recommended` mode

basedpyright defaults to `typeCheckingMode = "recommended"`. Per the basedpyright config-files documentation, `"recommended"` "enables all diagnostic rules as either 'warning' or 'error', but sets `failOnWarnings` to true so that all diagnostics will still cause a non-zero exit code when run in the CLI. this means 'recommended' is essentially the same as 'all'" — the difference is only in labeling: `recommended` reports lower-severity issues (a missing annotation) as warnings and likely-crash issues (an undefined variable) as errors, while `all` escalates everything to error. Because `failOnWarnings` is on, both fail the CLI identically. Write code that produces **zero** diagnostics.

What this demands in practice:

- **Annotate everything.** Every parameter, every return type, and — because `reportUnannotatedClassAttribute` is on — every class attribute. `recommended` also checks unannotated functions (`analyzeUnannotatedFunctions`), so there is no "escape by leaving it untyped."
- **Eliminate `Any`.** `reportAny` flags any *expression* whose type is `Any`; `reportExplicitAny` flags the `Any` *annotation* itself. When a third-party API returns `Any`, narrow it immediately with `cast()` or an `isinstance` check and a typed local, rather than letting `Any` propagate.
- **Use every call result, or explicitly discard it.** `reportUnusedCallResult` fires on a call statement whose non-`None` return is ignored. Assign to `_` to signal intent: `_ = queue.put_nowait(item)`.
- **Never drop a coroutine.** `reportUnusedCoroutine` is an *error* — a bare `some_async_fn()` without `await` is almost always a missing `await`.
- **Mark overrides.** `reportImplicitOverride` requires `@override` (from `typing`) on any method that overrides a base-class method.
- **Put rules in ignore comments.** `reportIgnoreCommentWithoutRule` requires suppressions to name the rule: `# pyright: ignore[reportAny]`, never a bare `# pyright: ignore`. Prefer `# pyright: ignore[...]` over `# type: ignore` — basedpyright disables `# type: ignore` comments by default (`enableTypeIgnoreComments = false`) even in `all` mode.

basedpyright also adds diagnostic rules absent from upstream pyright, including `reportAny`, `reportExplicitAny`, `reportIgnoreCommentWithoutRule`, `reportUnreachable`, `reportPrivateLocalImportUsage`, `reportImplicitRelativeImport`, `reportInvalidCast`, `reportUnsafeMultipleInheritance`, `reportUnusedParameter`, `reportImplicitAbstractClass`, `reportUnannotatedClassAttribute`, `reportEmptyAbstractUsage`, `reportInvalidAbstractMethod`, and `reportSelfClsDefault` — all active in `recommended`.

A representative fully-typed unit:

```python
from typing import override
from collections.abc import Mapping


class ConfigError(Exception):
    pass


class Settings:
    debug: bool
    timeout: float

    def __init__(self, *, debug: bool, timeout: float) -> None:
        self.debug = debug
        self.timeout = timeout

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "Settings":
        raw = env.get("TIMEOUT")
        if raw is None:
            raise ConfigError("TIMEOUT is required")
        return cls(debug=env.get("DEBUG") == "1", timeout=float(raw))


class VerboseSettings(Settings):
    @override
    def __init__(self, *, debug: bool, timeout: float) -> None:
        super().__init__(debug=True, timeout=timeout)
```

Handling `Any` from an untyped boundary — narrow at the edge so nothing downstream is `Any`:

```python
import json
from typing import cast


def load_port(raw: str) -> int:
    parsed = cast(dict[str, object], json.loads(raw))  # json.loads returns Any
    value = parsed.get("port")
    if not isinstance(value, int):
        raise ValueError("port must be an integer")
    return value  # narrowed to int; no reportAny downstream
```

Configuration goes under `[tool.basedpyright]`. Set `pythonVersion` explicitly for reproducible CI (it otherwise defaults to the running interpreter):

```toml
[tool.basedpyright]
pythonVersion = "3.14"
typeCheckingMode = "recommended"
include = ["src", "tests"]
# reportMissingTypeStubs is a warning in recommended; silence it for a
# well-known untyped dependency rather than weakening the whole mode:
# reportMissingTypeStubs = false
```

Do not downgrade `typeCheckingMode` to `standard` or `basic` to make errors disappear; fix the code or add a rule-scoped ignore comment. For adopting the strict mode on a large existing tree without fixing everything at once, `basedpyright --writebaseline` records current diagnostics to a baseline file so only *new* issues fail — but new code should never rely on it.

## Data modeling

For plain data, prefer standard-library tools before reaching for a dependency:

```python
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float

    def translated(self, dx: float, dy: float) -> "Point":
        return Point(self.x + dx, self.y + dy)


@dataclass(slots=True)
class Bucket:
    name: str
    items: list[str] = field(default_factory=list)
```

`frozen=True` gives immutability and hashability; `slots=True` cuts per-instance memory and blocks accidental attribute typos. Never use a mutable default directly (`items: list[str] = []`) — Ruff's `B006`/`RUF012` and dataclass semantics both reject it; use `field(default_factory=list)`.

For validation, parsing untrusted input, or settings, add **Pydantic v2** as a runtime dependency — it is the current default for typed validation and its model classes are fully understood by basedpyright:

```python
from pydantic import BaseModel, Field


class CreateUser(BaseModel):
    email: str
    age: int = Field(ge=0, le=120)


user = CreateUser.model_validate({"email": "a@b.com", "age": 30})
```

Choose dataclasses for internal, already-trusted data; Pydantic when data crosses a trust boundary and needs validation or (de)serialization.

## String templating with t-strings (PEP 750)

Template strings were added in Python 3.14: `t"..."` "has the full flexibility of Python's f-strings, but returns a `Template` instance that gives access to the static and interpolated (in curly brackets) parts of a string before they are combined." A `string.templatelib.Template` exposes `.strings` (literal fragments) and `.interpolations` (the interpolated values, each an `Interpolation` with `.value`, `.expression`, `.conversion`, `.format_spec`) rather than a finished `str`. This lets a library sanitize or escape interpolated values *before* rendering, making injection bugs structurally preventable. Application code mostly *consumes* t-strings through a library helper; library code writes the processing function.

```python
from string.templatelib import Interpolation, Template
from html import escape


def render_html(template: Template) -> str:
    parts: list[str] = []
    for item in template:
        if isinstance(item, Interpolation):
            parts.append(escape(str(item.value)))
        else:  # item is a literal str fragment
            parts.append(item)
    return "".join(parts)


user_input = "<script>alert('xss')</script>"
safe = render_html(t"<p>Hello, {user_input}</p>")
# "<p>Hello, &lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;</p>"
```

Note that concatenating a `Template` with a `str` is not supported, and a t-string is never a drop-in for a place that expects `str`. Use plain f-strings for ordinary display formatting; reserve t-strings for cases where deferred, structured processing (escaping, SQL parameterization, structured logging) is the point.

## Concurrency

3.14 gives three real concurrency models. Pick by workload:

- **`asyncio` for I/O-bound work.** Use `asyncio.TaskGroup` (structured concurrency) over bare `create_task` — it propagates exceptions and cancels siblings on failure. `asyncio.timeout()` is the idiomatic cancellation scope.
- **`concurrent.interpreters` / `InterpreterPoolExecutor` for CPU-bound parallelism** without multiprocessing's fork overhead. Each interpreter is isolated; data crossing the boundary is copied (via pickle for most objects) or passed through a cross-interpreter `Queue`. This is new in 3.14 and is the practical replacement for `multiprocessing` in many CPU-bound cases.
- **Free-threaded (no-GIL) builds** are officially supported (PEP 779) but remain an opt-in build variant (`python3.14t`), not the default. Use it only when your entire dependency graph ships `cp314t` wheels; a C extension that has not declared GIL-safety will silently re-enable the GIL on import.

Structured async with a task group:

```python
import asyncio
import httpx


async def fetch(client: httpx.AsyncClient, url: str) -> int:
    response = await client.get(url)
    return response.status_code


async def fetch_all(urls: list[str]) -> list[int]:
    async with httpx.AsyncClient() as client:
        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(fetch(client, url)) for url in urls]
    return [task.result() for task in tasks]  # all done; failures already raised
```

CPU-bound parallelism across interpreters:

```python
from concurrent.futures import InterpreterPoolExecutor


def count_primes(limit: int) -> int:
    return sum(
        all(n % d for d in range(2, int(n**0.5) + 1))
        for n in range(2, limit)
    )


def parallel_counts(limits: list[int]) -> list[int]:
    with InterpreterPoolExecutor(max_workers=4) as pool:
        return list(pool.map(count_primes, limits))
```

Per the Python 3.14 `multiprocessing` docs, "On POSIX platforms the default start method was changed from `fork` to `forkserver` to retain the performance but avoid common multithreaded process incompatibilities." Code that relied on inherited global state across a `fork` must now pass that state explicitly to `ProcessPoolExecutor`/`multiprocessing`.

## Standard-library niceties on 3.14

- **Zstandard (PEP 784):** `compression.zstd` is now in the stdlib, and `tarfile`/`zipfile`/`shutil` can read and write Zstandard archives. Prefer it over a third-party binding for new compression code.
- **`pathlib` over `os.path`.** Ruff's `PTH` rules flag `os.path` usage; use `Path.read_text()`, `Path.glob()`, etc.
- **`uuid`:** versions 6–8 are supported and 3–5 generation is faster.
- The **JIT** compiler ships in official macOS/Windows binaries but is experimental and off by default (`PYTHON_JIT=1` to try); do not depend on it in production or in benchmarks presented as stable.

## Testing

Use **pytest** (add to the `dev` group). Configure it in `pyproject.toml`; pytest 9 reads a `[tool.pytest.ini_options]` table:

```toml
[tool.pytest.ini_options]
minversion = "9.0"
addopts = ["-ra", "--strict-markers", "--strict-config"]
testpaths = ["tests"]
```

Write plain functions with bare `assert`, use fixtures for setup/teardown, and `@pytest.mark.parametrize` for table-driven cases. Keep tests fully typed — they are checked by basedpyright too when `tests` is in `include`.

```python
import pytest
from myservice import Settings, ConfigError


@pytest.mark.parametrize(
    ("env", "expected_debug"),
    [
        ({"TIMEOUT": "1.0", "DEBUG": "1"}, True),
        ({"TIMEOUT": "1.0"}, False),
    ],
)
def test_from_env(env: dict[str, str], expected_debug: bool) -> None:
    settings = Settings.from_env(env)
    assert settings.debug is expected_debug


def test_missing_timeout_raises() -> None:
    with pytest.raises(ConfigError):
        Settings.from_env({})
```

Run with `uv run pytest`. For async tests, add `anyio` or `pytest-asyncio` to the `dev` group. Parallelize large suites with `pytest-xdist`.

## Tooling configuration: Ruff

Ruff is both linter and formatter — do not add `black`, `isort`, `flake8`, `autoflake`, or `pyupgrade`; Ruff owns all of those roles. Per Astral's Ruff v0.16.0 release, "Ruff now enables 413 rules by default, up from 59 in previous versions" (and the total rule count grew from 708 to 968 since the default set was last changed). Still declare your selection **explicitly** with `select` so upgrades never silently change what fires:

```toml
[tool.ruff]
target-version = "py314"
line-length = 88

[tool.ruff.lint]
select = [
    "E", "F",      # pycodestyle errors, Pyflakes
    "I",           # isort (import sorting)
    "UP",          # pyupgrade — modernize syntax and type hints
    "B",           # flake8-bugbear — mutable defaults, common bugs
    "SIM",         # flake8-simplify
    "C4",          # flake8-comprehensions
    "PTH",         # prefer pathlib over os.path
    "RUF",         # Ruff-specific rules
    "TC",          # flake8-type-checking
]
ignore = ["E501"]  # line length is enforced by the formatter, not the linter

[tool.ruff.format]
quote-style = "double"
docstring-code-format = true
```

- **Set `target-version = "py314"`** (or omit it to inherit from `requires-python`). This is what lets Ruff apply 3.14-only rewrites (e.g. bracketless `except`) and the correct `UP` modernizations.
- **Let the formatter own line length**; `ignore = ["E501"]` avoids the linter and formatter fighting.
- Import sorting is a lint rule (`I`), applied by `ruff check --fix`; run `ruff check --fix` before `ruff format`.
- Ruff does **not** type-check — that is basedpyright's job. Do not add `mypy`; basedpyright is the type checker for this stack, and running two is redundant.

Commands:

```console
$ uv run ruff format .            # format
$ uv run ruff format --check .    # CI: fail if unformatted
$ uv run ruff check .             # lint
$ uv run ruff check --fix .       # lint + apply safe fixes
```

## One coherent CI sequence

```console
$ uv sync --frozen
$ uv run ruff format --check .
$ uv run ruff check .
$ uv run basedpyright
$ uv run pytest
```

Each step is fast and independent; run them in this order so formatting and lint noise doesn't obscure type or test failures.

## Anti-patterns to avoid

| Wrong | Why | Right |
|---|---|---|
| `from __future__ import annotations` | Redundant on 3.14 (PEP 649 defers evaluation) and turns annotations into strings, breaking runtime introspection | Omit it; forward references resolve natively |
| `from typing import List, Dict, Optional` | Deprecated aliases; `UP` flags them | `list`, `dict`, `X \| None` built-ins |
| `T = TypeVar("T"); class Box(Generic[T])` | Pre-3.12 boilerplate | `class Box[T]:` (PEP 695) |
| `def f(x):` with no annotations | `recommended` checks unannotated functions and requires annotations | Annotate every parameter and return |
| Letting `json.loads(...)` flow untyped | `reportAny` fails the build | `cast()` then narrow with `isinstance` at the boundary |
| `some_async_fn()` without `await` | `reportUnusedCoroutine` is an error — almost always a bug | `await some_async_fn()` |
| `# type: ignore` | Disabled by default in basedpyright; `reportIgnoreCommentWithoutRule` wants a rule | `# pyright: ignore[reportSpecificRule]` |
| `pip install`, `python -m venv`, `poetry` | uv owns interpreters, envs, locking, builds | `uv add`, `uv sync`, `uv run` |
| Adding `black` + `isort` + `flake8` | Ruff replaces all three | `ruff format` + `ruff check` |
| Adding `mypy` alongside basedpyright | Two type checkers; redundant and conflicting | basedpyright only |
| `def f(items: list[str] = [])` | Shared mutable default (`B006`/`RUF012`) | `field(default_factory=list)` or `None` sentinel |
| Lowering `typeCheckingMode` to silence errors | Hides real defects across the tree | Fix the code or add a scoped `# pyright: ignore[...]` |
| Using `python3.14t` for speed by default | Free-threading is opt-in; unprepared C extensions re-enable the GIL | Standard build unless the whole graph ships `cp314t` wheels |

## Version & compatibility

| Component | Target | Notes |
|---|---|---|
| CPython | 3.14 line | Language mode 3.14; deferred annotations, PEP 695 generics, t-strings, `concurrent.interpreters`. Free-threading (PEP 779) and JIT are opt-in/experimental. |
| Minimum runtime | `requires-python = ">=3.14"` | Deployment floor; drives Ruff `target-version` and resolution. |
| uv | 0.12 line | `uv_build>=0.12.10,<0.13` backend; PEP 735 dependency groups; commit `uv.lock`. |
| Ruff | 0.16 line | Linter + formatter; 2026 style guide; `target-version = "py314"`; explicit `select`. |
| basedpyright | 1.39 line | `typeCheckingMode = "recommended"`; `pythonVersion = "3.14"`; supports 3.14 typing features. |
| pytest | 9 line | Config in `[tool.pytest.ini_options]`. |
| Pydantic | v2 line | Optional runtime dependency for validation at trust boundaries. |

All four core tools are mutually compatible at these lines; no unresolved conflicts. Ruff and basedpyright both read `pyproject.toml` and both honor `requires-python`/`target-version` and `pythonVersion` respectively for 3.14.

- **Research date:** September 5, 2026
