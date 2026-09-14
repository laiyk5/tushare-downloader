from datetime import timedelta

import pytest

from tushare_downloader.config import ConfigError, duration, load_settings


def test_precedence_and_no_side_effects(tmp_path):
    (tmp_path / ".env").write_text("TUSHARE_TOKEN=file-secret\nPGPORT=5433\nPLAIN=false\n")
    settings = load_settings(cwd=tmp_path, environ={"TUSHARE_TOKEN": "env-secret"}, plain=True)
    assert settings.require_token() == "env-secret"
    assert settings.pg_port == 5433
    assert settings.plain
    assert "secret" not in repr(settings)
    assert not settings.log_dir.exists()


def test_no_parent_search(tmp_path):
    (tmp_path / ".env").write_text("TUSHARE_TOKEN=parent-secret")
    child = tmp_path / "child"
    child.mkdir()
    with pytest.raises(ConfigError):
        load_settings(cwd=child, environ={}).require_token()


@pytest.mark.parametrize(
    "value,expected", [("0", 0), ("30s", 30), ("5m", 300), ("24h", 86400), ("7d", 604800)]
)
def test_duration(value, expected):
    assert duration(value) == timedelta(seconds=expected)


@pytest.mark.parametrize("value", ["-1d", "tomorrow", "30", "1.5h"])
def test_bad_duration(value):
    with pytest.raises(ConfigError):
        duration(value)


@pytest.mark.parametrize(
    "key,value",
    [
        ("PGPORT", "0"),
        ("PGPORT", "65536"),
        ("MAX_ATTEMPTS", "0"),
        ("EMPTY_RECHECK_AGE", "0"),
        ("PROGRESS", "secret"),
    ],
)
def test_invalid_config_redaction(tmp_path, key, value):
    with pytest.raises(ConfigError) as error:
        load_settings(cwd=tmp_path, environ={key: value})
    assert key in str(error.value)
    assert "secret" not in str(error.value)


def test_missing_explicit_file(tmp_path):
    with pytest.raises(ConfigError):
        load_settings(tmp_path / "missing", environ={})


@pytest.mark.parametrize("count", [0, 5, 20])
@pytest.mark.parametrize("mode", ["basic", "calendar", "off"])
def test_display_and_calendar_settings(tmp_path, count, mode):
    settings = load_settings(
        cwd=tmp_path,
        environ={
            "TERMINAL_LOG_LINES": str(count),
            "CALENDAR_FILTER": mode,
            "CALENDAR_CACHE_DIR": "cache",
            "CALENDAR_MAX_AGE": "12h",
        },
    )
    assert settings.terminal_log_lines == count
    assert settings.calendar_filter == mode
    assert settings.calendar_cache_dir == tmp_path / "cache"
    assert settings.calendar_max_age == timedelta(hours=12)
    assert not settings.calendar_cache_dir.exists()


@pytest.mark.parametrize(
    "key,value",
    [
        ("TERMINAL_LOG_LINES", "-1"),
        ("TERMINAL_LOG_LINES", "21"),
        ("TERMINAL_LOG_LINES", "1.5"),
        ("CALENDAR_FILTER", "fallback"),
        ("CALENDAR_MAX_AGE", "0"),
        ("CALENDAR_MAX_AGE", "-1d"),
    ],
)
def test_invalid_v02_settings(tmp_path, key, value):
    with pytest.raises(ConfigError, match=key):
        load_settings(cwd=tmp_path, environ={key: value})


def test_new_settings_default_without_migrating_file(tmp_path):
    config = tmp_path / ".env"
    original = "PGPORT=5433\nCUSTOM=keep\nPGPORT=5434\n"
    config.write_text(original)
    settings = load_settings(cwd=tmp_path, environ={})
    assert settings.pg_port == 5434
    assert settings.calendar_filter == "basic"
    assert settings.terminal_log_lines == 5
    assert settings.calendar_max_age == timedelta(hours=24)
    assert config.read_text() == original
