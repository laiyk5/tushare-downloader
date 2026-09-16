"""Native setup interface. Database rules belong to setup_service."""

import asyncio
from dataclasses import replace
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, Static

from .setup_service import SetupSession
from .setup_wizard import selected_settings


class ConfirmTarget(ModalScreen[bool]):
    BINDINGS = [("escape", "cancel", "Back")]
    DEFAULT_CSS = """
    ConfirmTarget { align: center middle; background: $background 80%; }
    ConfirmTarget > VerticalScroll { width: 90%; max-width: 65; height: auto;
        max-height: 90%; padding: 1 2; border: round $warning; background: $surface; }
    ConfirmTarget Button { width: 100%; }
    """

    def __init__(self, target):
        super().__init__()
        self.target = target

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static("Apply database changes", classes="heading")
            yield Static("Completed changes will remain if a later step fails.")
            yield Label("Type the target database: " + self.target)
            yield Input(id="confirmation")
            yield Button("Back", id="confirm_back")
            yield Button("Apply changes", id="confirm_apply", variant="warning", disabled=True)

    @on(Input.Changed, "#confirmation")
    def validate_target(self, event):
        self.query_one("#confirm_apply", Button).disabled = event.value != self.target

    @on(Button.Pressed, "#confirm_back")
    def action_cancel(self):
        self.dismiss(False)

    @on(Button.Pressed, "#confirm_apply")
    def confirm(self):
        if self.query_one("#confirmation", Input).value == self.target:
            self.dismiss(True)


class Information(ModalScreen[None]):
    BINDINGS = [("escape", "close", "Back")]
    DEFAULT_CSS = """
    Information { align: center middle; background: $background 80%; }
    Information > VerticalScroll { width: 90%; max-width: 70; height: auto;
        max-height: 90%; padding: 1 2; background: $surface; border: round $accent; }
    """

    def compose(self):
        with VerticalScroll():
            yield Static(
                "Tab / Shift+Tab: move focus\nMouse: select a field directly\n"
                "Enter: activate a focused button\nEsc: close a dialog / request exit\n"
                "Edits require a fresh check. Database changes require confirmation."
            )
            yield Button("Back", id="info_back")

    @on(Button.Pressed, "#info_back")
    def action_close(self):
        self.dismiss(None)


