You are contributing to WhisperTray, a Python 3.12+ cross-platform tray app for speech-to-text. Write code that matches the repository’s enforced tooling and existing architecture.

Hard requirements:
- Produce code that passes Black (line length 88), isort (Black profile), Flake8, mypy, Bandit, detect-secrets, and the custom validate-build hook.
- Assume production code is type-checked strictly: every production function and method must have complete type annotations. Do not rely on implicit Optional values.
- Keep imports isort-compatible: standard library, third-party, then local imports.
- Keep cyclomatic complexity reasonable; if logic is getting branchy, split it into helpers before Flake8 complexity becomes a problem.
- Never add secrets, tokens, API keys, or sample credentials to the repo.

Style and structure:
- Use Python 3.12-era typing and stdlib features where they improve clarity.
- Prefer explicit, readable code over clever abstractions.
- Keep functions focused, testable, and small enough to understand quickly.
- Add module docstrings and docstrings for public classes/functions. Private helpers only need docstrings when the behavior is non-obvious.
- Use `PascalCase` for classes, `snake_case` for functions/variables, `UPPER_SNAKE_CASE` for constants, and leading `_` for private members.
- Prefer typed `dataclass`, `Protocol`, `Literal`, and small value objects for boundaries and configuration.
- Match the repo’s fallback-oriented design: when dependencies, UI backends, or platform features are unavailable, fail safely and degrade gracefully instead of crashing.
- Do not use bare `except:`. Catch specific exceptions when practical; otherwise log useful context and preserve safe behavior.
- Use the module logger pattern: `logger = logging.getLogger(__name__)`.
- Prefer structured logging calls without losing useful runtime context.
- Avoid placeholder code, TODO-only implementations, and dead branches.

Project-specific behavior:
- Preserve CPU-first defaults and cross-platform behavior.
- Do not block tray or hotkey responsiveness with long-running work on the main path.
- Respect the existing threading model and background-work boundaries.
- Keep config/environment parsing centralized rather than scattering env access across the app.
- When touching optional UI/overlay/tray backends, preserve safe fallback to non-Qt behavior.

Testing expectations:
- Add or update pytest tests for behavior changes.
- Follow repo conventions: `test_*.py`, `test_*` functions, grouped `Test*` classes when helpful.
- Mock or fake OS/GUI/audio integrations rather than depending on live desktop hardware or platform APIs.
- Test edge cases, failure paths, and fallback behavior, not just the happy path.
- Keep tests readable and deterministic.

Definition of done:
- Black/isort produce no changes.
- Flake8 passes.
- mypy passes for `whisper_tray/`.
- Bandit passes for production code.
- `scripts/validate-build.py` passes.
- Relevant pytest coverage is updated for the changed behavior.

When in doubt, optimize for: typed code, graceful degradation, small testable units, and consistency with the existing WhisperTray modules.
