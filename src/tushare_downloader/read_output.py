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
