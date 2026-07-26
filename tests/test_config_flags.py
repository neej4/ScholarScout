from src.core.config import _as_bool


def test_as_bool_accepts_yaml_bool_and_common_env_strings():
    assert _as_bool(True) is True
    assert _as_bool("1") is True
    assert _as_bool("true") is True
    assert _as_bool("yes") is True
    assert _as_bool("on") is True


def test_as_bool_rejects_falsey_values():
    assert _as_bool(False) is False
    assert _as_bool("0") is False
    assert _as_bool("false") is False
    assert _as_bool("no") is False
    assert _as_bool("") is False
    assert _as_bool(None) is False
