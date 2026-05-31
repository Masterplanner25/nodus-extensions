# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

---

## [0.1.0] — 2026-05-30

Initial release — prepared, not yet published.

### Added

- **`ExtensionManifest`** — typed extension declaration. Fields: `name`,
  `version`, `description`, `abi_version`, `sandbox_tier`, `surfaces`,
  `capabilities`. Validates on construction; raises `ManifestValidationError`
  on invalid fields.

- **ABI version constants** — `MANIFEST_ABI_V1`, `NODE_REGISTRATION_ABI_V1ALPHA1`,
  `WEBHOOK_REGISTRATION_ABI_V1ALPHA1`, `FLOW_REGISTRATION_ABI_V1ALPHA1`,
  `AGENT_TOOL_REGISTRATION_ABI_V1ALPHA1`, `PLANNER_BACKEND_REGISTRATION_ABI_V1ALPHA1`,
  `SUPPORTED_ABI_VERSIONS`, `ALL_SURFACES`.

- **Surface constants** — `SURFACE_MANIFEST`, `SURFACE_DYNAMIC_NODE`,
  `SURFACE_WEBHOOK`, `SURFACE_FLOW`, `SURFACE_AGENT_TOOL`, `SURFACE_PLANNER`.

- **Owner constants** — `OWNER_RUNTIME_BUILTIN`, `OWNER_FIRST_PARTY_APP`,
  `OWNER_EXTERNAL_THIRD_PARTY`.

- **`SandboxTier`** — `INSECURE_DEV` | `CONTAINER` | `STRONG` enum.

- **`ExtensionRegistry`** — disk-discovery registry. `discover(path)` scans
  a directory tree for `nodus-extension.json` files. `load(path)`,
  `get(name)`, `list_all()`, `unload(name)`. Thread-safe.

- **`HookRunner`** — phase hook lifecycle. `register(phase, name, fn)`,
  `unregister(phase, name)`, `run(phase, params)` (async-aware).
  Phase constants: `PHASE_INIT`, `PHASE_BEFORE_AGENT_START`,
  `PHASE_BEFORE_MODEL_RESOLVE`, `PHASE_AFTER_AGENT_END`, `PHASE_SHUTDOWN`,
  `ALL_PHASES`.

- **`SubprocessSandboxRunner`** — insecure-dev tier. Spawns extension code as
  a child process; communicates via JSON over stdin/stdout. Returns
  `SandboxResult`.

- **`OciSandboxRunner`** — container-grade tier. Runs extension in a Docker
  container. Requires Docker daemon.

- **`make_runner(tier)`** — factory returning the appropriate runner for a
  `SandboxTier`.

- **`SandboxResult`** — `stdout`, `stderr`, `returncode`, `output` (parsed),
  `ok` (bool).

- **`ExtensionProvenance`** — source, owner_class, trust_class, loaded_at.

- **`ProvenanceInventory`** — thread-safe registry. `record`, `get`,
  `list_all`.

- **`derive_trust_class(owner_class)`** — maps owner class string to trust
  classification.

- **35 tests** in `tests/test_extensions.py`. Uses `asyncio.run()` (not
  deprecated `get_event_loop().run_until_complete()`).

- **No required dependencies** — pure stdlib.

[0.1.0]: https://github.com/Masterplanner25/nodus-extensions/releases/tag/v0.1.0
