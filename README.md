# nodus-extensions

**Typed, versioned, sandboxed extension loading for Nodus AI systems.**

Provides ABI versioning constants, a hook lifecycle runner, subprocess and OCI
sandbox runners, disk-discovery extension registry, and a provenance inventory.
No required external dependencies — pure stdlib.

> **Note on naming:** This package (`nodus-extensions`, plural) is distinct from
> [`nodus-extension`](https://github.com/Masterplanner25/nodus-extension) (singular).
> `nodus-extension` is the nodus-lang companion that provides `.nd` script bindings
> (`import "nodus-extension"`). This package is a standalone Tier 4 library for
> building extension-hosting platforms in Python.

> **Status:** v0.1.0 — prepared, not yet published.

---

## Install

```bash
pip install nodus-extensions
```

---

## What it provides

| Component | Purpose |
|---|---|
| `ExtensionManifest` | Typed extension declaration (name, version, ABI, surfaces) |
| `ExtensionRegistry` | Disk-discovery registry: `discover()`, `load()`, `get()`, `list_all()` |
| `HookRunner` | Phase hook lifecycle: register, unregister, run |
| `SubprocessSandboxRunner` | Insecure-dev tier: runs extensions as child processes |
| `OciSandboxRunner` | Container-grade tier: runs extensions via Docker |
| `make_runner(tier)` | Factory for the appropriate sandbox runner |
| `ExtensionProvenance` / `ProvenanceInventory` | Source, trust class, load time tracking |

---

## ExtensionManifest

```python
from nodus_extensions import (
    ExtensionManifest, SandboxTier,
    MANIFEST_ABI_V1, AGENT_TOOL_REGISTRATION_ABI_V1ALPHA1,
    SURFACE_AGENT_TOOL, OWNER_EXTERNAL_THIRD_PARTY,
)

manifest = ExtensionManifest(
    name="myapp.greet-extension",
    version="1.0.0",
    description="Greets users",
    abi_version=MANIFEST_ABI_V1,
    sandbox_tier=SandboxTier.INSECURE_DEV,
    surfaces=[SURFACE_AGENT_TOOL],
    capabilities=["tool.invoke"],
)
```

### ABI version constants

| Constant | Value | Surface |
|---|---|---|
| `MANIFEST_ABI_V1` | `"v1"` | Manifest schema |
| `NODE_REGISTRATION_ABI_V1ALPHA1` | `"v1alpha1"` | Dynamic nodes |
| `WEBHOOK_REGISTRATION_ABI_V1ALPHA1` | `"v1alpha1"` | Webhooks |
| `FLOW_REGISTRATION_ABI_V1ALPHA1` | `"v1alpha1"` | Flows |
| `AGENT_TOOL_REGISTRATION_ABI_V1ALPHA1` | `"v1alpha1"` | Agent tools |
| `PLANNER_BACKEND_REGISTRATION_ABI_V1ALPHA1` | `"v1alpha1"` | Planner backends |

---

## ExtensionRegistry

```python
from nodus_extensions import ExtensionRegistry

registry = ExtensionRegistry()
registry.discover("/path/to/extensions/")   # scans for nodus-extension.json files
registry.load("/path/to/specific-ext/")     # load one extension dir

ext = registry.get("myapp.greet-extension")  # ExtensionManifest | None
all_exts = registry.list_all()               # list[ExtensionManifest]
registry.unload("myapp.greet-extension")
```

---

## HookRunner

```python
from nodus_extensions import (
    HookRunner,
    PHASE_INIT, PHASE_BEFORE_AGENT_START,
    PHASE_BEFORE_MODEL_RESOLVE, PHASE_AFTER_AGENT_END, PHASE_SHUTDOWN,
)

runner = HookRunner()

def my_init_hook(params: dict) -> None:
    print("Initialising:", params)

runner.register(PHASE_INIT, "my-hook", my_init_hook)
await runner.run(PHASE_INIT, {"context": "startup"})
runner.unregister(PHASE_INIT, "my-hook")
```

Hooks are `async`-aware — sync hooks are called directly; async hooks are
awaited. All hooks for a phase run in registration order.

---

## Sandbox runners

```python
from nodus_extensions import SubprocessSandboxRunner, OciSandboxRunner, make_runner, SandboxTier

# Subprocess (insecure-dev — same OS user as host)
runner = SubprocessSandboxRunner()
result = runner.run("python3 extension.py", input_data={"tool": "greet", "args": {}})
# result.ok, result.stdout, result.stderr, result.returncode, result.output

# OCI container (Docker required)
runner = OciSandboxRunner(image="myapp/greet-extension:1.0")
result = runner.run("python3 extension.py", input_data={...})

# Factory
runner = make_runner(SandboxTier.INSECURE_DEV)
runner = make_runner(SandboxTier.CONTAINER)
```

---

## Provenance

```python
from nodus_extensions import ExtensionProvenance, ProvenanceInventory, derive_trust_class

inventory = ProvenanceInventory()
prov = ExtensionProvenance(
    name="myapp.greet-extension",
    source="local",
    owner_class="personal",
    trust_class=derive_trust_class("personal"),
)
inventory.record(prov)

all_prov = inventory.list_all()
entry = inventory.get("myapp.greet-extension")
```

---

## Design

- **No required dependencies.** Pure stdlib (`asyncio`, `threading`,
  `subprocess`, `importlib`, `pathlib`, `json`, `logging`).
- **Thread-safe.** `ExtensionRegistry` and `ProvenanceInventory` use
  `threading.Lock`.
- **Sandbox tiers are explicit.** `SandboxTier.INSECURE_DEV` (subprocess)
  and `SandboxTier.CONTAINER` (OCI) are named constants, not flags.

---

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -q
```

---

## License

MIT — see [LICENSE](LICENSE).
