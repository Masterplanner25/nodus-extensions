"""nodus-extensions — typed, versioned, sandboxed extension loading for Nodus.

Manifest:
    ExtensionManifest      — typed extension declaration (name, version, abi, surfaces)
    ManifestValidationError — raised on invalid manifests
    SandboxTier            — INSECURE_DEV | CONTAINER | STRONG constants
    ABI version constants  — MANIFEST_ABI_V1, NODE_REGISTRATION_ABI_V1ALPHA1, etc.
    Surface constants      — SURFACE_MANIFEST, SURFACE_AGENT_TOOL, etc.
    Owner constants        — OWNER_RUNTIME_BUILTIN, OWNER_FIRST_PARTY_APP, etc.

Registry:
    ExtensionRegistry      — discover(), load(), get(), list_all(), unload()

Hooks:
    HookRunner             — register(), unregister(), run(phase, params)
    Phase constants        — PHASE_INIT, PHASE_BEFORE_AGENT_START, etc.

Sandbox:
    SandboxResult          — stdout, stderr, returncode, output, ok
    SandboxError           — raised on execution failure
    SubprocessSandboxRunner — insecure-dev tier (child process)
    OciSandboxRunner       — container-grade tier (Docker)
    make_runner(tier)      — factory for the appropriate runner

Provenance:
    ExtensionProvenance    — source, owner_class, trust_class, loaded_at
    ProvenanceInventory    — thread-safe registry of provenance records
    derive_trust_class()   — map owner_class → trust classification
"""
from .hooks import (
    ALL_PHASES,
    PHASE_AFTER_AGENT_END,
    PHASE_BEFORE_AGENT_START,
    PHASE_BEFORE_MODEL_RESOLVE,
    PHASE_INIT,
    PHASE_SHUTDOWN,
    HookRunner,
)
from .manifest import (
    AGENT_TOOL_REGISTRATION_ABI_V1ALPHA1,
    ALL_SURFACES,
    FLOW_REGISTRATION_ABI_V1ALPHA1,
    MANIFEST_ABI_V1,
    NODE_REGISTRATION_ABI_V1ALPHA1,
    OWNER_EXTERNAL_THIRD_PARTY,
    OWNER_FIRST_PARTY_APP,
    OWNER_RUNTIME_BUILTIN,
    PLANNER_BACKEND_REGISTRATION_ABI_V1ALPHA1,
    SURFACE_AGENT_TOOL,
    SURFACE_DYNAMIC_NODE,
    SURFACE_FLOW,
    SURFACE_MANIFEST,
    SURFACE_PLANNER,
    SURFACE_WEBHOOK,
    SUPPORTED_ABI_VERSIONS,
    WEBHOOK_REGISTRATION_ABI_V1ALPHA1,
    ExtensionManifest,
    ManifestValidationError,
    SandboxTier,
)
from .provenance import (
    ExtensionProvenance,
    ProvenanceInventory,
    derive_trust_class,
)
from .registry import ExtensionRegistry
from .sandbox import (
    OciSandboxRunner,
    SandboxError,
    SandboxResult,
    SubprocessSandboxRunner,
    make_runner,
)

__all__ = [
    # Manifest
    "ExtensionManifest",
    "ManifestValidationError",
    "SandboxTier",
    "MANIFEST_ABI_V1",
    "NODE_REGISTRATION_ABI_V1ALPHA1",
    "WEBHOOK_REGISTRATION_ABI_V1ALPHA1",
    "FLOW_REGISTRATION_ABI_V1ALPHA1",
    "AGENT_TOOL_REGISTRATION_ABI_V1ALPHA1",
    "PLANNER_BACKEND_REGISTRATION_ABI_V1ALPHA1",
    "SUPPORTED_ABI_VERSIONS",
    "ALL_SURFACES",
    "SURFACE_MANIFEST",
    "SURFACE_DYNAMIC_NODE",
    "SURFACE_WEBHOOK",
    "SURFACE_FLOW",
    "SURFACE_AGENT_TOOL",
    "SURFACE_PLANNER",
    "OWNER_RUNTIME_BUILTIN",
    "OWNER_FIRST_PARTY_APP",
    "OWNER_EXTERNAL_THIRD_PARTY",
    # Registry
    "ExtensionRegistry",
    # Hooks
    "HookRunner",
    "PHASE_INIT",
    "PHASE_BEFORE_AGENT_START",
    "PHASE_BEFORE_MODEL_RESOLVE",
    "PHASE_AFTER_AGENT_END",
    "PHASE_SHUTDOWN",
    "ALL_PHASES",
    # Sandbox
    "SandboxResult",
    "SandboxError",
    "SubprocessSandboxRunner",
    "OciSandboxRunner",
    "make_runner",
    # Provenance
    "ExtensionProvenance",
    "ProvenanceInventory",
    "derive_trust_class",
]
