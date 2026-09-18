"""Human-readable static query rendering; no file output."""

import os
import sys
from datetime import UTC, datetime

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def console(ctx):
    plain = (
        ctx.obj.get("plain")
        or os.environ.get("PLAIN") in {"true", "1"}
        or "NO_COLOR" in os.environ
        or os.environ.get("TERM") == "dumb"
        or not sys.stdout.isatty()
        or not sys.stderr.isatty()
    )
    return None if plain else Console(highlight=False)


def display(value):
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, (list, tuple)):
        return "; ".join(display(item) for item in value) if value else "Never"
    return str(value)


def size(value):
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.1f} {unit}"
        value /= 1024


def show(ctx, title, rows):
    formatted = []
    for key, value in rows:
        if key == "Storage bytes (total / table / indexes)" and isinstance(value, tuple):
            formatted.extend(
                (label, f"{size(n)} ({n:,} bytes)")
                for label, n in zip(("Total size", "Table size", "Index size"), value, strict=True)
            )
        else:
            formatted.append((key, display(value)))
    rows = formatted
    renderer = console(ctx)
    if renderer is None:
        click.echo(title)
        for key, value in rows:
            click.echo(f"  {key}: {value}")
    else:
        table = Table.grid(padding=(0, 2))
        table.add_column(style="bold cyan")
        table.add_column(overflow="fold")
        for key, value in rows:
            style = (
                {
                    "Ready": "green",
                    "Not initialized": "dim",
                    "Incompatible": "red",
                    "Permission denied": "red",
                    "Timed out": "yellow",
                    "Unavailable": "red",
                    "Partial inspection": "yellow",
                }.get(str(value), "")
                if key == "State"
                else ""
            )
            table.add_row(Text(str(key)), Text(str(value), style=style))
        renderer.print(Panel(table, title=Text(title)))


def show_overview(ctx, results):
    """One logical row per dataset; no detail cards in the default query."""
    import shutil
    import textwrap

    headers = ("Dataset", "State", "Size", "Latest data", "Last fetched (UTC)")
    rows = []
    for result in results:
        state = result.get("State", "Unavailable")
        absent = "—" if state in {"Not initialized", "Migration needed"} else "Unavailable"
        amount = result.get("Storage bytes (total / table / indexes)", absent)
        amount = size(amount[0]) if isinstance(amount, tuple) else amount
        latest = result.get("Latest data", absent)
        latest = {"N/A (snapshot)": "N/A", "No active data": "No data"}.get(str(latest), latest)
        fetched = result.get("Last successful fetch (UTC)", absent)
        if isinstance(fetched, datetime):
            fetched = fetched.astimezone(UTC).strftime("%Y-%m-%d %H:%M")
        values = [result["Dataset"], state, amount, latest, fetched]
        rows.append(
            [
                "".join(c if ord(c) >= 32 and ord(c) != 127 else "?" for c in display(v))
                for v in values
            ]
        )
    renderer = console(ctx)
    if renderer and renderer.width < 100:
        renderer.print(Text("Local datasets", style="bold"))
        renderer.print(Text("  |  ".join(headers), style="bold cyan"))
        for values in rows:
            style = {"Ready": "green", "Migration needed": "yellow", "Not initialized": "dim"}.get(
                values[1], "red"
            )
            line = Text()
            for index, value in enumerate(values):
                if index:
                    line.append("  |  ", style="dim")
                line.append(value, style=style if index == 1 else "")
            renderer.print(line, overflow="fold")
    elif renderer:
        table = Table(title="Local datasets", box=None, padding=(0, 1), expand=False)
        for header in headers:
            table.add_column(header, overflow="fold", no_wrap=False)
        for values in rows:
            style = {"Ready": "green", "Migration needed": "yellow", "Not initialized": "dim"}.get(
                values[1], "red"
            )
            table.add_row(*[Text(v, style=style if i == 1 else "") for i, v in enumerate(values)])
        renderer.print(table)
    else:
        width = max(20, shutil.get_terminal_size((80, 24)).columns)
        click.echo("Local datasets")
        for values in [headers, *rows]:
            click.echo(textwrap.fill("  |  ".join(values), width=width, subsequent_indent="  "))
    click.echo("Observed at: " + display(datetime.now(UTC)))
    for result in results:
        for key in ("Detail", "Recorded history compatibility"):
            if result.get(key):
                click.echo(f"{result['Dataset']}: {display(result[key])}", err=True)
        if ctx.obj.get("verbose"):
            for key in ("Recorded spec versions", "Query seconds"):
                if key in result:
                    click.echo(f"{result['Dataset']} · {key}: {display(result[key])}")
    if not ctx.obj.get("quiet"):
        click.echo(
            "Ready does not imply complete coverage. Last fetched means successful fetch (including empty)."
        )
        click.echo("N/A = snapshot; — = not initialized/not inspected. Details: inspect DATASET")
