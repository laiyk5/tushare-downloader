"""Optional human-guided setup; all mutations follow a displayed, rechecked plan."""

import os
from dataclasses import replace
from pathlib import Path

import click

from .bounded import DeadlineExceeded, bounded
from .config import Settings, duration
from .read_output import show
from .setup_config import KEYS, read_config, save_config
from .setup_db import apply_step, build_plan, name, snapshot, verify
from .setup_export import export_bundle
from .storage import connect


def connection_test(settings):
    with connect(settings) as conn:
        return conn.execute("SELECT current_user,current_database()").fetchone()


def selected_settings(values):
    cfg = Settings(
        pg_host=values.get("PGHOST", "localhost"),
        pg_port=int(values.get("PGPORT", "5432")),
        pg_database=values.get("PGDATABASE", "tushare"),
        pg_user=values.get("PGUSER", "tushare_writer"),
        pg_password=values.get("PGPASSWORD", ""),
        pg_sslmode=values.get("PGSSLMODE", "prefer"),
        connect_timeout=int(values.get("CONNECT_TIMEOUT_SECONDS", "10")),
        inspect_timeout=duration(values.get("INSPECT_TIMEOUT", "5s"), allow_zero=False),
        setup_step_timeout=duration(values.get("SETUP_STEP_TIMEOUT", "60s"), allow_zero=False),
    )
    if not 1 <= cfg.pg_port <= 65535 or cfg.connect_timeout < 1:
        raise ValueError("Invalid port or connection timeout.")
    if cfg.inspect_timeout.total_seconds() > 300 or cfg.setup_step_timeout.total_seconds() > 600:
        raise ValueError("Inspection/setup time budget exceeds its allowed maximum.")
    if cfg.pg_sslmode not in {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}:
        raise ValueError("Invalid PGSSLMODE.")
    if "," in cfg.pg_host or not cfg.pg_host or any(ord(c) < 32 for c in cfg.pg_host):
        raise ValueError("Setup requires one host without control characters.")
    return cfg


def prompt_settings(values):
    labels = {
        "PGHOST": "Server host",
        "PGPORT": "Server port",
        "PGDATABASE": "Target database",
        "PGUSER": "Writer account",
        "PGSSLMODE": "SSL mode",
    }
    defaults = {
        "PGHOST": "localhost",
        "PGPORT": "5432",
        "PGDATABASE": "tushare",
        "PGUSER": "tushare_writer",
        "PGSSLMODE": "prefer",
    }
    entered = dict(values)
    for key, label in labels.items():
        entered[key] = click.prompt(label, default=values.get(key, defaults[key]))
    if click.confirm(
        "Enter a writer password for this connection?", default=not bool(values.get("PGPASSWORD"))
    ):
        entered["PGPASSWORD"] = click.prompt(
            "Writer password", hide_input=True, default="", show_default=False
        )
    return selected_settings(entered)


def save_offer(ctx, path, original, cfg):
    if not click.confirm("Save downloader connection settings?", default=False):
        click.echo("Configuration: not saved.")
        return
    updates = dict(
        zip(
            KEYS,
            [
                cfg.pg_host,
                str(cfg.pg_port),
                cfg.pg_database,
                cfg.pg_user,
                cfg.pg_password,
                cfg.pg_sslmode,
            ],
            strict=True,
        )
    )
    if not click.confirm(
        "Store the writer password in this private configuration file?", default=False
    ):
        updates.pop("PGPASSWORD")
    _, existing = read_config(path)
    rows = []
    for key, value in updates.items():
        source = "environment override" if key in os.environ else "file"
        rows.append((key, ("[hidden]" if key == "PGPASSWORD" else value) + f" ({source})"))
    show(ctx, "Configuration plan · " + str(path), rows)
    if not click.confirm("Apply this configuration change?", default=False):
        click.echo("Configuration: cancelled.")
        return
    save_config(path, original, updates)
    effective = dict(existing) | updates | dict(os.environ)
    expected = dict(
        zip(
            KEYS,
            [
                cfg.pg_host,
                str(cfg.pg_port),
                cfg.pg_database,
                cfg.pg_user,
                cfg.pg_password,
                cfg.pg_sslmode,
            ],
            strict=True,
        )
    )
    if all(str(effective.get(k, "")) == str(v) for k, v in expected.items()):
        click.echo("Configuration: saved; effective connection matches the verified selection.")
    elif any(k in os.environ for k in KEYS):
        click.echo(
            "Configuration: saved, overridden by environment. Check effective connection settings.",
            err=True,
        )
    else:
        click.echo(
            "Configuration: saved; effective connection not verified (password may be omitted)."
        )


