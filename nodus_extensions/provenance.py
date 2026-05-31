"""ExtensionProvenance — origin, trust class, and owner tracking."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .manifest import ExtensionManifest


@dataclass
class ExtensionProvenance:
    """Tracks where an extension came from and its trust classification.

    Attributes
    ----------
    extension_name:  Matches ``ExtensionManifest.name``.
    source:          Where this extension was loaded from (path, npm, URL).
    owner_class:     Inherited from manifest.
    trust_class:     Derived classification (``"trusted"`` | ``"sandboxed"`` | ``"untrusted"``).
    loaded_at:       UTC timestamp when the extension was registered.
    loaded_by:       Identity of the operator who authorised loading.
    """

    extension_name: str
    source: str
    owner_class: str
    trust_class: str
    loaded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    loaded_by: Optional[str] = None


def derive_trust_class(manifest: ExtensionManifest) -> str:
    """Derive a trust classification from a manifest's owner_class."""
    from .manifest import OWNER_RUNTIME_BUILTIN, OWNER_FIRST_PARTY_APP  # noqa: PLC0415
    if manifest.owner_class == OWNER_RUNTIME_BUILTIN:
        return "trusted"
    if manifest.owner_class == OWNER_FIRST_PARTY_APP:
        return "sandboxed"
    return "untrusted"


class ProvenanceInventory:
    """Thread-safe registry of extension provenance records."""

    def __init__(self) -> None:
        self._records: dict[str, ExtensionProvenance] = {}
        self._lock = threading.Lock()

    def record(self, provenance: ExtensionProvenance) -> None:
        with self._lock:
            self._records[provenance.extension_name] = provenance

    def get(self, extension_name: str) -> Optional[ExtensionProvenance]:
        with self._lock:
            return self._records.get(extension_name)

    def list_all(self) -> list[ExtensionProvenance]:
        with self._lock:
            return list(self._records.values())

    def __len__(self) -> int:
        with self._lock:
            return len(self._records)
