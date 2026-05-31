"""ExtensionRegistry — discover, validate, and register extensions."""
from __future__ import annotations

import importlib
import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Callable, Optional

from .manifest import ExtensionManifest, ManifestValidationError
from .provenance import ExtensionProvenance, ProvenanceInventory, derive_trust_class

logger = logging.getLogger(__name__)

_MANIFEST_FILENAMES = ("extension.json", "manifest.json", "nodus_extension.json")

LoadHook = Callable[[ExtensionManifest], None]


class ExtensionRegistry:
    """Discover, validate, and register Nodus extensions.

    Extensions are loaded from directories on disk.  Each extension directory
    must contain a manifest file (``extension.json``, ``manifest.json``, or
    ``nodus_extension.json``).

    Usage::

        registry = ExtensionRegistry()
        manifests = registry.discover(["/opt/nodus/extensions", "~/.nodus/plugins"])
        for manifest in manifests:
            registry.load(manifest)

        # Access registered hooks
        hooks = registry.get_hooks("before_agent_start")
    """

    def __init__(
        self,
        *,
        hook_runner=None,     # Optional HookRunner (duck-typed)
        provenance: Optional[ProvenanceInventory] = None,
        on_load: Optional[LoadHook] = None,
    ) -> None:
        self._manifests: dict[str, ExtensionManifest] = {}
        self._hooks = hook_runner
        self._provenance = provenance or ProvenanceInventory()
        self._on_load = on_load
        self._lock = threading.Lock()

    def discover(self, paths: list[str]) -> list[ExtensionManifest]:
        """Scan *paths* for extension manifests and return validated manifests.

        Skips invalid manifests with a warning rather than raising.
        """
        found: list[ExtensionManifest] = []
        for base in paths:
            expanded = os.path.expanduser(base)
            if not os.path.isdir(expanded):
                continue
            for entry in os.scandir(expanded):
                if not entry.is_dir():
                    continue
                manifest = self._load_manifest_from_dir(entry.path)
                if manifest is not None:
                    found.append(manifest)
        return found

    def _load_manifest_from_dir(self, dirpath: str) -> Optional[ExtensionManifest]:
        for filename in _MANIFEST_FILENAMES:
            candidate = os.path.join(dirpath, filename)
            if os.path.isfile(candidate):
                try:
                    with open(candidate) as f:
                        data = json.load(f)
                    manifest = ExtensionManifest.from_dict(data)
                    manifest.validate()
                    return manifest
                except (json.JSONDecodeError, ManifestValidationError, Exception) as exc:
                    logger.warning("[ExtensionRegistry] skipping %s: %s", candidate, exc)
        return None

    def load(
        self,
        manifest: ExtensionManifest,
        *,
        source: str = "unknown",
        loaded_by: Optional[str] = None,
    ) -> None:
        """Validate and register an extension manifest.

        If the manifest has an ``entry_point``, the module is imported and
        an optional ``setup(hook_runner)`` function is called.

        Raises:
            ManifestValidationError: If the manifest is invalid.
        """
        manifest.validate()

        with self._lock:
            self._manifests[manifest.name] = manifest

        # Record provenance
        prov = ExtensionProvenance(
            extension_name=manifest.name,
            source=source,
            owner_class=manifest.owner_class,
            trust_class=derive_trust_class(manifest),
            loaded_by=loaded_by,
        )
        self._provenance.record(prov)

        # Import entry point if provided
        if manifest.entry_point:
            self._import_entry_point(manifest)

        if self._on_load is not None:
            try:
                self._on_load(manifest)
            except Exception as exc:
                logger.warning("[ExtensionRegistry] on_load callback failed: %s", exc)

        logger.info("[ExtensionRegistry] loaded %s v%s", manifest.name, manifest.version)

    def _import_entry_point(self, manifest: ExtensionManifest) -> None:
        """Import ``module:function`` and call it with the hook runner."""
        ep = manifest.entry_point or ""
        if ":" in ep:
            module_path, fn_name = ep.rsplit(":", 1)
        else:
            module_path, fn_name = ep, "setup"
        try:
            mod = importlib.import_module(module_path)
            fn = getattr(mod, fn_name, None)
            if fn is not None and self._hooks is not None:
                fn(self._hooks)
        except Exception as exc:
            logger.warning("[ExtensionRegistry] entry_point %s failed: %s", ep, exc)

    def get(self, name: str) -> Optional[ExtensionManifest]:
        with self._lock:
            return self._manifests.get(name)

    def list_all(self, *, owner_class: Optional[str] = None) -> list[ExtensionManifest]:
        with self._lock:
            manifests = list(self._manifests.values())
        if owner_class is not None:
            manifests = [m for m in manifests if m.owner_class == owner_class]
        return manifests

    def unload(self, name: str) -> bool:
        """Unload an extension. Returns True if it was registered."""
        with self._lock:
            removed = self._manifests.pop(name, None)
        if removed is not None and self._hooks is not None:
            try:
                self._hooks.unregister(name)
            except Exception:
                pass
        return removed is not None

    def provenance(self, name: str) -> Optional[ExtensionProvenance]:
        return self._provenance.get(name)

    def __len__(self) -> int:
        with self._lock:
            return len(self._manifests)

    def __contains__(self, name: str) -> bool:
        with self._lock:
            return name in self._manifests
