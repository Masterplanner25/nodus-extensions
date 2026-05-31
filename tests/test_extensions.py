"""nodus-extensions tests."""
import asyncio
import json
import os
import tempfile

import pytest

from nodus_extensions import (
    ALL_PHASES,
    AGENT_TOOL_REGISTRATION_ABI_V1ALPHA1,
    MANIFEST_ABI_V1,
    OWNER_EXTERNAL_THIRD_PARTY,
    OWNER_FIRST_PARTY_APP,
    OWNER_RUNTIME_BUILTIN,
    PHASE_BEFORE_AGENT_START,
    PHASE_BEFORE_MODEL_RESOLVE,
    PHASE_INIT,
    SURFACE_AGENT_TOOL,
    SURFACE_MANIFEST,
    ExtensionManifest,
    ExtensionRegistry,
    HookRunner,
    ManifestValidationError,
    OciSandboxRunner,
    ProvenanceInventory,
    SandboxError,
    SandboxTier,
    SubprocessSandboxRunner,
    derive_trust_class,
    make_runner,
)


def _valid_manifest(**overrides):
    defaults = dict(
        name="test/extension",
        version="1.0.0",
        abi_version=MANIFEST_ABI_V1,
        surfaces=[SURFACE_MANIFEST],
        owner_class=OWNER_EXTERNAL_THIRD_PARTY,
        sandbox_tier=SandboxTier.INSECURE_DEV,
    )
    defaults.update(overrides)
    return ExtensionManifest(**defaults)


# ── ExtensionManifest ─────────────────────────────────────────────────────────

def test_manifest_validate_passes():
    m = _valid_manifest()
    m.validate()   # should not raise


def test_manifest_validate_no_name_raises():
    m = _valid_manifest(name="")
    with pytest.raises(ManifestValidationError, match="name"):
        m.validate()


def test_manifest_validate_bad_abi_raises():
    m = _valid_manifest(abi_version="unknown/v99")
    with pytest.raises(ManifestValidationError, match="abi_version"):
        m.validate()


def test_manifest_validate_bad_surface_raises():
    m = _valid_manifest(surfaces=["not-a-surface"])
    with pytest.raises(ManifestValidationError, match="surface"):
        m.validate()


def test_manifest_validate_bad_sandbox_tier_raises():
    m = _valid_manifest(sandbox_tier="teleporter")
    with pytest.raises(ManifestValidationError, match="sandbox_tier"):
        m.validate()


def test_manifest_from_dict():
    data = {
        "name": "my/ext", "version": "2.0.0",
        "abi_version": MANIFEST_ABI_V1,
        "surfaces": [SURFACE_AGENT_TOOL],
        "owner_class": OWNER_FIRST_PARTY_APP,
        "sandbox_tier": SandboxTier.INSECURE_DEV,
    }
    m = ExtensionManifest.from_dict(data)
    assert m.name == "my/ext"
    assert SURFACE_AGENT_TOOL in m.surfaces


def test_manifest_from_dict_ignores_unknown_fields():
    data = {
        "name": "x", "version": "1.0", "abi_version": MANIFEST_ABI_V1,
        "completely_unknown_field": "ignored",
    }
    m = ExtensionManifest.from_dict(data)   # should not raise
    assert m.name == "x"


# ── HookRunner ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_hook_runner_register_and_run():
    runner = HookRunner()
    called = []
    runner.register(PHASE_INIT, lambda p: called.append(p) or "result",
                    extension_id="ext-1")
    results = await runner.run(PHASE_INIT, {"key": "value"})
    assert len(results) == 1
    assert results[0] == "result"
    assert called[0]["key"] == "value"


@pytest.mark.asyncio
async def test_hook_runner_first_match_semantics():
    runner = HookRunner()
    runner.register(PHASE_BEFORE_MODEL_RESOLVE, lambda p: "first-override",
                    extension_id="ext-1", priority=0)
    runner.register(PHASE_BEFORE_MODEL_RESOLVE, lambda p: "second-override",
                    extension_id="ext-2", priority=1)
    results = await runner.run(PHASE_BEFORE_MODEL_RESOLVE, {})
    assert len(results) == 1    # first-match — only one result
    assert results[0] == "first-override"


