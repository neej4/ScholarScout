import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parents[1]


def _version_file() -> str:
    return (ROOT / "VERSION").read_text(encoding="utf-8").strip()


def _pyproject_version() -> str | None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    dynamic_match = re.search(r"^dynamic\s*=\s*\[(.*?)\]", text, re.M | re.S)
    if dynamic_match and "version" in dynamic_match.group(1):
        return None
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
    return match.group(1) if match else None


def test_version_sources_agree():
    version = _version_file()
    pyproject_version = _pyproject_version()

    if pyproject_version is not None:
        assert pyproject_version == version

    changelog_head = "\n".join((ROOT / "CHANGELOG.md").read_text(encoding="utf-8").splitlines()[:5])
    assert f"v{version}" in changelog_head