class SetupApp(App):
    TITLE = "tushare-downloader · setup"
    BINDINGS = [("f1", "help", "Keys"), ("escape", "request_exit", "Exit")]
    ENABLE_COMMAND_PALETTE = False
    CSS = """
    #navigation { height: auto; }
    #navigation Button { width: 1fr; min-width: 8; padding: 0; }
    #pages { height: 1fr; }
    .page { padding: 0 1; }
    .page Label { height: auto; margin-top: 1; }
    .page Input { width: 100%; }
    .heading { text-style: bold; color: $accent; margin: 1 0; }
    .page Button { width: 100%; margin-top: 1; }
    #resize_notice { background: $warning; color: $text; height: auto; }
    #status, #log_path { height: auto; padding: 0 1; }
    #log_path { color: $text-muted; }
    """

    def __init__(self, *, config_path=None, values=None, session_factory=None, auto_check=False):
        super().__init__()
        self.config_path = Path(config_path or ".env").absolute()
        self.values = dict(values or {})
        self.original_password = self.values.get("PGPASSWORD", "")
        self.session_factory = session_factory or SetupSession
        self.session = None
        self.inspection = None
        self.auto_check = auto_check
        self.closing = False
        self.applied = False
        self.can_apply = False
        self.generation = 0
        self.dirty = True
        self.busy = False

    def compose(self):
        yield Header(show_clock=False)
        yield Static("Resize required: at least 40 columns × 20 rows.", id="resize_notice")
        with Horizontal(id="navigation"):
            for page in ("connection", "access", "review", "result"):
                yield Button(page.capitalize(), id="nav_" + page)
        yield Static("Not checked", id="status")
        with Container(id="pages"):
            with VerticalScroll(id="connection", classes="page"):
                for identity, title in (
                    ("host", "Server host"),
                    ("port", "Server port"),
                    ("database", "Target database"),
                    ("writer", "Writer account"),
                    ("sslmode", "SSL mode"),
                ):
                    yield Label(title)
                    yield Input(
                        id=identity,
                        value=self.values.get(
                            {
                                "host": "PGHOST",
                                "port": "PGPORT",
                                "database": "PGDATABASE",
                                "writer": "PGUSER",
                                "sslmode": "PGSSLMODE",
                            }[identity],
                            {
                                "host": "",
                                "port": "5432",
                                "database": "tushare",
                                "writer": "tushare_writer",
                                "sslmode": "prefer",
                            }[identity],
                        ),
                    )
                yield Button("Check connection", id="check", variant="primary")
                yield Button("Access settings", id="access_button")
                yield Button("New connection", id="new_connection")
            with VerticalScroll(id="access", classes="page"):
                yield Static("Credentials are temporary; existing passwords are never reset.")
                for identity, title, secret in (
                    ("writer_password", "Writer password", True),
                    ("reader", "Reader account", False),
                    ("reader_password", "Reader password for creation / verification", True),
                    ("reader_confirm", "Confirm new reader password", True),
                    ("admin_user", "Administrator account (only when needed)", False),
                    ("admin_password", "Administrator password", True),
                    ("maintenance", "Maintenance database", False),
                ):
                    yield Label(title)
                    yield Input(
                        id=identity,
                        password=secret,
                        value={
                            "reader": self.values.get("SETUP_READER_USER", "tushare_reader"),
                            "maintenance": "postgres",
                        }.get(identity, ""),
                    )
                yield Button("Recheck and review", id="recheck", variant="primary")
            with VerticalScroll(id="review", classes="page"):
                yield Static("Check the connection before reviewing changes.", id="review_text")
                yield Button("Apply changes", id="apply", variant="warning", disabled=True)
                yield Button("Back to connection", id="review_back")
            with VerticalScroll(id="result", classes="page"):
                yield Static("No operations performed.", id="result_text")
                yield Button("Recheck and review", id="retry")
                yield Button("Finish", id="finish")
        yield Static("Log: not started", id="log_path")
        yield Footer()

    def on_mount(self):
        self.show_page("connection")
        self.update_size()
        if self.auto_check and all(self.values.get(k) for k in ("PGHOST", "PGDATABASE", "PGUSER")):
            self.run_worker(self.check_connection(), group="inspection")

    def show_page(self, page):
        for widget in self.query(".page"):
            widget.display = widget.id == page
        self.page = page

    def update_size(self, size=None):
        size = size or self.size
        sufficient = size.width >= 40 and size.height >= 20
        self.query_one("#resize_notice").display = not sufficient
        self.can_apply = (
            sufficient
            and not self.dirty
            and not self.busy
            and bool(self.inspection and self.inspection["actions"])
        )
        self.query_one("#apply", Button).disabled = not self.can_apply

    def on_resize(self, event):
        if self.is_mounted:
            self.update_size(event.size)

    @on(Input.Changed)
    def edited(self, event):
        self.generation += 1
        self.dirty = True
        self.query_one("#status", Static).update("Edited — check again before applying.")
        self.update_size()

    @on(Button.Pressed)
    def navigate(self, event):
        identity = event.button.id or ""
        if identity.startswith("nav_"):
            self.show_page(identity[4:])
        elif identity == "access_button":
            self.show_page("access")
        elif identity == "review_back":
            self.show_page("connection")
        elif identity in {"check", "recheck", "retry"} and not self.busy:
            self.run_worker(self.check_connection(), group="inspection")
        elif identity == "new_connection" and not self.busy:
            self.new_connection()
        elif identity == "apply" and self.can_apply:
            self.confirm_target(self.query_one("#database", Input).value)
        elif identity == "finish":
            self.action_request_exit()

    def confirm_target(self, target):
        self.push_screen(ConfirmTarget(target), self.confirmed)

    def confirmed(self, accepted):
        if accepted and self.can_apply:
            self.applied = True

    def action_help(self):
        self.push_screen(Information())

    def action_request_exit(self):
        self.closing = True
        self.generation += 1
        if self.session:
            self.session.cancelled = True
        self.exit(0)

    def new_connection(self):
        self.generation += 1
        self.inspection = None
        self.original_password = ""
        self.values.pop("PGPASSWORD", None)
        destination = self.config_path.parent / ".env.new"
        suffix = 0
        while destination.exists() or destination.is_symlink():
            suffix += 1
            destination = self.config_path.parent / f".env.new.{suffix}"
        self.config_path = destination
        for identity in (
            "writer_password",
            "reader_password",
            "reader_confirm",
            "admin_password",
            "admin_user",
        ):
            self.query_one("#" + identity, Input).value = ""
        self.dirty = True
        self.update_size()
        self.query_one("#status", Static).update(
            "New connection — original configuration and database preserved."
        )
        self.show_page("connection")

    async def check_connection(self):
        if self.busy or self.closing:
            return
        generation = self.generation

        def value(identity):
            return self.query_one("#" + identity, Input).value

        selected = dict(self.values)
        for identity, key in (
            ("host", "PGHOST"),
            ("port", "PGPORT"),
            ("database", "PGDATABASE"),
            ("writer", "PGUSER"),
            ("sslmode", "PGSSLMODE"),
        ):
            selected[key] = value(identity)
        selected["PGPASSWORD"] = value("writer_password") or self.original_password
        credentials = {"reader": {"password": value("reader_password")}}
        if value("admin_user"):
            credentials["admin"] = {
                "user": value("admin_user"),
                "password": value("admin_password"),
                "maintenance_database": value("maintenance") or "postgres",
            }
        try:
            settings = replace(
                selected_settings(selected), log_dir=Path(selected.get("LOG_DIR", "logs"))
            )
            candidate = self.session_factory(settings, value("reader"), credentials, mode="tui")
        except (ValueError, OSError):
            self.query_one("#status", Static).update(
                "Check the connection values and log directory."
            )
            return
        self.query_one("#log_path", Static).update("Log: " + str(candidate.log.path))
        self.query_one("#status", Static).update("Checking — no database changes.")
        self.busy = True
        self.update_size()
        try:
            inspection = await asyncio.to_thread(candidate.inspect)
        except (RuntimeError, OSError):
            inspection = {"readiness": "unknown", "actions": [], "facts": None}
        finally:
            self.busy = False
        if self.closing or generation != self.generation:
            candidate.close()
            self.update_size()
            return
        if self.session:
            self.session.close()
        self.session = candidate
        self.inspection = inspection
        self.dirty = inspection["readiness"] not in {"ready", "needs_configuration"}
        self.query_one("#status", Static).update(
            inspection["readiness"].replace("_", " ").capitalize()
        )
        self.query_one("#review_text", Static).update(
            "Target: "
            + selected["PGHOST"]
            + "/"
            + selected["PGDATABASE"]
            + "\n"
            + (
                "Necessary changes:\n" + "\n".join(inspection["actions"])
                if inspection["actions"]
                else "No database changes. Reader login may not have been checked."
            )
        )
        self.update_size()
