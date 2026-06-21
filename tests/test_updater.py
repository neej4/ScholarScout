from pathlib import Path

from src.core.updater import build_update_target_dir, normalize_release_version, pick_launch_port


def test_normalize_release_version_strips_v_prefix():
    assert normalize_release_version("v1.6.5") == "1.6.5"
    assert normalize_release_version("1.6.5") == "1.6.5"


def test_build_update_target_dir_uses_sibling_folder():
    root = Path("D:/Apps/ScholarScout")
    target = build_update_target_dir(root, "1.6.5")
    assert target == Path("D:/Apps/ScholarScout-v1.6.5")


def test_pick_launch_port_prefers_requested_port_when_free():
    assert pick_launch_port(5050, lambda port: port != 5050) == 5050


def test_pick_launch_port_finds_next_available_port():
    busy = {5050, 5051}
    port = pick_launch_port(5050, lambda candidate: candidate in busy)
    assert port == 5052
