"""ExtensionManifest — typed, versioned extension declaration."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ── ABI version constants ─────────────────────────────────────────────────────

MANIFEST_ABI_V1                       = "aindy.extension.manifest/v1"
NODE_REGISTRATION_ABI_V1ALPHA1        = "aindy.extension.node-registration/v1alpha1"
WEBHOOK_REGISTRATION_ABI_V1ALPHA1     = "aindy.extension.webhook-registration/v1alpha1"
FLOW_REGISTRATION_ABI_V1ALPHA1        = "aindy.extension.flow-registration/v1alpha1"
AGENT_TOOL_REGISTRATION_ABI_V1ALPHA1  = "aindy.extension.agent-tool-registration/v1alpha1"
PLANNER_BACKEND_REGISTRATION_ABI_V1ALPHA1 = "aindy.extension.planner-backend-registration/v1alpha1"

SUPPORTED_ABI_VERSIONS: frozenset[str] = frozenset({
    MANIFEST_ABI_V1,
    NODE_REGISTRATION_ABI_V1ALPHA1,
    WEBHOOK_REGISTRATION_ABI_V1ALPHA1,
    FLOW_REGISTRATION_ABI_V1ALPHA1,
    AGENT_TOOL_REGISTRATION_ABI_V1ALPHA1,
    PLANNER_BACKEND_REGISTRATION_ABI_V1ALPHA1,
})

# ── Surface constants ─────────────────────────────────────────────────────────

SURFACE_MANIFEST      = "manifest"
SURFACE_DYNAMIC_NODE  = "dynamic-node-registration"
SURFACE_WEBHOOK       = "webhook-registration"
SURFACE_FLOW          = "flow-registration"
SURFACE_AGENT_TOOL    = "agent-tool-registration"
SURFACE_PLANNER       = "planner-backend-registration"

ALL_SURFACES: frozenset[str] = frozenset({
    SURFACE_MANIFEST, SURFACE_DYNAMIC_NODE, SURFACE_WEBHOOK,
    SURFACE_FLOW, SURFACE_AGENT_TOOL, SURFACE_PLANNER,
})

# ── Owner / trust classes ─────────────────────────────────────────────────────

OWNER_RUNTIME_BUILTIN    = "runtime-builtin"
OWNER_FIRST_PARTY_APP    = "first-party-app"
OWNER_EXTERNAL_THIRD_PARTY = "external-third-party"


class SandboxTier:
    INSECURE_DEV = "insecure_dev_subprocess"
    CONTAINER    = "containerized_oci"
    STRONG       = "strong_sandbox_vm"
    ALL = (INSECURE_DEV, CONTAINER, STRONG)


class ManifestValidationError(Exception):
    """Raised when an extension manifest fails validation."""


@dataclass
class ExtensionManifest:
    """Typed declaration of one Nodus extension.

    Attributes
    ----------
    name:          Unique extension name (e.g. ``"acme/slack-notifier"``).
    version:       SemVer string (e.g. ``"1.0.0"``).
    abi_version:   ABI version this manifest conforms to.
    surfaces:      List of surface IDs this extension registers against.
    owner_class:   One of the OWNER_* constants.
    sandbox_tier:  One of the ``SandboxTier`` constants.
    description:   Human-readable description.
    entry_point:   Optional Python importable (``"my_pkg.extension:setup"``).
    extra:         Extension-specific extra metadata.
    """

    name: str
    version: str
    abi_version: str
    surfaces: list[str] = field(default_factory=list)
    owner_class: str = OWNER_EXTERNAL_THIRD_PARTY
    sandbox_tier: str = SandboxTier.INSECURE_DEV
    description: str = ""
    entry_point: Optional[str] = None
    extra: dict = field(default_factory=dict)

    def validate(self) -> None:
        """Raise ``ManifestValidationError`` on any constraint violation."""
        if not self.name or not self.name.strip():
            raise ManifestValidationError("name is required")
        if not self.version or not self.version.strip():
            raise ManifestValidationError("version is required")
        if self.abi_version not in SUPPORTED_ABI_VERSIONS:
            raise ManifestValidationError(
                f"unsupported abi_version {self.abi_version!r}; "
                f"supported: {sorted(SUPPORTED_ABI_VERSIONS)}"
            )
        for surface in self.surfaces:
            if surface not in ALL_SURFACES:
                raise ManifestValidationError(
                    f"unknown surface {surface!r}; known: {sorted(ALL_SURFACES)}"
                )
        if self.sandbox_tier not in SandboxTier.ALL:
            raise ManifestValidationError(
                f"unknown sandbox_tier {self.sandbox_tier!r}; "
                f"valid: {SandboxTier.ALL}"
            )

    @classmethod
    def from_dict(cls, data: dict) -> "ExtensionManifest":
        """Deserialise from a plain dict (e.g. parsed JSON/YAML)."""
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)
