"""DBW13/23: configuration previews explain actual effect without secrets."""

from tushare_downloader.setup_presentation import configuration_preview


def test_environment_override_and_saved_password_retention_are_explicit():
    text, matches, overridden = configuration_preview(
        {"PGHOST": "file_host", "PGPASSWORD": "OLD_SECRET"},
        {"PGHOST": "env_host", "PGPASSWORD": "OLD_SECRET"},
        {"PGHOST": "selected_host", "PGPASSWORD": "NEW_SECRET"},
        {"PGHOST": "selected_host"},
        {"PGHOST": "env_host"},
    )
    assert not matches
    assert overridden
    for label in ("File", "Current", "Selected", "Saved", "Effective after", "environment"):
        assert label in text
    for value in ("file_host", "env_host", "selected_host"):
        assert value in text
    assert "OLD_SECRET" not in text and "NEW_SECRET" not in text
    assert "retained" in text


def test_new_file_does_not_claim_unstored_password_matches():
    text, matches, overridden = configuration_preview(
        {}, {}, {"PGHOST": "localhost", "PGPASSWORD": "SECRET"}, {"PGHOST": "localhost"}, {}
    )
    assert not matches
    assert not overridden
    assert "SECRET" not in text
    assert "not stored" in text


def test_matching_configuration_is_recognized_without_environment_override():
    selected = {"PGHOST": "localhost", "PGPASSWORD": "SECRET"}
    _, matches, overridden = configuration_preview({}, {}, selected, selected, {})
    assert matches
    assert not overridden
