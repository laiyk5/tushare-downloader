"""Minimal executable entry point; no downloader commands are implemented."""

import click


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(package_name="tushare-downloader")
def main() -> None:
    """Tushare downloader development scaffold.

    Fetch, refresh, update, database access, and configuration loading are not
    implemented yet. See docs/design/index.md for the current design.
    """
    click.echo("项目骨架已就绪；下载功能尚未实现。设计入口：docs/design/index.md")
