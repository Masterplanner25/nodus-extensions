"""SandboxRunner — execute extension code in an isolated environment."""
from __future__ import annotations

import json
import logging
import subprocess
import sys
import tempfile
from typing import Any, Optional

from .manifest import SandboxTier

logger = logging.getLogger(__name__)


class SandboxError(Exception):
    """Raised when sandbox execution fails."""


class SandboxResult:
    """Result of one sandbox execution."""

    def __init__(self, stdout: str, stderr: str, returncode: int) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.output: Optional[Any] = None

        # Try to parse stdout as JSON
        if stdout.strip():
            try:
                self.output = json.loads(stdout.strip())
            except json.JSONDecodeError:
                self.output = stdout.strip()

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class SubprocessSandboxRunner:
    """Run extension code in a child subprocess (insecure-dev tier).

    Suitable for trusted internal extensions only.  Provides no meaningful
    isolation — the child process has the same OS permissions as the parent.

    Args:
        timeout_seconds: Maximum wall-clock time (default: 10s).
        python_executable: Python interpreter to use (default: current).
    """

    def __init__(
        self,
        *,
        timeout_seconds: int = 10,
        python_executable: Optional[str] = None,
    ) -> None:
        self._timeout = timeout_seconds
        self._python = python_executable or sys.executable

    def run_code(
        self,
        code: str,
        *,
        input_data: Optional[dict] = None,
        env: Optional[dict] = None,
    ) -> SandboxResult:
        """Execute *code* in a subprocess.

        The script receives ``input_data`` via stdin as JSON and should write
        its result to stdout as JSON.

        Args:
            code:       Python source code to execute.
            input_data: Optional dict passed to the script via stdin.
            env:        Optional environment variable overrides.

        Returns:
            ``SandboxResult`` with stdout/stderr/returncode and parsed output.
        """
        import os  # noqa: PLC0415
        run_env = dict(os.environ)
        if env:
            run_env.update(env)

        stdin_data = json.dumps(input_data or {}).encode()

        try:
            proc = subprocess.run(
                [self._python, "-c", code],
                input=stdin_data,
                capture_output=True,
                timeout=self._timeout,
                env=run_env,
            )
            return SandboxResult(
                stdout=proc.stdout.decode("utf-8", errors="replace"),
                stderr=proc.stderr.decode("utf-8", errors="replace"),
                returncode=proc.returncode,
            )
        except subprocess.TimeoutExpired as exc:
            raise SandboxError(
                f"Subprocess timed out after {self._timeout}s"
            ) from exc
        except Exception as exc:
            raise SandboxError(f"Subprocess failed: {exc}") from exc

    def run_file(
        self,
        path: str,
        *,
        input_data: Optional[dict] = None,
        env: Optional[dict] = None,
    ) -> SandboxResult:
        """Execute a Python file path in a subprocess."""
        import os  # noqa: PLC0415
        run_env = dict(os.environ)
        if env:
            run_env.update(env)
        stdin_data = json.dumps(input_data or {}).encode()
        try:
            proc = subprocess.run(
                [self._python, path],
                input=stdin_data,
                capture_output=True,
                timeout=self._timeout,
                env=run_env,
            )
            return SandboxResult(
                stdout=proc.stdout.decode("utf-8", errors="replace"),
                stderr=proc.stderr.decode("utf-8", errors="replace"),
                returncode=proc.returncode,
            )
        except subprocess.TimeoutExpired as exc:
            raise SandboxError(f"Script timed out after {self._timeout}s") from exc


class OciSandboxRunner:
    """Run extension code inside a container (container-grade tier).

    Requires Docker or a compatible OCI runtime.

    Args:
        image:     Container image to use.
        timeout_seconds: Maximum wall-clock time.
    """

    def __init__(self, image: str = "python:3.11-slim", timeout_seconds: int = 30) -> None:
        self._image = image
        self._timeout = timeout_seconds

    def run_code(self, code: str, *, input_data: Optional[dict] = None, **kwargs) -> SandboxResult:
        """Run *code* inside a container.  Raises SandboxError if Docker unavailable."""
        import shutil  # noqa: PLC0415
        if not shutil.which("docker"):
            raise SandboxError("Docker not found — OCI sandbox unavailable")

        stdin_data = json.dumps(input_data or {}).encode()
        try:
            proc = subprocess.run(
                ["docker", "run", "--rm", "-i",
                 "--cap-drop", "ALL",
                 "--security-opt", "no-new-privileges",
                 "--network", "none",
                 self._image,
                 "python3", "-c", code],
                input=stdin_data,
                capture_output=True,
                timeout=self._timeout,
            )
            return SandboxResult(
                stdout=proc.stdout.decode("utf-8", errors="replace"),
                stderr=proc.stderr.decode("utf-8", errors="replace"),
                returncode=proc.returncode,
            )
        except subprocess.TimeoutExpired as exc:
            raise SandboxError(f"Container timed out after {self._timeout}s") from exc
        except FileNotFoundError as exc:
            raise SandboxError("docker not found") from exc


def make_runner(tier: str, **kwargs) -> "SubprocessSandboxRunner | OciSandboxRunner":
    """Factory: return the appropriate runner for *tier*."""
    if tier == SandboxTier.INSECURE_DEV:
        return SubprocessSandboxRunner(**kwargs)
    if tier == SandboxTier.CONTAINER:
        return OciSandboxRunner(**kwargs)
    raise ValueError(
        f"Unsupported sandbox tier: {tier!r}. "
        f"Strong-sandbox VM requires external infrastructure."
    )
