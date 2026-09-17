"""Human-readable commands; persistent preferences live in configuration."""

import os
import shutil
import sys
import textwrap
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path

import click
import psycopg
from rich.console import Console
from rich.text import Text

from .apis import APIS, get_api
from .config import ConfigError, duration, load_settings
from .download import execute
from .reporting import Reporter
from .storage import BusyError, StorageError, Store, connect

EXAMPLES = {
    "main": ["list", "fetch daily_basic -s 2026-09-01 -e 2026-09-10", "update stock_basic"],
    "fetch": ["fetch daily_basic -s 2026-09-01 -e 2026-09-10", "fetch stock_basic"],
    "refresh": [
        "refresh daily_basic -s 2026-09-01 -e 2026-09-10 --max-age 7d",
        "--plain refresh stock_basic --max-age 0",
    ],
    "update": ["update daily_basic", "update stock_basic"],
    "clean": ["clean stock_basic"],
    "init-db": ["init-db"],
    "list": ["list"],
    "schema": ["schema", "schema daily"],
    "inspect": ["inspect", "inspect daily", "inspect daily --counts"],
    "setup": ["setup"],
    "migrate": ["migrate suspend_d", "migrate suspend_d --apply --confirm-database tushare"],
}
SHORT_HELP = {
    "fetch": "Fetch missing or expired data.",
    "refresh": "Reconcile data with the source.",
    "update": "Update using the API policy.",
    "init-db": "Initialize or validate tables.",
    "clean": "Preview or remove an API table.",
    "list": "List supported datasets offline.",
    "schema": "Read shipped table contracts offline.",
    "inspect": "Summarize datasets in the configured database.",
    "setup": "Configure database access interactively.",
    "migrate": "Preview or apply a supported schema migration.",
}
REFERENCE = "https://laiyk5.github.io/tushare-downloader/reference/cli/"


class HelpLayout:
    def format_help(self, ctx, formatter):
        self.format_usage(ctx, formatter)
        self.format_help_text(ctx, formatter)
        if isinstance(self, click.Group):
            for title, names in [
                ("Download", [("fetch", "f"), ("refresh", ""), ("update", "u")]),
                ("Database", [("setup", ""), ("init-db", "init"), ("migrate", ""), ("clean", "")]),
                ("Inspect", [("list", "ls"), ("inspect", "i"), ("schema", "")]),
            ]:
                with formatter.section(title):
                    formatter.write_dl(
                        [
                            (
                                f"{name} ({alias})" if alias else name,
                                SHORT_HELP[name],
                            )
                            for name, alias in names
                        ]
                    )
            click.Command.format_options(self, ctx, formatter)
        else:
            self.format_options(ctx, formatter)
        with formatter.section("Examples"):
            for example in EXAMPLES.get(self.name, EXAMPLES["main"]):
                command = "tushare-downloader " + example
                lines = textwrap.wrap(
                    command,
                    width=max(20, formatter.width - formatter.current_indent - 4),
                    break_long_words=False,
                    break_on_hyphens=False,
                )
                for index, line in enumerate(lines):
                    continuation = " \\" if index < len(lines) - 1 else ""
                    indent = formatter.current_indent + (2 if index else 0)
                    formatter.write(" " * indent + line + continuation + "\n")
                formatter.write_paragraph()
        formatter.write_text("Reference: " + REFERENCE)

    def get_help(self, ctx):
        if ctx.terminal_width is None:
            ctx.terminal_width = shutil.get_terminal_size((80, 24)).columns
        text = super().get_help(ctx)
        root = ctx.find_root()
        plain = root.params.get("plain", False) or os.environ.get("PLAIN") in {"true", "1"}
        if (
            plain
            or "NO_COLOR" in os.environ
            or os.environ.get("TERM") == "dumb"
            or not sys.stdout.isatty()
            or not sys.stderr.isatty()
        ):
            return text
        output = StringIO()
        rich_text = Text(text)
        rich_text.highlight_regex(
            r"(?m)^(Usage:|Download|Database|Inspect|Options:|Examples:)", "bold cyan"
        )
        rich_text.highlight_regex(r"--[a-z-]+|(?<![a-z])-([hqvsec])\b", "bold green")
        Console(file=output, force_terminal=True, width=ctx.terminal_width or 80).print(
            rich_text, end=""
        )
        return output.getvalue()