@pytest.mark.asyncio
async def test_hook_runner_notification_calls_all():
    runner = HookRunner()
    results_store = []
    runner.register(PHASE_INIT, lambda p: results_store.append("h1") or "r1", extension_id="e1")
    runner.register(PHASE_INIT, lambda p: results_store.append("h2") or "r2", extension_id="e2")
    results = await runner.run(PHASE_INIT, {})
    assert len(results) == 2    # notification phase — all called
    assert "h1" in results_store and "h2" in results_store


@pytest.mark.asyncio
async def test_hook_runner_exception_does_not_stop_others():
    runner = HookRunner()
    def bad(p): raise RuntimeError("hook failure")
    def good(p): return "good"
    runner.register(PHASE_INIT, bad, extension_id="bad", priority=0)
    runner.register(PHASE_INIT, good, extension_id="good", priority=1)
    results = await runner.run(PHASE_INIT, {})
    assert "good" in results


@pytest.mark.asyncio
async def test_hook_runner_returns_none_hook_skipped():
    runner = HookRunner()
    runner.register(PHASE_INIT, lambda p: None, extension_id="noop")
    results = await runner.run(PHASE_INIT, {})
    assert results == []


def test_hook_runner_unregister():
    runner = HookRunner()
    runner.register(PHASE_INIT, lambda p: "r", extension_id="ext-1")
    removed = runner.unregister("ext-1")
    assert removed == 1
    assert runner.hook_count(PHASE_INIT) == 0


def test_hook_runner_priority_order():
    runner = HookRunner()
    order = []
    runner.register(PHASE_INIT, lambda p: order.append("b") or None, extension_id="b", priority=2)
    runner.register(PHASE_INIT, lambda p: order.append("a") or None, extension_id="a", priority=0)
    runner.register(PHASE_INIT, lambda p: order.append("c") or None, extension_id="c", priority=1)
    asyncio.run(runner.run(PHASE_INIT, {}))
    assert order == ["a", "c", "b"]


@pytest.mark.asyncio
async def test_hook_runner_async_hook():
    runner = HookRunner()
    async def async_hook(p): return "async-result"
    runner.register(PHASE_INIT, async_hook, extension_id="ext-async")
    results = await runner.run(PHASE_INIT, {})
    assert results == ["async-result"]


# ── SubprocessSandboxRunner ───────────────────────────────────────────────────

def test_subprocess_runner_simple_echo():
    runner = SubprocessSandboxRunner(timeout_seconds=10)
    result = runner.run_code(
        'import sys, json; print(json.dumps({"ok": True}))'
    )
    assert result.ok is True
    assert result.output == {"ok": True}


def test_subprocess_runner_exit_nonzero():
    runner = SubprocessSandboxRunner(timeout_seconds=5)
    result = runner.run_code("import sys; sys.exit(1)")
    assert result.ok is False
    assert result.returncode == 1


def test_subprocess_runner_reads_input():
    runner = SubprocessSandboxRunner(timeout_seconds=5)
    result = runner.run_code(
        'import sys, json; data = json.loads(sys.stdin.read()); print(json.dumps({"received": data}))',
        input_data={"x": 42},
    )
    assert result.ok is True
    assert result.output["received"]["x"] == 42


def test_subprocess_runner_timeout():
    runner = SubprocessSandboxRunner(timeout_seconds=1)
    with pytest.raises(SandboxError, match="timed out"):
        runner.run_code("import time; time.sleep(999)")


def test_subprocess_run_file():
    runner = SubprocessSandboxRunner(timeout_seconds=5)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write('import json; print(json.dumps({"from": "file"}))\n')
        tmppath = f.name
    try:
        result = runner.run_file(tmppath)
        assert result.ok is True
        assert result.output["from"] == "file"
    finally:
        os.unlink(tmppath)


def test_make_runner_subprocess():
    r = make_runner(SandboxTier.INSECURE_DEV)
    assert isinstance(r, SubprocessSandboxRunner)


def test_make_runner_oci():
    r = make_runner(SandboxTier.CONTAINER)
    assert isinstance(r, OciSandboxRunner)


