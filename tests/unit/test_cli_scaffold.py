from click.testing import CliRunner

from tushare_downloader.cli import main


def test_help():
    result = CliRunner().invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Examples:" in result.output


def test_list_without_credentials(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)
    runner = CliRunner()
    result = runner.invoke(main, ["list"])
    assert result.exit_code == 0
    assert "daily_basic: append-only" in result.output
    assert runner.invoke(main, ["ls"]).output == result.output


def test_version():
    assert CliRunner().invoke(main, ["--version"]).exit_code == 0


def test_unimplemented_command():
    assert CliRunner().invoke(main, ["fetch", "daily_basic"]).exit_code == 2


def test_conflicting_verbosity():
    assert CliRunner().invoke(main, ["-q", "-v", "list"]).exit_code == 2


def test_help_is_static_english_and_has_examples(tmp_path, monkeypatch):
    import re

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "tushare_downloader.cli.load_settings",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("configuration read")),
    )
    monkeypatch.setattr(
        "tushare_downloader.cli.connect",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("database access")),
    )
    runner = CliRunner()
    for command in [[], ["fetch"], ["refresh"], ["update"], ["clean"], ["init-db"], ["list"]]:
        result = runner.invoke(main, [*command, "--help"], terminal_width=40)
        assert result.exit_code == 0, result.output
        assert "Examples:" in result.output
        assert not re.search(r"[\u4e00-\u9fff]", result.output)
        assert "\x1b" not in result.output
    result = runner.invoke(main, ["-q", "list"])
    assert result.exit_code == 0 and "stock_basic" in result.output
    assert not list(tmp_path.iterdir())


def test_help_groups_and_aliases():
    output = CliRunner().invoke(main, ["--help"]).output
    assert (
        output.index("Download")
        < output.index("Database")
        < output.index("Inspect")
        < output.index("Options:")
        < output.index("Examples:")
    )
    for alias in ["fetch (f)", "update (u)", "init-db (init)", "list (ls)"]:
        assert alias in output


def test_help_single_stream_redirection_is_plain(monkeypatch):
    import io

    import click

    class TTY(io.StringIO):
        def isatty(self):
            return True

    monkeypatch.setattr("sys.stdout", TTY())
    monkeypatch.setattr("sys.stderr", io.StringIO())
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm")
    with click.Context(main) as ctx:
        assert "\x1b" not in main.get_help(ctx)


def test_narrow_help_examples_preserve_shell_arguments():
    import shlex

    from tushare_downloader.cli import EXAMPLES

    for width in (40, 80, 120):
        for command, examples in EXAMPLES.items():
            args = [] if command == "main" else [command]
            output = CliRunner().invoke(main, [*args, "--help"], terminal_width=width)
            assert output.exit_code == 0
            section = output.output.split("Examples:\n", 1)[1].split("Reference:", 1)[0]
            actual = [
                shlex.split(block.replace("\\\n", " "))
                for block in section.strip().split("\n\n")
                if block.strip()
            ]
            expected = [shlex.split("tushare-downloader " + item) for item in examples]
            assert actual == expected
            assert all(len(line) <= width for line in section.splitlines())


def test_plain_is_processed_before_eager_help(monkeypatch):
    import io
    from contextlib import redirect_stderr, redirect_stdout

    class Terminal(io.StringIO):
        def isatty(self):
            return True

    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("PLAIN", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    stdout, stderr = Terminal(), Terminal()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        main.main(args=["--plain", "--help"], prog_name="tushare-downloader", standalone_mode=False)
    assert "Usage:" in stdout.getvalue()
    assert "\x1b" not in stdout.getvalue() + stderr.getvalue()
