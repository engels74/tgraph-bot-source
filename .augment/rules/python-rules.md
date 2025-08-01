---
type: "always_apply"
description: "Python Development Guidelines"
---
- Use `uv` or `uvx` for all Python commands (e.g., `uv run`, `uv run pytest`, `uv pip install`).  
- Adhere to Python 3.12+ best practices for 2025, and leverage modern 2025 typing features.  
- Verify type safety using `uvx basedpyright` before commits.  
- Install type stubs for dependencies (e.g., `uv pip install types-requests`) only when `basedpyright` reports missing stubs.  
- Prefer `# pyright: ignore[specific-error]` over `# type: ignore` comments, always with specific error codes.  
- **MANDATORY: Achieve exactly 0 errors and 0 warnings across ALL code including tests.** No exceptions—this prevents technical debt and ensures real issues aren't masked.  
- **Fix type issues properly rather than using ignores.** Ignores are a last resort for unavoidable third-party limitations, not a shortcut for difficult typing.  
- **NEVER use global configuration ignores.** Always use targeted per-line ignores (`# pyright: ignore[import-untyped]`) to maintain visibility of suppressed issues.  
- Add brief inline comments for ignores only when the reason isn't immediately obvious (e.g., `# pyright: ignore[import-untyped] # third-party lib has no stubs`).  
- Do not modify basedpyright rules in `pyproject.toml` to suppress issues—fix the root cause instead.  
- Treat test files with the same type safety standards as production code.