def test_make_runner_invalid_raises():
    with pytest.raises(ValueError):
        make_runner("teleporter")


# ── Provenance ────────────────────────────────────────────────────────────────

def test_derive_trust_class_runtime_builtin():
    m = _valid_manifest(owner_class=OWNER_RUNTIME_BUILTIN)
    assert derive_trust_class(m) == "trusted"


def test_derive_trust_class_first_party():
    m = _valid_manifest(owner_class=OWNER_FIRST_PARTY_APP)
    assert derive_trust_class(m) == "sandboxed"


def test_derive_trust_class_external():
    m = _valid_manifest(owner_class=OWNER_EXTERNAL_THIRD_PARTY)
    assert derive_trust_class(m) == "untrusted"


def test_provenance_inventory_record_and_get():
    inv = ProvenanceInventory()
    from nodus_extensions import ExtensionProvenance
    p = ExtensionProvenance(
        extension_name="test/ext",
        source="/path/to/ext",
        owner_class=OWNER_FIRST_PARTY_APP,
        trust_class="sandboxed",
    )
    inv.record(p)
    assert inv.get("test/ext") is p
    assert len(inv) == 1


# ── ExtensionRegistry ─────────────────────────────────────────────────────────

def test_registry_load_and_get():
    reg = ExtensionRegistry()
    m = _valid_manifest()
    reg.load(m, source="test")
    assert reg.get("test/extension") is m
    assert len(reg) == 1
    assert "test/extension" in reg


def test_registry_load_invalid_raises():
    reg = ExtensionRegistry()
    m = _valid_manifest(name="")    # invalid
    with pytest.raises(ManifestValidationError):
        reg.load(m)


def test_registry_unload():
    reg = ExtensionRegistry()
    m = _valid_manifest()
    reg.load(m)
    assert reg.unload("test/extension") is True
    assert reg.get("test/extension") is None
    assert reg.unload("test/extension") is False


def test_registry_list_all():
    reg = ExtensionRegistry()
    reg.load(_valid_manifest(name="a/ext", owner_class=OWNER_RUNTIME_BUILTIN))
    reg.load(_valid_manifest(name="b/ext", owner_class=OWNER_FIRST_PARTY_APP))
    all_m = reg.list_all()
    assert len(all_m) == 2


def test_registry_list_by_owner():
    reg = ExtensionRegistry()
    reg.load(_valid_manifest(name="a/ext", owner_class=OWNER_RUNTIME_BUILTIN))
    reg.load(_valid_manifest(name="b/ext", owner_class=OWNER_FIRST_PARTY_APP))
    builtin = reg.list_all(owner_class=OWNER_RUNTIME_BUILTIN)
    assert len(builtin) == 1
    assert builtin[0].name == "a/ext"


def test_registry_provenance_recorded():
    reg = ExtensionRegistry()
    reg.load(_valid_manifest(), source="/my/path", loaded_by="operator-1")
    prov = reg.provenance("test/extension")
    assert prov is not None
    assert prov.source == "/my/path"
    assert prov.loaded_by == "operator-1"


def test_registry_discover_from_disk():
    reg = ExtensionRegistry()
    with tempfile.TemporaryDirectory() as tmpdir:
        ext_dir = os.path.join(tmpdir, "my_extension")
        os.makedirs(ext_dir)
        manifest_data = {
            "name": "test/discovered",
            "version": "1.0.0",
            "abi_version": MANIFEST_ABI_V1,
            "surfaces": [SURFACE_MANIFEST],
        }
        with open(os.path.join(ext_dir, "extension.json"), "w") as f:
            json.dump(manifest_data, f)

        manifests = reg.discover([tmpdir])
        assert len(manifests) == 1
        assert manifests[0].name == "test/discovered"


def test_registry_discover_skips_invalid_manifests():
    reg = ExtensionRegistry()
    with tempfile.TemporaryDirectory() as tmpdir:
        ext_dir = os.path.join(tmpdir, "bad_ext")
        os.makedirs(ext_dir)
        with open(os.path.join(ext_dir, "extension.json"), "w") as f:
            f.write("not valid json{{")

        manifests = reg.discover([tmpdir])
        assert len(manifests) == 0   # skipped, no exception
