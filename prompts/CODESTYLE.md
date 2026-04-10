You are contributing to WhisperTray, a Python 3.12+ speech-to-text tray app with optional UI backends and platform-specific integrations. Write code that matches the repository's real architecture, checked-in tooling, and fallback-oriented behavior.

This document is a repo-specific working guide. It distinguishes between:

- `Must`: enforced or high-confidence rules for all new changes.
- `Prefer`: the forward-looking style for new and touched code.
- `Legacy tolerated`: patterns that already exist and do not need repo-wide cleanup unless you are safely touching them.

## Sources of Truth

`Must`

- Treat checked-in tool and hook configuration as the canonical source of truth.
- Check `pyproject.toml`, `.flake8`, `.pre-commit-config.yaml`, and `scripts/validate-build.py` for current constraints.
- If a prompt like this file and a checked-in config disagree, follow the checked-in config and hook behavior.
- Do not duplicate numeric tool settings here unless the value is essential to understanding the code. Prefer pointing to config files because values can drift.

`Prefer`

- When a tool rule matters to a change, confirm it from config instead of relying on memory.
- Treat pre-commit and validation hooks as part of the development contract, not as optional cleanup.

## Project Shape

`Must`

- Preserve the current subsystem boundaries: configuration, audio capture, transcription, clipboard integration, hotkeys, tray runtime, and overlay runtime are separate concerns coordinated by the app layer.
- Preserve CPU-first and cross-platform behavior. Windows is the primary product target, but the core logic should remain safe to develop and test on Linux and macOS.
- Keep configuration and environment parsing centralized in config code. Do not scatter new `os.getenv` or `os.environ` reads across unrelated modules.
- Keep tray and hotkey responsiveness intact. Long-running work must not block the main tray path or input callbacks.
- Respect the existing background-work model: model loading, transcription, and optional UI work should stay on the correct threads or runtime boundaries.
- When touching optional UI, overlay, or tray backends, preserve a safe non-Qt or no-op fallback path.

`Prefer`

- Use shared state and presentation models for UI-facing behavior instead of ad-hoc dictionaries, loose tuples, or stringly typed status passing.
- Use typed boundaries between subsystems. Small dataclasses, protocols, enums, literals, and explicit result objects fit this codebase well.
- Prefer null-object patterns for optional integrations when they simplify control flow. Existing examples such as `NullOverlayController` are good models.

`Legacy tolerated`

- Older modules may still mix orchestration and lower-level details more than new code should.
- Existing code may use direct branching where a small value object or helper would now be clearer.

## Production Code Style

`Must`

- Production functions and methods must have complete type annotations.
- Do not rely on implicit optionality. If `None` is valid, make that explicit in the type.
- Keep imports grouped in isort-compatible order: standard library, third-party, then local imports.
- Add module docstrings and docstrings for public classes and public functions. Private helpers only need docstrings when behavior is non-obvious.
- Use `PascalCase` for classes, `snake_case` for functions and variables, `UPPER_SNAKE_CASE` for constants, and a leading `_` for private members.
- New or touched code must pass the applicable formatter, lint, type-check, and pre-commit checks before handoff.
- Use the simplest construct that matches the intent. Avoid syntax or abstraction that adds no semantic value.
- String formatting must match the use case: plain strings for constant text, f-strings only when interpolating values, and parameterized logging for log messages.
- The same code-quality expectations apply to production modules, tests, scripts, and repo tooling unless the repository explicitly documents an exception.
- Avoid bare `except:`. Catch specific exceptions when practical. If a broad catch is necessary at a process boundary, log useful context and preserve safe behavior.
- Never add secrets, tokens, sample credentials, or other sensitive material to the repo.
- Use the module logger pattern `logger = logging.getLogger(__name__)` when a module emits logs.

`Prefer`

- Prefer explicit, readable code over clever abstractions.
- Prefer small helpers when a function starts accumulating branches, backend-specific cases, or multi-step normalization logic.
- Prefer Python 3.12-era typing and standard-library features when they make code clearer.
- Prefer `X | None` over `Optional[X]` in new and touched production code.
- Prefer immutable or frozen value objects when the data represents a snapshot, result, command, or presentation model.
- Prefer structured logging calls such as `logger.info("Loaded model on %s", device)` over f-strings inside logging calls.
- Prefer actionable logging that explains what failed, what fallback was chosen, and whether the application remains usable.
- Prefer focused comments that explain why a tricky branch exists, not comments that restate the code.

`Legacy tolerated`

- Some current modules still use `Optional[...]` instead of `| None`.
- Some current modules still use f-strings in logging calls.
- Existing code may use targeted `# type: ignore[...]` comments where third-party boundaries or test seams make that pragmatic.

## Fallback and Platform Behavior

`Must`

- Match the repo's fallback-oriented design. Missing desktop backends, optional UI dependencies, audio integration limits, or platform-specific capabilities should degrade safely instead of crashing the app.
- Keep fallback behavior explicit. If a feature becomes unavailable, either return a safe no-op object, choose a clearly defined fallback path, or surface an actionable error state.
- Preserve platform-aware behavior where it already exists, such as CPU defaults, Windows-specific keyboard injection, and optional Qt runtime selection.
- Keep platform checks and backend detection close to the boundary where they matter. Do not spread the same runtime decision across multiple unrelated modules.

`Prefer`

- Represent fallback decisions with named helpers or result objects instead of nested inline conditionals.
- Log enough information to diagnose the chosen fallback without overwhelming normal operation logs.
- Keep user-facing recovery behavior actionable. If something fails, prefer a message that helps the user recover rather than a vague silent fallback.

`Avoid`

- Do not add blocking work to tray callbacks, hotkey callbacks, or other latency-sensitive paths.
- Do not introduce broad silent fallbacks that hide a failure without logging or a defined safe outcome.
- Do not add placeholder branches, TODO-only implementations, or dead code paths to "prepare" for future work.
- Do not scatter runtime checks, backend selection rules, or environment parsing across the codebase.

## Testing

`Must`

- Add or update pytest coverage for behavior changes.
- Keep tests deterministic and readable.
- Prefer fakes, monkeypatching, and controlled stubs over real desktop hardware, GUI sessions, microphones, or platform APIs.
- Test fallback paths, failure behavior, and boundary conditions, not only the happy path.
- Keep production code strictly typed even if tests use more flexible scaffolding.

`Prefer`

- Follow repo naming conventions: `test_*.py` modules and `test_*` functions, with grouped `Test*` classes when they improve clarity.
- In tests, pragmatic seams are acceptable: `SimpleNamespace`, fake runtime classes, monkeypatching, and focused `type: ignore[...]` comments are fine when they keep platform-dependent behavior isolated.
- When behavior spans state transitions, test the published snapshot or result object rather than only checking incidental side effects.

## Definition of Done

`Must`

- The change matches the checked-in formatter, import-order, lint, type-check, security, secrets, and validation hooks.
- Relevant pytest coverage is updated for the behavior you changed.
- New code follows the preferred style in this document unless a local consistency concern makes a legacy pattern safer.

`Prefer`

- If you touch legacy code, move it toward the preferred style when the cleanup is low-risk and directly adjacent to your change.
- Do not perform repo-wide style churn unless the task explicitly calls for it.

When in doubt, optimize for typed code, small testable units, explicit subsystem boundaries, graceful degradation, and consistency with the strongest existing WhisperTray patterns.
