"""Native setup interface. Database rules belong to setup_service."""

import asyncio
import os
from dataclasses import replace
from pathlib import Path

import click
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Footer, Header, Input, Label, Select, Static

from .setup_config import read_config, save_config
from .setup_events import SetupLog
from .setup_inputs import connection_errors, selected_settings
from .setup_presentation import configuration_preview, database_preview
from .setup_service import SetupSession


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


class Decision(ModalScreen[bool]):
    BINDINGS = [("escape", "cancel", "Back")]
    DEFAULT_CSS = """
    Decision { align: center middle; background: $background 80%; }
    Decision > VerticalScroll { width: 90%; max-width: 70; height: auto;
        max-height: 90%; padding: 1 2; background: $surface; border: round $warning; }
    Decision Button { width: 100%; }
    """

    def __init__(self, title, detail, action):
        super().__init__()
        self.heading, self.detail, self.action_label = title, detail, action

    def compose(self):
        with VerticalScroll():
            yield Static(self.heading, classes="heading", markup=False)
            yield Static(self.detail, markup=False)
            yield Button("Back", id="decision_back")
            yield Button(self.action_label, id="decision_yes", variant="warning")

    @on(Button.Pressed, "#decision_back")
    def action_cancel(self):
        self.dismiss(False)

    @on(Button.Pressed, "#decision_yes")
    def accept(self):
        self.dismiss(True)


