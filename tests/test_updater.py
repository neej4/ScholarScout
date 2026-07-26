from pathlib import Path

from src.core.updater import _copy_user_state, build_update_target_dir, normalize_release_version, pick_launch_port
from src.web.routes.update import _safe_release_url


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


def test_safe_release_url_accepts_github_https_sources():
    assert _safe_release_url("https://github.com/neej4/ScholarScout/archive/refs/tags/v1.7.0.zip")
    assert _safe_release_url("https://api.github.com/repos/neej4/ScholarScout/zipball/v1.7.0")
    assert _safe_release_url("https://codeload.github.com/neej4/ScholarScout/zip/refs/tags/v1.7.0")


def test_safe_release_url_rejects_non_github_or_non_https_sources():
    assert not _safe_release_url("http://github.com/neej4/ScholarScout/archive/refs/tags/v1.7.0.zip")
    assert not _safe_release_url("file:///tmp/ScholarScout.zip")
    assert not _safe_release_url("https://example.com/ScholarScout.zip")
    assert not _safe_release_url("")


def test_copy_user_state_only_copies_config_and_data(tmp_path):
    repo_root = tmp_path / "ScholarScout"
    target = tmp_path / "ScholarScout-v1.7.0"
    (repo_root / "data").mkdir(parents=True)
    target.mkdir()
    (repo_root / "config.yaml").write_text("provider: local\n", encoding="utf-8")
    (repo_root / "data" / "session_history.json").write_text("[]", encoding="utf-8")
    (repo_root / "notes.txt").write_text("do not copy", encoding="utf-8")

    _copy_user_state(repo_root, target)

    assert (target / "config.yaml").read_text(encoding="utf-8") == "provider: local\n"
    assert (target / "data" / "session_history.json").read_text(encoding="utf-8") == "[]"
    assert not (target / "notes.txt").exists()
