"""Noninteractive setup entry: check by default, explicit finite apply."""

import os
from pathlib import Path

import click

from .config import load_settings
from .setup_config import read_config
from .setup_credentials import load_credentials
from .setup_inputs import connection_errors
from .setup_presentation import (
    READY_EXPLANATION,
    configuration_result,
    database_preview,
    inspection_message,
    login_result,
)
from .setup_service import SetupSession

LABELS = {
    "ready": "Ready",
    "needs_configuration": "Needs configuration",
    "unknown": "Unknown",
    "unsupported": "Unsupported",
    "migration_needed": "Migration needed",
}
CODES = {
    "ready": 0,
    "needs_configuration": 4,
    "unknown": 1,
    "unsupported": 5,
    "migration_needed": 4,
}


def run_headless(ctx, apply, credentials_file, confirm_database=None):
    selected = ctx.obj.get("env_file")
    path = Path(selected or ".env")
    if selected is not None and not path.is_file():
        raise click.UsageError("The selected configuration file does not exist.")
    try:
        _, values = read_config(path)
        values.update(os.environ)
        credentials = load_credentials(credentials_file) if credentials_file else {}
        settings = load_settings(selected)
        missing = [key for key in ("PGHOST", "PGDATABASE", "PGUSER") if not values.get(key)]
        if missing:
            supported = ("PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD", "PGSSLMODE")
            if "DATABASE_URL" in values and not any(key in values for key in supported):
                click.echo(
                    "DATABASE_URL is not supported. Configure PG* connection keys.", err=True
                )
            click.echo("Needs configuration: " + ", ".join(missing), err=True)
            ctx.exit(4)
        reader = values.get("SETUP_READER_USER", "tushare_reader")
        errors = connection_errors(values, reader, credentials.get("admin"))
        if errors:
            raise ValueError("; ".join(errors.values()))
        app = SetupSession(
            settings,
            reader,
            credentials,
            observer=lambda event, fields: show_event(ctx, event, fields),
        )
    except ValueError as error:
        raise click.UsageError(str(error)) from None
    except OSError:
        raise click.ClickException(
            "Cannot read configuration or create the private setup log."
        ) from None
    click.echo("Log: " + str(app.log.path))
    click.echo(
        "Target: " + settings.pg_host + ":" + str(settings.pg_port) + "/" + settings.pg_database
    )
    try:
        checked = app.inspect()
        click.echo(LABELS[checked["readiness"]])
        message = inspection_message(checked.get("reason_code"))
        if message:
            click.echo(message, err=True)
        if not ctx.obj.get("quiet"):
            if checked["readiness"] == "migration_needed":
                click.echo(database_preview(settings, reader, checked))
            else:
                click.echo("Plan: " + (", ".join(checked["actions"]) or "No database changes"))
        result = (
            app.apply(confirm_database=confirm_database)
            if apply
            else app.finish_check(CODES[checked["readiness"]])
        )
        if result.get("reason_code"):
            click.echo("Reason: " + result["reason_code"], err=True)
        for key in ("completed", "failed", "unknown", "not_attempted"):
            if result.get(key):
                click.echo(
                    key.replace("_", " ").capitalize() + ": " + ", ".join(result[key]),
                    err=result["exit_code"] != 0,
                )
        if result.get("readiness") == "ready":
            click.echo(READY_EXPLANATION)
        for key in ("writer_verification", "reader_verification"):
            if key in result:
                click.echo(login_result(key.split("_")[0], result[key]))
        if credentials.get("writer", {}).get("password"):
            click.echo(
                "Temporary writer credential used; configure daily authentication separately."
            )
        click.echo(configuration_result("not_saved", headless=True))
        ctx.exit(result["exit_code"])
    except KeyboardInterrupt:
        result = app.finish_check(130)
        click.echo("Interrupted; inspect the database before retrying.", err=True)
        ctx.exit(result["exit_code"])
    except OSError:
        click.echo("Setup logging failed; no further changes will be scheduled.", err=True)
        ctx.exit(1)
    finally:
        try:
            app.close()
        except OSError:
            click.echo(
                "Setup log could not be closed; database results above remain valid.", err=True
            )
            ctx.exit(1)


def show_event(ctx, event, fields):
    if event == "step_started" and not ctx.obj.get("quiet"):
        click.echo("Applying: " + fields["action"])
    if event == "step_finished" and fields.get("outcome") != "completed":
        click.echo("Step " + fields["action"] + ": " + fields["outcome"], err=True)