def run_setup(ctx):
    path = Path(ctx.obj.get("env_file") or ".env").absolute()
    try:
        original, values = read_config(path)
    except ValueError as error:
        click.echo(str(error), err=True)
        path = Path(click.prompt("Select a new configuration file")).absolute()
        original, values = read_config(path)
    values |= dict(os.environ)
    if values.get("DATABASE_URL"):
        click.echo(
            "Unsupported connection key DATABASE_URL — not used; enter PG* settings.", err=True
        )
    intent = click.prompt(
        "Action: 1 connection, 2 initialize, 3 upgrade check", type=click.IntRange(1, 3), default=1
    )
    cfg = prompt_settings(values)
    try:
        if intent == 1:
            identity = bounded(connection_test, cfg, seconds=cfg.connect_timeout)
            show(ctx, "Connection verified", [("Account", identity[0]), ("Database", identity[1])])
            save_offer(ctx, path, original, cfg)
            return
        reader = name(click.prompt("Reader account", default="tushare_reader"))
        name(cfg.pg_user)
        name(cfg.pg_database)
        administrator = replace(
            cfg, pg_database=click.prompt("Maintenance database", default="postgres")
        )
        use_admin = click.confirm("Use a temporary administrator connection?", default=False)
        if use_admin:
            administrator = replace(
                administrator,
                pg_user=click.prompt("Administrator account", default="postgres"),
                pg_password=click.prompt(
                    "Administrator password", hide_input=True, default="", show_default=False
                ),
            )
        try:
            state = bounded(
                snapshot,
                cfg,
                administrator,
                reader,
                seconds=cfg.connect_timeout + cfg.inspect_timeout.total_seconds(),
            )
        except (RuntimeError, DeadlineExceeded):
            if click.confirm(
                "Cannot inspect the database. Export a read-only unverified template?",
                default=False,
            ):
                target = Path(click.prompt("New export directory"))
                export_bundle(target, None, cfg, administrator, reader, path)
                click.echo("Unverified template generated — database changes not applied.")
                return
            raise
        plan = build_plan(state)
        show(
            ctx,
            "Database setup · " + cfg.pg_database,
            [
                ("Database state", state["kind"]),
                ("Database ID", state.get("database_id") or "Not initialized"),
                ("Writer", cfg.pg_user),
                ("Reader", reader),
                ("Cluster-wide role reuse", "Review other applications before confirming"),
                ("Plan", ", ".join(plan) if plan else "No database migration required"),
            ],
        )
        if not use_admin and plan:
            click.echo(
                "No administrator connection: use the generated steps with an administrator."
            )
        if click.confirm(
            "Export a script bundle instead of applying changes?",
            default=not use_admin and bool(plan),
        ):
            target = Path(click.prompt("New export directory"))
            export_bundle(target, state, cfg, administrator, reader, path)
            click.echo("Script generated — database changes not applied.")
            return
        if plan and not use_admin:
            raise ValueError("An administrator connection is required for this plan.")
        if plan:
            typed = click.prompt(
                "Apply these changes? Type the target database name", default="", show_default=False
            )
            if typed != cfg.pg_database:
                click.echo("Cancelled — no database changes applied.")
                return
        reader_password = click.prompt(
            "Reader password for creation/verification (blank if not required)",
            hide_input=True,
            default="",
            show_default=False,
        )
        completed = []
        for action in plan:
            click.echo("Applying: " + action)
            try:
                password = cfg.pg_password if action == "create-writer" else reader_password
                state = bounded(
                    apply_step,
                    state,
                    action,
                    cfg,
                    administrator,
                    reader,
                    password,
                    seconds=cfg.setup_step_timeout.total_seconds(),
                )
                completed.append(action)
            except (RuntimeError, DeadlineExceeded):
                click.echo(
                    "Step outcome unknown or failed; completed: "
                    + (", ".join(completed) or "none"),
                    err=True,
                )
                try:
                    actual = bounded(
                        snapshot,
                        cfg,
                        administrator,
                        reader,
                        seconds=cfg.connect_timeout + cfg.inspect_timeout.total_seconds(),
                    )
                    click.echo(
                        "Rechecked database state: "
                        + actual["kind"]
                        + "; rerun setup to make a new plan.",
                        err=True,
                    )
                except (RuntimeError, DeadlineExceeded):
                    click.echo(
                        "Recheck unavailable. No change will be retried automatically.", err=True
                    )
                raise
        for label, connection in [
            ("writer", cfg),
            ("reader", replace(cfg, pg_user=reader, pg_password=reader_password)),
        ]:
            facts = bounded(
                verify,
                connection,
                seconds=cfg.connect_timeout + cfg.inspect_timeout.total_seconds(),
            )
            click.echo(label.capitalize() + " connection verified: " + facts["user"])
        final = bounded(
            snapshot,
            cfg,
            administrator,
            reader,
            seconds=cfg.connect_timeout + cfg.inspect_timeout.total_seconds(),
        )
        if not final["roles_safe"]:
            raise ValueError("Reader effective permissions require administrator review.")
        click.echo("Database and access verification complete; no structural migration was needed.")
        save_offer(ctx, path, original, cfg)
    except (RuntimeError, DeadlineExceeded) as error:
        raise click.ClickException("Setup did not complete: " + str(error)) from None
    except KeyboardInterrupt:
        click.echo(
            "Interrupted; previously completed database steps remain. Rerun setup to inspect.",
            err=True,
        )
        ctx.exit(130)
