# Contributing to nodus-extensions

## Note on naming

This is `nodus-extensions` (plural) — not `nodus-extension` (singular).
See the README for the distinction.

## Setup

```bash
git clone https://github.com/Masterplanner25/nodus-extensions.git
cd nodus-extensions
pip install -e ".[dev]"
```

## Running tests

```bash
pytest tests/ -q
```

Tests use `asyncio.run()` — do not use `asyncio.get_event_loop().run_until_complete()`
(deprecated in Python 3.10+, raises in strict mode on 3.12+).

## Code style

- Python 3.11+
- No required external dependencies (stdlib only)
- `asyncio.run()` for sync test wrappers around async hooks
- `SandboxTier` is an explicit enum — not a string flag

## Submitting changes

1. Fork the repo and create a branch from `main`
2. Add tests for any new behaviour
3. Ensure `pytest tests/ -q` passes
4. Open a pull request with a description of what changes and why