class SetupApp(App):
    TITLE = "tushare-downloader · setup"
    BINDINGS = [
        ("f1", "help", "Keys"),
        ("escape", "request_exit", "Exit"),
        ("ctrl+c", "interrupt", "Interrupt"),
    ]
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
    #connection_body, #connection_fields { height: auto; width: 100%; }
    #connection_summary { height: auto; margin-top: 1; padding: 1; background: $surface; }
    .wide #navigation { dock: left; layout: vertical; width: 18; height: 1fr; }
    .wide #navigation Button { width: 100%; height: 3; }
    .wide #connection_body { layout: horizontal; }
    .wide #connection_fields { width: 1fr; }
    .wide #connection_summary { width: 1fr; margin-left: 2; }
    """

    def __init__(
        self,
        *,
        config_path=None,
        values=None,
        session_factory=None,
        auto_check=False,
        event_log=None,
        environ=None,
    ):
        super().__init__()
        self.event_log = event_log
        self.environment = dict(environ or {})
        self.runtime_error = False
        self.config_path = Path(config_path or ".env").absolute()
        self.values = dict(values or {})
        self.original_password = self.values.get("PGPASSWORD", "")
        self.session_factory = session_factory or SetupSession
        self.session = None
        self.active_session = None
        self.inspection = None
        self.auto_check = auto_check
        self.closing = False
        self.applied = False
        self.can_apply = False
        self.generation = 0
        self.dirty = True
        self.busy = False
        self.executing = False
        self.final_result = {}
        self.completed_history = []
        self.review_number = 0
        self.configuration_status = "not_saved"
        self.events = []
        self.checked_values = None
        self.field_values = {}
        self.pending_exit = None
        try:
            self.config_original, self.file_values = read_config(self.config_path)
            self.file_error = None
        except (ValueError, OSError):
            self.config_original, self.file_values = None, {}
            self.file_error = "Cannot safely edit this configuration; choose another file."

    def compose(self):
        yield Header(show_clock=False)
        yield Static("Resize required: at least 40 columns × 20 rows.", id="resize_notice")
        with Horizontal(id="navigation"):
            for page in ("connection", "access", "review", "result"):
                yield Button(page.capitalize(), id="nav_" + page)
        yield Static("Not checked", id="status")
        with Container(id="pages"):
            with VerticalScroll(id="connection", classes="page"):
                with Container(id="connection_body"):
                    with Vertical(id="connection_fields"):
                        for identity, title in (
                            ("host", "Server host"),
                            ("port", "Server port"),
                            ("database", "Target database"),
                            ("writer", "Writer account"),
                            ("sslmode", "SSL mode"),
                        ):
                            yield Label(title, id="label_" + identity)
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
                    yield Static(
                        "Not checked.\n\nChecks inspect database structure and permissions, not data coverage.",
                        id="connection_summary",
                        markup=False,
                    )
            with VerticalScroll(id="access", classes="page"):
                yield Static("Credentials are temporary; existing passwords are never reset.")
                yield Label("Writer credential choice")
                yield Select(
                    [
                        ("Keep current credential", "keep"),
                        ("Replace for this connection", "replace"),
                        ("Clear for this connection", "clear"),
                    ],
                    id="writer_password_mode",
                    allow_blank=False,
                    value="keep" if self.original_password else "replace",
                )
                for identity, title, secret in (
                    ("writer_password", "Writer password", True),
                    ("writer_confirm", "Confirm new writer password", True),
                    ("reader", "Reader account", False),
                    ("reader_password", "Reader password for creation / verification", True),
                    ("reader_confirm", "Confirm new reader password", True),
                    ("admin_user", "Administrator account (only when needed)", False),
                    ("admin_password", "Administrator password", True),
                    ("maintenance", "Maintenance database", False),
                ):
                    yield Label(title, id="label_" + identity)
                    yield Input(
                        id=identity,
                        password=secret,
                        value={
                            "reader": self.values.get("SETUP_READER_USER", "tushare_reader"),
                            "maintenance": "postgres",
                        }.get(identity, ""),
                    )
                yield Checkbox(
                    "Create writer without a password; I confirm other authentication is configured",
                    id="writer_passwordless",
                )
                yield Checkbox(
                    "Create reader without a password; I confirm other authentication is configured",
                    id="reader_passwordless",
                )
                yield Static("", id="credential_notice")
                yield Button("Recheck and review", id="recheck", variant="primary")
                yield Button("Retry access verification", id="verify_again", disabled=True)
            with VerticalScroll(id="review", classes="page"):
                yield Static("Check the connection before reviewing changes.", id="review_text")
                yield Button("Apply changes", id="apply", variant="warning", disabled=True)
                yield Button("Back to connection", id="review_back")
                yield Label("Configuration destination")
                yield Input(str(self.config_path), id="save_path")
                yield Checkbox("Save writer password (private file)", id="save_password")
                yield Checkbox("Clear the old stored writer password", id="clear_password")
                yield Static("Admin and reader passwords are never saved.", id="save_notice")
                yield Button("Review configuration save", id="save", disabled=True)
            with VerticalScroll(id="result", classes="page"):
                yield Static("No operations performed.", id="result_text")
                yield Button("Recheck and review", id="retry")
                yield Button("Edit verification credentials", id="fix_access", disabled=True)
                yield Button("Finish", id="finish")
        yield Static(
            "Log: " + str(self.event_log.path) if self.event_log else "Log: not started",
            id="log_path",
            markup=False,
        )
        yield Footer()

    def on_mount(self):
        for identity in (
            "review_text",
            "connection_summary",
            "status",
            "result_text",
            "save_notice",
            "log_path",
        ):
            self.query_one("#" + identity, Static).markup = False
        self.show_page("connection")
        self.update_size()
        # Initial widget change events must settle before the startup explanation.
        self.call_after_refresh(self.startup_check)

    def startup_check(self):
        if self.file_error:
            self.query_one("#status", Static).update(self.file_error)
            return
        required = ("PGHOST", "PGDATABASE", "PGUSER")
        missing = [key for key in required if not self.values.get(key)]
        supported = ("PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD", "PGSSLMODE")
        if missing:
            if "DATABASE_URL" in self.values and not any(key in self.values for key in supported):
                message = "DATABASE_URL is not supported. Configure PGHOST, PGDATABASE and PGUSER."
            elif any(key in self.values for key in supported):
                message = "Complete connection configuration: " + ", ".join(missing)
            else:
                message = "No connection configured. Enter the server and target account details."
            self.query_one("#status", Static).update(message)
        elif self.auto_check:
            self.run_worker(self.check_connection(), group="inspection")

    def show_page(self, page):
        for widget in self.query(".page"):
            widget.display = widget.id == page
        self.page = page

    def update_size(self, size=None):
        size = size or self.size
        self.screen_stack[0].set_class(size.width >= 100, "wide")
        sufficient = size.width >= 40 and size.height >= 20
        self.query_one("#resize_notice").display = not sufficient
        self.can_apply = (
            sufficient
            and not self.dirty
            and not self.busy
            and bool(self.inspection and self.inspection["actions"])
            and self.credentials_ready()
        )
        self.query_one("#apply", Button).disabled = not self.can_apply
        self.query_one("#save", Button).disabled = self.dirty or self.busy
        recovering = bool(self.session and getattr(self.session, "verification_pending", False))
        self.query_one("#verify_again", Button).disabled = (
            self.busy or not recovering or not self.same_target()
        )
        self.query_one("#fix_access", Button).disabled = self.busy or not recovering
        self.update_access_fields(recovering)
        for identity in ("nav_review", "nav_result"):
            self.query_one("#" + identity, Button).disabled = (
                self.inspection is None if identity == "nav_review" else not bool(self.final_result)
            )

    def update_access_fields(self, recovering):
        actions = self.inspection["actions"] if self.inspection else []
        unknown = not self.inspection or self.inspection["readiness"] in {"unknown", "unsupported"}
        admin_needed = unknown or any(
            a in actions for a in ("create-writer", "create-reader", "create-database")
        )
        reader_needed = recovering or any(a in actions for a in ("create-reader", "grants"))
        for field, visible in (
            ("admin_user", admin_needed),
            ("admin_password", admin_needed),
            ("maintenance", admin_needed),
            ("reader_password", reader_needed),
        ):
            self.query_one("#" + field).display = visible
            self.query_one("#label_" + field).display = visible
        for role in ("writer", "reader"):
            creating = "create-" + role in actions
            for identity in (
                role + "_confirm",
                "label_" + role + "_confirm",
                role + "_passwordless",
            ):
                self.query_one("#" + identity).display = creating

    def on_resize(self, event):
        if self.is_mounted:
            self.update_size(event.size)

    @on(Input.Changed)
    def edited(self, event):
        identity = event.input.id
        event.input.border_subtitle = None
        if identity in {"confirmation", "save_path"}:
            return
        old = self.field_values.get(identity)
        self.field_values[identity] = event.value
        if (
            old is not None
            and old != event.value
            and identity in {"host", "port", "database", "writer", "reader", "admin_user"}
        ):
            related = {
                "writer": ("writer_password", "writer_confirm"),
                "reader": ("reader_password", "reader_confirm"),
                "admin_user": ("admin_password",),
            }.get(
                identity,
                (
                    "writer_password",
                    "writer_confirm",
                    "reader_password",
                    "reader_confirm",
                    "admin_password",
                ),
            )
            if "writer_password" in related:
                self.original_password = ""
            for target in related:
                self.query_one("#" + target, Input).value = ""
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
        elif identity == "fix_access":
            self.show_page("access")
        elif identity == "verify_again" and not self.busy:
            self.run_worker(self.retry_access(), group="verification")
        elif identity == "save" and not self.dirty and not self.busy:
            self.prepare_save()
        elif identity == "finish":
            self.action_request_exit()

    def confirm_target(self, target):
        self.push_screen(ConfirmTarget(target), self.confirmed)

    def confirmed(self, accepted):
        if accepted and self.can_apply:
            self.applied = True
            self.busy = True
            self.executing = True
            self.update_size()
            for field in self.query("Input, Select, Checkbox"):
                field.disabled = True
            self.show_page("result")
            self.run_worker(self.execute_plan(), group="execution")

    def action_help(self):
        self.push_screen(Information())

    def action_request_exit(self):
        self.push_screen(
            Decision(
                "Exit setup?",
                "Unsaved configuration will be discarded. Completed database changes remain."
                + (
                    " An operation is running; cancellation must finish first." if self.busy else ""
                ),
                "Cancel operation and exit" if self.busy else "Exit",
            ),
            self.exit_confirmed,
        )

    def exit_confirmed(self, accepted):
        if not accepted:
            return
        code = 130 if self.busy else self.final_result.get("exit_code", 0)
        if self.configuration_status == "failed" or self.runtime_error:
            code = 1
        self.request_stop(code)

    def action_interrupt(self):
        self.request_stop(130)

    def request_stop(self, code):
        self.closing = True
        self.pending_exit = code
        self.generation += 1
        for session in (self.session, self.active_session):
            if session:
                if hasattr(session, "request_cancel"):
                    session.request_cancel()
                else:
                    session.cancelled = True
        if self.busy:
            self.query_one("#status", Static).update(
                "Stopping — previously completed changes remain."
            )
        else:
            if self.session:
                self.session.close()
            self.exit(code)

    def new_connection(self):
        self.generation += 1
        self.inspection = None
        self.original_password = ""
        self.query_one("#writer_password_mode", Select).value = "replace"
        self.values.pop("PGPASSWORD", None)
        destination = self.config_path.parent / ".env.new"
        suffix = 0
        while destination.exists() or destination.is_symlink():
            suffix += 1
            destination = self.config_path.parent / f".env.new.{suffix}"
        self.config_path = destination
        self.config_original, self.file_values, self.file_error = None, {}, None
        self.query_one("#save_path", Input).value = str(destination)
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
        if (
            self.session
            and getattr(self.session, "verification_pending", False)
            and self.same_target()
        ):
            await self.retry_access()
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
        selected["PGPASSWORD"] = self.writer_password()
        credentials = {"reader": {"password": value("reader_password")}}
        for role in ("writer", "reader"):
            if self.query_one("#" + role + "_passwordless", Checkbox).value:
                credentials.setdefault(role, {})["allow_passwordless_creation"] = True
        if value("admin_user"):
            credentials["admin"] = {
                "user": value("admin_user"),
                "password": value("admin_password"),
                "maintenance_database": value("maintenance") or "postgres",
            }
        errors = connection_errors(selected, value("reader"), credentials.get("admin"))
        if errors:
            for field, message in errors.items():
                self.query_one("#" + field, Input).border_subtitle = message
            field = next(iter(errors))
            self.show_page(
                "connection"
                if field in {"host", "port", "database", "writer", "sslmode"}
                else "access"
            )
            self.query_one("#" + field, Input).focus()
            self.query_one("#status", Static).update(errors[field])
            return
        try:
            settings = replace(
                selected_settings(selected), log_dir=Path(selected.get("LOG_DIR", "logs"))
            )
            candidate = self.session_factory(
                settings, value("reader"), credentials, mode="tui", event_log=self.event_log
            )
            candidate.observer = self.service_event
        except (ValueError, OSError):
            self.query_one("#status", Static).update(
                "Check the connection values and log directory."
            )
            return
        self.active_session = candidate
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
            self.active_session = None
        if self.closing or generation != self.generation:
            candidate.close()
            self.update_size()
            if self.closing:
                self.exit(self.pending_exit or 0)
            return
        if self.session:
            self.session.close()
        self.session = candidate
        self.review_number += 1
        self.events = []
        self.checked_values = {
            k: selected[k]
            for k in ("PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGSSLMODE", "PGPASSWORD")
        }
        self.checked_values["SETUP_READER_USER"] = value("reader")
        self.inspection = inspection
        for role in ("writer", "reader"):
            creating = "create-" + role in inspection["actions"]
            for identity in (
                role + "_confirm",
                "label_" + role + "_confirm",
                role + "_passwordless",
            ):
                self.query_one("#" + identity).display = creating
        self.dirty = inspection["readiness"] not in {"ready", "needs_configuration"}
        self.query_one("#status", Static).update(
            inspection["readiness"].replace("_", " ").capitalize()
        )
        self.query_one("#connection_summary", Static).update(
            inspection["readiness"].replace("_", " ").capitalize()
            + "\n\n"
            + "Target: "
            + selected["PGHOST"]
            + "/"
            + selected["PGDATABASE"]
            + "\nWriter: "
            + selected["PGUSER"]
            + "\nReader: "
            + value("reader")
            + "\n\n"
            + (
                "Necessary changes: " + ", ".join(inspection["actions"])
                if inspection["actions"]
                else "No changes planned."
            )
            + "\n\nReader login is separate from permission inspection."
        )
        self.query_one("#review_text", Static).update(
            database_preview(settings, value("reader"), inspection)
        )
        self.update_size()

    def service_event(self, event, fields):
        if event not in {"step_started", "step_finished", "verification_finished"}:
            return
        text = (
            (fields.get("action") or "Access verification")
            + ": "
            + fields.get("outcome", "running")
        )
        self.call_from_thread(self.display_event, text)

    def remember_completed(self, result):
        actions = result.get("completed", [])
        if not actions:
            return
        record = next(
            (item for item in self.completed_history if item["review"] == self.review_number), None
        )
        if record is None:
            selected = self.checked_values or {}
            record = {
                "review": self.review_number,
                "target": selected.get("PGHOST", "?")
                + ":"
                + str(selected.get("PGPORT", "?"))
                + "/"
                + selected.get("PGDATABASE", "?"),
                "completed": [],
            }
            self.completed_history.append(record)
        record["completed"].extend(
            action for action in actions if action not in record["completed"]
        )

    def previous_completion_lines(self):
        return [
            "Completed earlier · " + item["target"] + ": " + ", ".join(item["completed"])
            for item in self.completed_history
            if item["review"] != self.review_number
        ]

    def display_event(self, text):
        self.events.append(text)
        self.query_one("#result_text", Static).update(
            "\n".join(self.previous_completion_lines() + self.events)
        )

    async def execute_plan(self):
        try:
            result = await asyncio.to_thread(self.session.apply)
        except Exception:
            # Secrets and arbitrary driver exception text never reach the UI.
            result = {"exit_code": 1, "unknown": ["Execution interrupted; recheck the database."]}
        self.present_result(result)

    def present_result(self, result):
        self.remember_completed(result)
        self.final_result = result
        self.busy = self.executing = False
        self.dirty = result["exit_code"] != 0
        if self.inspection:
            self.inspection["actions"] = []
        for field in self.query("Input, Select, Checkbox"):
            field.disabled = False
        rows = self.previous_completion_lines()
        if result.get("reason_code"):
            rows.append("Reason: " + result["reason_code"])
        for key in ("completed", "failed", "unknown", "not_attempted"):
            rows.append(
                key.replace("_", " ").capitalize()
                + ": "
                + (", ".join(result.get(key, [])) or "None")
            )
        for key in ("writer_verification", "reader_verification"):
            rows.append(key.replace("_", " ").capitalize() + ": " + result.get(key, "not_checked"))
        self.query_one("#result_text", Static).update("\n".join(rows))
        self.query_one("#status", Static).update(
            "Completed" if result["exit_code"] == 0 else "Incomplete — completed changes remain"
        )
        self.update_size()
        if self.closing:
            self.session.close()
            self.exit(self.pending_exit if self.pending_exit is not None else result["exit_code"])

    def same_target(self):
        if not self.checked_values:
            return False
        return all(
            self.query_one("#" + field, Input).value == str(self.checked_values.get(key, ""))
            for field, key in (
                ("host", "PGHOST"),
                ("port", "PGPORT"),
                ("database", "PGDATABASE"),
                ("writer", "PGUSER"),
                ("sslmode", "PGSSLMODE"),
                ("reader", "SETUP_READER_USER"),
            )
        )

    async def retry_access(self):
        if (
            self.busy
            or not self.same_target()
            or not getattr(self.session, "verification_pending", False)
        ):
            return
        self.busy = True
        self.update_size()
        writer_password = self.writer_password()
        reader_password = self.query_one("#reader_password", Input).value
        for field in self.query("Input, Select, Checkbox"):
            field.disabled = True
        self.show_page("result")
        self.query_one("#status", Static).update("Verifying access — no database changes.")
        try:
            result = await asyncio.to_thread(
                self.session.retry_verification,
                writer_password=writer_password,
                reader_password=reader_password,
            )
        except Exception:
            result = self.final_result | {"exit_code": 1, "reason_code": "verification_failed"}
        if result["exit_code"] == 0:
            self.checked_values["PGPASSWORD"] = writer_password
        self.present_result(result)

    def prepare_save(self):
        destination = Path(self.query_one("#save_path", Input).value).absolute()
        try:
            if destination != self.config_path:
                self.config_original, self.file_values = read_config(destination)
                self.config_path = destination
                self.file_error = None
            if self.file_error:
                raise ValueError(self.file_error)
            updates = self.configuration_updates()
        except (ValueError, OSError):
            self.query_one("#save_notice", Static).update(
                "Cannot save safely. Review the destination and password choices."
            )
            return
        preview, _, _ = configuration_preview(
            self.file_values, self.values, self.checked_values, updates, self.environment
        )
        self.push_screen(
            Decision("Save configuration?", str(destination) + "\n\n" + preview, "Save"),
            self.save_configuration,
        )

    def configuration_updates(self):
        updates = dict(self.checked_values or {})
        store = self.query_one("#save_password", Checkbox).value
        clear = self.query_one("#clear_password", Checkbox).value
        if store and clear:
            raise ValueError("Choose save or clear, not both.")
        if clear:
            updates["PGPASSWORD"] = ""
        elif not store:
            updates.pop("PGPASSWORD", None)
        return updates

    def save_configuration(self, accepted):
        if not accepted or self.dirty or self.busy or not self.checked_values:
            return
        try:
            updates = self.configuration_updates()
            if any(self.file_values.get(k) != v for k, v in updates.items()):
                save_config(self.config_path, self.config_original, updates)
                self.config_original, self.file_values = read_config(self.config_path)
            _, matches, overridden = configuration_preview(
                self.file_values, self.values, self.checked_values, updates, self.environment
            )
            self.configuration_status = (
                "saved_overridden" if overridden else ("saved" if matches else "saved_unverified")
            )
            explanation = (
                "Saved, overridden by environment."
                if overridden
                else "Saved; effective configuration matches the verified selection."
                if matches
                else "Saved; effective configuration differs from the verified selection (check credentials)."
            )
            self.query_one("#save_notice", Static).update(
                explanation + "\n" + str(self.config_path) + "\nUse -c to select this file."
            )
            if self.event_log:
                try:
                    self.event_log.emit(
                        "configuration_saved",
                        outcome="completed",
                        configuration=self.configuration_status,
                    )
                except OSError:
                    self.runtime_error = True
                    self.query_one("#save_notice", Static).update(
                        "Configuration saved, but writing its log event failed."
                    )
        except (OSError, ValueError):
            self.configuration_status = "failed"
            self.query_one("#save_notice", Static).update(
                "Configuration was not saved. Recheck the file or choose another path; database changes remain."
            )

    def writer_password(self):
        choice = self.query_one("#writer_password_mode", Select).value
        if choice == "keep":
            return self.original_password
        if choice == "clear":
            return ""
        return self.query_one("#writer_password", Input).value

    def credentials_ready(self):
        if not self.inspection:
            return False
        for role in ("writer", "reader"):
            if "create-" + role not in self.inspection["actions"]:
                continue
            password = (
                self.writer_password()
                if role == "writer"
                else self.query_one("#reader_password", Input).value
            )
            passwordless = self.query_one("#" + role + "_passwordless", Checkbox).value
            confirmation = self.query_one("#" + role + "_confirm", Input).value
            if (passwordless and password) or (
                not passwordless and (not password or password != confirmation)
            ):
                self.query_one("#credential_notice", Static).update(
                    "For new "
                    + role
                    + ": confirm a matching password, or explicitly choose passwordless creation."
                )
                return False
        self.query_one("#credential_notice", Static).update("")
        return True

    @on(Select.Changed, "#writer_password_mode")
    def password_mode_changed(self, event):
        self.generation += 1
        self.dirty = True
        self.update_size()

    @on(Checkbox.Changed)
    def creation_mode_changed(self, event):
        if event.checkbox.id in {"writer_passwordless", "reader_passwordless"}:
            self.generation += 1
            self.dirty = True
            self.update_size()


def run_tui(ctx):
    path = Path(ctx.obj.get("env_file") or ".env").absolute()
    invalid_file = False
    try:
        _, file_values = read_config(path)
    except (OSError, ValueError):
        file_values = {}
        invalid_file = True
    values = file_values | dict(os.environ)
    if values.get("PLAIN", "false") in {"true", "1"}:
        raise click.UsageError(
            "Interactive setup conflicts with PLAIN; disable it or use --headless."
        )
    try:
        log = SetupLog(Path(values.get("LOG_DIR", "logs")), "tui", {})
    except OSError:
        raise click.ClickException("Cannot create the private setup log.") from None
    app = SetupApp(
        config_path=path,
        values=values,
        auto_check=not invalid_file,
        event_log=log,
        environ=os.environ,
    )
    try:
        result = app.run()
        log.emit(
            "session_finished",
            exit_code=result or 0,
            outcome="completed" if result == 0 else "incomplete",
            configuration=app.configuration_status,
            completed_history=getattr(app, "completed_history", []),
            readiness=app.final_result.get(
                "readiness", (getattr(app, "inspection", None) or {}).get("readiness", "unknown")
            ),
            reason_code=app.final_result.get("reason_code"),
            writer_verification=app.final_result.get("writer_verification", "not_checked"),
            reader_verification=app.final_result.get("reader_verification", "not_checked"),
            completed=app.final_result.get("completed", []),
            failed=app.final_result.get("failed", []),
            unknown=app.final_result.get("unknown", []),
            not_attempted=app.final_result.get("not_attempted", []),
        )
    except OSError:
        result = 1
        click.echo("Setup log could not be completed; review the result summary.", err=True)
    finally:
        log.close()
    click.echo(
        "Database setup: "
        + (
            "Completed"
            if result == 0 and app.final_result.get("exit_code") == 0
            else "Closed; review the results below"
        )
    )
    if app.checked_values:
        selected = app.checked_values
        click.echo("Target: " + selected["PGHOST"] + "/" + selected["PGDATABASE"])
    for key in ("completed", "failed", "unknown", "not_attempted"):
        if app.final_result.get(key):
            click.echo(key.replace("_", " ").capitalize() + ": " + ", ".join(app.final_result[key]))
    if app.final_result.get("reason_code"):
        click.echo("Reason: " + app.final_result["reason_code"], err=True)
    for key in ("writer_verification", "reader_verification"):
        click.echo(
            key.replace("_", " ").capitalize() + ": " + app.final_result.get(key, "not_checked")
        )
    for item in getattr(app, "completed_history", []):
        click.echo(
            "Completed in this session · " + item["target"] + ": " + ", ".join(item["completed"])
        )
    click.echo("Configuration: " + app.configuration_status)
    click.echo("Log: " + str(log.path))
    ctx.exit(result or 0)