class Command(HelpLayout, click.Command):
    pass


class Commands(HelpLayout, click.Group):
    command_class = Command

    def get_command(self, ctx, name):
        return super().get_command(
            ctx,
            {"ls": "list", "i": "inspect", "f": "fetch", "u": "update", "init": "init-db"}.get(
                name, name
            ),
        )


@click.group(
    cls=Commands,
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option(package_name="tushare-downloader")
@click.option(
    "-c",
    "--env-file",
    type=click.Path(path_type=Path, dir_okay=False),
    help="Configuration file; default: .env in cwd.",
)
@click.option("-q", "--quiet", is_flag=True, help="Essential output only.")
@click.option("-v", "--verbose", count=True, help="Include request and diagnostic details.")
@click.option("--plain", is_flag=True, is_eager=True, help="Plain text without terminal controls.")
@click.pass_context
def main(ctx, env_file, quiet, verbose, plain):
    """Download Tushare Pro data into PostgreSQL."""
    if quiet and verbose:
        raise click.UsageError("-q and -v cannot be used together.")
    ctx.obj = {"env_file": env_file, "plain": plain, "quiet": quiet, "verbose": verbose}
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


def settings(ctx):
    try:
        return load_settings(ctx.obj["env_file"], plain=ctx.obj["plain"])
    except ConfigError as error:
        raise click.UsageError(str(error)) from None


def guarded(ctx, action):
    try:
        return action()
    except BusyError as error:
        click.echo(str(error), err=True)
        ctx.exit(3)
    except (ConfigError, ValueError) as error:
        raise click.UsageError(str(error)) from None
    except StorageError as error:
        raise click.ClickException(str(error)) from None
    except psycopg.Error as error:
        raise click.ClickException(
            f"Database operation failed (SQLSTATE={error.sqlstate or 'connection'}). Check connection, permissions and schema."
        ) from None
    except OSError:
        raise click.ClickException(
            "Cannot access log, report or configuration files. Check paths and permissions."
        ) from None


@main.command("list")
@click.pass_context
def list_apis(ctx):
    """List supported APIs without connecting to PostgreSQL or Tushare."""
    for api in APIS.values():
        kind = api.change_kind
        shape = api.query_kind
        click.echo(
            f"{api.name}: {kind} / {shape}; key={','.join(api.unique_key)}; "
            f"stale reconciliation={'enabled' if api.stale_scope_verified else 'unverified'}"
        )


@main.command("init-db")
@click.pass_context
def init_db(ctx):
    """Initialize or validate managed database objects."""
    config = settings(ctx)

    def action():
        with connect(config) as conn:
            store = Store(conn)
            with store.writer():
                identity = store.initialize()
            click.echo(f"Initialized: {conn.info.dbname}; database_id={identity}")

    guarded(ctx, action)


@main.command("migrate")
@click.argument("api_name", type=click.Choice(["suspend_d"]))
@click.option("--apply", "apply_changes", is_flag=True, help="Apply the supported migration.")
@click.option("--confirm-database", help="Exact database name; required with --apply.")
@click.pass_context
def migrate_command(ctx, api_name, apply_changes, confirm_database):
    """Preview a migration; changes require explicit database confirmation."""
    from .migration import apply, preview
    from .read_output import show
    from .setup_events import SetupLog
    from .storage import CommitUnknown

    if apply_changes != bool(confirm_database):
        raise click.UsageError("Use --apply and --confirm-database together.")
    config = settings(ctx)

    def action():
        log = SetupLog(
            config.log_dir,
            "apply" if apply_changes else "preview",
            {
                "host": config.pg_host,
                "port": config.pg_port,
                "database": config.pg_database,
                "writer": config.pg_user,
            },
            command="migrate",
        )
        outcome = "not_applied"
        try:
            click.echo(f"Log: {log.path}")
            log.emit("config_loaded")
            with connect(config) as conn:
                if apply_changes and confirm_database != conn.info.dbname:
                    raise click.UsageError(
                        "Database confirmation does not match the connected database."
                    )
                plan = preview(conn)
                log.plan(
                    ["migrate-suspend-d"] if plan["spec"] == "1" else [],
                    before={"spec": plan["spec"]},
                    after={"spec": "2"},
                )
                show(
                    ctx,
                    "Migration · suspend_d",
                    [
                        ("Database", conn.info.dbname),
                        ("Database ID", plan["database_id"]),
                        ("State", plan["state"]),
                        ("Installed schema", "1.0.0" if plan["spec"] == "1" else "2.0.0"),
                        ("Expected schema", "2.0.0"),
                        ("Rows", plan.get("rows", "Not counted")),
                        (
                            "Coverage",
                            "Old spec observations are not reused; re-fetch your original range.",
                        ),
                    ],
                )
                if apply_changes:
                    log.emit("step_started", action="migrate-suspend-d")
                    outcome = "unknown"
                    result = apply(conn, plan["database_id"])
                    outcome = "committed"
                    click.echo(result["state"] + ": suspend_d schema 2.0.0")
                    log.emit("step_finished", action="migrate-suspend-d", outcome="success")
                else:
                    outcome = "preview"
            log.emit("session_finished", outcome=outcome, exit_code=0)
        except BaseException as error:
            interrupted = isinstance(error, KeyboardInterrupt) or (
                isinstance(error, CommitUnknown) and error.interrupted
            )
            code = (
                130
                if interrupted
                else 3
                if isinstance(error, BusyError)
                else 2
                if isinstance(error, click.UsageError)
                else 1
            )
            if isinstance(error, CommitUnknown):
                click.echo(
                    "Migration commit: Unknown. Run migrate suspend_d to inspect before retrying.",
                    err=True,
                )
            elif outcome == "committed":
                click.echo(
                    "Migration committed; recording results failed. Do not replay blindly.",
                    err=True,
                )
            else:
                outcome = "failed"
            try:
                log.emit("session_finished", outcome=outcome, exit_code=code)
            except OSError:
                pass
            if interrupted:
                click.echo("Migration interrupted; inspect the database before retrying.", err=True)
                ctx.exit(130)
            raise
        finally:
            pending_exception = sys.exc_info()[0] is not None
            try:
                log.close()
            except OSError:
                click.echo(f"Migration log could not close; database outcome: {outcome}.", err=True)
                if not pending_exception:
                    ctx.exit(1)

    guarded(ctx, action)


def run(
    ctx, command, api_name, start=None, end=None, dry_run=False, max_age=None, ignore_calendar=False
):
    def action():
        api = get_api(api_name)
        config = settings(ctx)
        if max_age is not None:
            config = replace(config, max_age=duration(max_age))
        first, last = start.date() if start else None, end.date() if end else None
        if command != "update":
            if api.query_kind == "time-range" and (first is None or last is None):
                raise ValueError("Time-range APIs require both --start and --end.")
            if api.query_kind == "snapshot" and (first or last):
                raise ValueError("Snapshot APIs do not accept dates.")
            if first and last and first > last:
                raise ValueError("Start date must not be after end date.")
            if last is not None and last > api.available_end(datetime.now(UTC)) + timedelta(days=1):
                raise ValueError("End date must not be after today in Asia/Shanghai.")
        with Reporter(
            config, api, command, quiet=ctx.obj["quiet"], verbose=ctx.obj["verbose"]
        ) as reporter:
            with connect(config) as conn:
                store = Store(conn)
                # Dry-run does not acquire the writer lock and issues no data mutations.
                if dry_run:
                    code = execute(
                        store,
                        api,
                        command,
                        config,
                        start=first,
                        end=last,
                        dry_run=True,
                        quiet=ctx.obj["quiet"],
                        verbose=ctx.obj["verbose"],
                        reporter=reporter,
                        ignore_calendar=ignore_calendar,
                    )
                else:
                    with store.writer():
                        code = execute(
                            store,
                            api,
                            command,
                            config,
                            start=first,
                            end=last,
                            quiet=ctx.obj["quiet"],
                            verbose=ctx.obj["verbose"],
                            reporter=reporter,
                            ignore_calendar=ignore_calendar,
                        )
        ctx.exit(code)

    guarded(ctx, action)


def range_options(func):
    func = click.option(
        "--ignore-calendar", is_flag=True, help="Bypass trading-day filtering for this invocation."
    )(func)
    func = click.option(
        "--dry-run", is_flag=True, help="Preview the plan without remote requests or data writes."
    )(func)
    func = click.option(
        "-e",
        "--end",
        type=click.DateTime(formats=["%Y-%m-%d"]),
        help="Inclusive date (YYYY-MM-DD).",
    )(func)
    func = click.option(
        "-s",
        "--start",
        type=click.DateTime(formats=["%Y-%m-%d"]),
        help="Inclusive date (YYYY-MM-DD).",
    )(func)
    return click.argument("api_name", type=click.Choice(list(APIS)), metavar="API")(func)


@main.command("fetch")
@range_options
@click.pass_context
def fetch(ctx, **kwargs):
    """Fetch a range or snapshot, skipping valid local records.

    Time-range APIs require both dates; snapshots reject dates."""
    run(ctx, "fetch", **kwargs)


@main.command("refresh")
@range_options
@click.option(
    "--max-age", help="Freshness threshold, e.g. 12h, 7d, or 0. Config: MAX_AGE; default: 24h."
)
@click.pass_context
def refresh(ctx, **kwargs):
    """Reconcile a range or snapshot with the source.

    Request when the last reconciliation is older than --max-age.
    Missing or invalid records are always requested. Use 0 to force.
    Calendar filtering still applies unless --ignore-calendar is given.
    Empty responses use EMPTY_RECHECK_AGE unless --max-age is 0.
    Time-range APIs require both dates; snapshots reject dates."""
    run(ctx, "refresh", **kwargs)


@main.command("update")
@click.option(
    "--ignore-calendar", is_flag=True, help="Bypass trading-day filtering for this invocation."
)
@click.argument("api_name", type=click.Choice(list(APIS)), metavar="API")
@click.option("--dry-run", is_flag=True)
@click.pass_context
def update(ctx, **kwargs):
    """Update data using the API update policy.

    Append-only daily APIs: re-fetch from the latest local date minus LOOKBACK_DAYS - 1
    through yesterday (Asia/Shanghai). Fetch an initial range if empty.
    stock_basic: reconcile the full snapshot; local data is optional.
    Dates are not accepted. Freshness does not skip update requests."""
    run(ctx, "update", **kwargs)


@main.command("clean")
@click.argument("api_name", type=click.Choice(list(APIS)), metavar="API")
@click.option(
    "--apply", is_flag=True, help="Delete data; requires both database name and UUID confirmation."
)
@click.option("--confirm-database")
@click.option("--confirm-database-id", type=click.UUID)
@click.pass_context
def clean(ctx, api_name, apply, confirm_database, confirm_database_id):
    """Preview cleanup; no cascading deletion of downstream data.

    Deletion requires --apply, --confirm-database and --confirm-database-id."""
    config = settings(ctx)

    def action():
        with connect(config) as conn:
            store = Store(conn)
            with store.writer():
                result = store.clean(
                    get_api(api_name),
                    apply=apply,
                    database=confirm_database,
                    database_id=confirm_database_id,
                )
            click.echo("Cleanup completed" if apply else "Cleanup preview (nothing deleted)")
            for key, value in result.items():
                click.echo(f"{key}: {value}")

    guarded(ctx, action)


@main.command("schema")
@click.argument("api_name", required=False)
@click.pass_context
def schema_command(ctx, api_name):
    """Read shipped contracts without database access."""
    from .contracts import contract
    from .read_output import show

    try:
        selected = [get_api(api_name)] if api_name else [APIS[n] for n in sorted(APIS)]
    except ValueError as error:
        raise click.UsageError(str(error)) from None
    for api in selected:
        c = contract(api)
        rows = [("Table", c["table"]), ("Schema", c["version"]), ("Key", ", ".join(c["key"]))]
        if api_name:
            rows += [
                (
                    f["name"],
                    f"{f['type']}; nullable={f['nullable']}; "
                    f"{'managed' if f['managed'] else 'source'}; {f['description']}",
                )
                for f in c["fields"]
            ]
        show(ctx, "Shipped schema contract · " + api.name, rows)


@main.command("inspect")
@click.argument("api_name", required=False)
@click.option("--counts", "-c", is_flag=True, help="Count exact rows; requires an API.")
@click.pass_context
def inspect_command(ctx, api_name, counts):
    """Read local sizes, dates and recorded fetch times. No downloads."""
    from .inspection import inspect_dataset
    from .read_output import show, show_overview

    if counts and not api_name:
        raise click.UsageError("--counts requires an API.")
    if api_name:
        try:
            get_api(api_name)
        except ValueError as error:
            raise click.UsageError(str(error)) from None
    config = settings(ctx)
    all_ok = True
    results = []
    for name in [api_name] if api_name else sorted(APIS):
        try:
            result = inspect_dataset(config, name, counts)
        except KeyboardInterrupt:
            if not api_name and results:
                show_overview(ctx, results)
            click.echo(
                "Inspection interrupted; previously displayed results are retained.", err=True
            )
            ctx.exit(130)
        all_ok &= result.pop("ok")
        if not ctx.obj.get("verbose"):
            result.pop("Recorded spec versions", None)
        if api_name:
            show(ctx, "Local dataset · " + name, list(result.items()))
        else:
            results.append(result)
    if not api_name:
        show_overview(ctx, results)
    if not ctx.obj.get("quiet"):
        click.echo(
            "Sizes include indexes and stale rows. Dates and fetch times do not prove coverage."
        )
        click.echo("Fetch times are recorded observation times, not exact COMMIT timestamps.")
    if not all_ok:
        click.echo("Partial inspection: check permissions, schema, or query time budget.", err=True)
        ctx.exit(1)


def setup_terminal_available():
    return sys.stdin.isatty() and sys.stdout.isatty()


@main.command("setup")
@click.option(
    "--new", is_flag=True, help="Configure a new connection without replacing the old file."
)
@click.option(
    "--headless", is_flag=True, help="Check without interaction; does not change the database."
)
@click.option("--apply", is_flag=True, help="Apply necessary changes with --headless.")
@click.option(
    "--credentials-file",
    type=click.Path(path_type=Path, dir_okay=False),
    help="Private JSON credentials for this headless invocation only.",
)
@click.pass_context
def setup_command(ctx, new, headless, apply, credentials_file):
    """Check and configure database access; use --headless for scripts."""
    if (apply or credentials_file is not None) and not headless:
        raise click.UsageError("--apply and --credentials-file require --headless.")
    if new and headless:
        raise click.UsageError("--new cannot be used with --headless.")
    if headless:
        from .setup_headless import run_headless

        return run_headless(ctx, apply, credentials_file)
    if not setup_terminal_available():
        raise click.UsageError("Setup requires an interactive terminal; use --headless.")
    from .setup_dialogue import run_dialogue

    guarded(ctx, lambda: run_dialogue(ctx, new=new))
