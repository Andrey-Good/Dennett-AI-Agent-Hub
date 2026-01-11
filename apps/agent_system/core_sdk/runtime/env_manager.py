from __future__ import annotations

import os
import json
import hashlib
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class EnvInfo:
    env_hash: str
    venv_path: Path
    python_executable: Path
    ready: bool


class EnvironmentManager:
    """Управляет uv-окружениями для плагинов."""

    def __init__(self, venvs_root: Path, sdk_version: str = "0.1.0"):
        self.venvs_root = venvs_root
        self.sdk_version = sdk_version
        self.venvs_root.mkdir(parents=True, exist_ok=True)

    def compute_env_hash(
        self,
        python_deps: List[str],
        python_version: str = "3.12",
        platform: str = "linux",
        arch: str = "x64",
    ) -> str:
        normalized = sorted(set(python_deps))
        payload = json.dumps(
            {
                "deps": normalized,
                "python_version": python_version,
                "platform": platform,
                "arch": arch,
                "sdk_version": self.sdk_version,
            },
            sort_keys=True,
        )
        h = hashlib.sha256()
        h.update(payload.encode("utf-8"))
        return h.hexdigest()[:16]

    def get_or_create_env(self, env_hash: str, python_deps: List[str]) -> EnvInfo:
        env_path = self.venvs_root / env_hash
        env_path.mkdir(parents=True, exist_ok=True)

        venv_path = env_path / ".venv"
        ready_marker = env_path / ".ready"
        lock_file = env_path / ".lock"

        if ready_marker.exists():
            python_exe = self._get_venv_python(venv_path)
            return EnvInfo(
                env_hash=env_hash,
                venv_path=venv_path,
                python_executable=python_exe,
                ready=True,
            )

        lock_file.touch()
        try:
            self._create_venv(venv_path)
            self._install_deps(venv_path, python_deps)
            ready_marker.touch()
        finally:
            lock_file.unlink(missing_ok=True)

        python_exe = self._get_venv_python(venv_path)
        return EnvInfo(env_hash=env_hash, venv_path=venv_path, python_executable=python_exe, ready=True)

    def _create_venv(self, venv_path: Path) -> None:
        result = subprocess.run(["uv", "venv", str(venv_path)], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to create venv: {result.stderr}")

    def _install_deps(self, venv_path: Path, python_deps: List[str]) -> None:
        python_exe = self._get_venv_python(venv_path)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as req_file:
            for dep in python_deps:
                req_file.write(f"{dep}\n")
            req_file.flush()
            req_file_path = req_file.name

        try:
            result = subprocess.run(
                ["uv", "pip", "install", "--python", str(python_exe), "-r", req_file_path],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Failed to install deps: {result.stderr}")
        finally:
            Path(req_file_path).unlink(missing_ok=True)

    @staticmethod
    def _get_venv_python(venv_path: Path) -> Path:
        if os.name == "nt":
            return venv_path / "Scripts" / "python.exe"
        else:
            return venv_path / "bin" / "python"
