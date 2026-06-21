"""Helpers and worker entrypoint for staged app updates."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
import webbrowser
import zipfile
from pathlib import Path


def normalize_release_version(version: str) -> str:
    return str(version or "").strip().lstrip("v")


def build_update_target_dir(repo_root: Path, version: str) -> Path:
    repo_root = Path(repo_root)
    clean_version = normalize_release_version(version)
    return repo_root.parent / f"{repo_root.name}-v{clean_version}"


def is_port_busy(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex(("127.0.0.1", int(port))) == 0


def pick_launch_port(preferred_port: int, is_busy_fn=is_port_busy) -> int:
    preferred_port = int(preferred_port)
    for candidate in range(preferred_port, preferred_port + 20):
        if not is_busy_fn(candidate):
            return candidate
    return preferred_port


def _write_status(status_file: Path, **payload) -> None:
    status_file.parent.mkdir(parents=True, exist_ok=True)
    payload.setdefault("updated_at", time.time())
    status_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _copy_user_state(repo_root: Path, target_dir: Path) -> None:
    config_src = repo_root / "config.yaml"
    if config_src.exists():
        shutil.copy2(config_src, target_dir / "config.yaml")

    data_src = repo_root / "data"
    if data_src.exists():
        shutil.copytree(data_src, target_dir / "data", dirs_exist_ok=True)


def _download_release_zip(zip_url: str, dest_zip: Path) -> None:
    with urllib.request.urlopen(zip_url) as response, open(dest_zip, "wb") as handle:
        shutil.copyfileobj(response, handle)


def _extract_release(zip_path: Path, extract_dir: Path) -> Path:
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(extract_dir)
    entries = [item for item in extract_dir.iterdir() if item.is_dir()]
    if not entries:
        raise RuntimeError("Downloaded archive did not contain a project folder.")
    return entries[0]


def _launch_updated_app(target_dir: Path, launch_port: int) -> str:
    env = os.environ.copy()
    env["SCOUT_PORT"] = str(launch_port)

    creationflags = 0
    for flag_name in ("CREATE_NEW_PROCESS_GROUP", "DETACHED_PROCESS"):
        creationflags |= int(getattr(subprocess, flag_name, 0))

    subprocess.Popen(
        [sys.executable, "preview_server.py"],
        cwd=str(target_dir),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    return f"http://127.0.0.1:{launch_port}"


def run_staged_update(repo_root: Path, version: str, zip_url: str, status_file: Path, preferred_port: int) -> None:
    repo_root = Path(repo_root)
    status_file = Path(status_file)
    version = normalize_release_version(version)
    target_dir = build_update_target_dir(repo_root, version)

    _write_status(status_file, state="running", progress=5, message=f"Preparing ScholarScout v{version} update")

    with tempfile.TemporaryDirectory(prefix="scholarscout-update-") as temp_dir_raw:
        temp_dir = Path(temp_dir_raw)
        zip_path = temp_dir / f"scholarscout-{version}.zip"
        extract_dir = temp_dir / "extract"
        extract_dir.mkdir(parents=True, exist_ok=True)

        _write_status(status_file, state="running", progress=15, message="Downloading release package")
        _download_release_zip(zip_url, zip_path)

        _write_status(status_file, state="running", progress=35, message="Extracting new build")
        extracted_root = _extract_release(zip_path, extract_dir)

        if target_dir.exists() and target_dir != repo_root:
            shutil.rmtree(target_dir)

        _write_status(status_file, state="running", progress=50, message="Preparing new folder")
        shutil.copytree(extracted_root, target_dir)

        _write_status(status_file, state="running", progress=62, message="Migrating your config and data")
        _copy_user_state(repo_root, target_dir)

        _write_status(status_file, state="running", progress=78, message="Installing dependencies")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            cwd=str(target_dir),
            check=True,
        )

        launch_port = pick_launch_port(preferred_port, is_port_busy)
        _write_status(status_file, state="running", progress=90, message=f"Launching updated app on port {launch_port}")
        launch_url = _launch_updated_app(target_dir, launch_port)

        deadline = time.time() + 45
        while time.time() < deadline:
            if is_port_busy(launch_port):
                webbrowser.open(launch_url)
                _write_status(
                    status_file,
                    state="done",
                    progress=100,
                    message="Update complete. Opening the new app window.",
                    launch_url=launch_url,
                    target_dir=str(target_dir),
                    version=version,
                )
                return
            time.sleep(1)

    raise RuntimeError("Updated app did not become ready in time.")


def main(argv: list[str]) -> int:
    if len(argv) != 6:
        raise SystemExit("Usage: updater.py <repo_root> <version> <zip_url> <status_file> <preferred_port>")

    _, repo_root, version, zip_url, status_file, preferred_port = argv
    status_path = Path(status_file)
    try:
        run_staged_update(
            repo_root=Path(repo_root),
            version=version,
            zip_url=zip_url,
            status_file=status_path,
            preferred_port=int(preferred_port),
        )
        return 0
    except Exception as exc:
        _write_status(
            status_path,
            state="error",
            progress=100,
            message=f"Update failed: {exc}",
            version=normalize_release_version(version),
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
