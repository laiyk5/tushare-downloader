"""Sequential human setup; database rules stay in SetupSession."""

import os
from dataclasses import replace
from pathlib import Path

import click
from rich.console import Console
from rich.text import Text

from .setup_config import KEYS, SAVE_KEYS, read_config, save_config
from .setup_events import SetupLog
from .setup_inputs import connection_errors, selected_settings
from .setup_presentation import configuration_preview, database_preview
from .setup_service import SetupSession

FIELDS = (
    ("PGHOST", "Server host", "localhost", "host"),
    ("PGPORT", "Server port", "5432", "port"),
    ("PGSSLMODE", "SSL mode", "prefer", "sslmode"),
    ("PGDATABASE", "Target database", "tushare", "database"),
    ("PGUSER", "Writer account", "tushare_writer", "writer"),
    ("SETUP_READER_USER", "Reader account", "tushare_reader", "reader"),
)
CODES = {
    "ready": 0,
    "needs_configuration": 4,
    "unknown": 1,
    "unsupported": 5,
    "migration_needed": 4,
}


def safe_text(value):
    return "".join(
        c if c in "\n\t" or (ord(c) >= 32 and not 127 <= ord(c) <= 159) else "?" for c in str(value)
    )


class Dialogue:
    def __init__(self, ctx, new=False):
        self.ctx = ctx
        self.new = new
        self.environment = dict(os.environ)
        self.path = Path(ctx.obj.get("env_file") or ".env").absolute()
        self.original = None
        self.file_values = {}
        self.values = {}
        self.credentials = {}
        self.dirty = False
        self.log = None
        self.session = None
        self.result = {}
        self.completed_history = []
        self.current_action = None
        self.plan_completed = []
        self.configuration = "not_saved"
        self.code = 0
        self.plain = bool(ctx.obj.get("plain"))
        self.console = Console(highlight=False)

    def say(self, text, style="", error=False):
        text = safe_text(text)
        if self.plain:
            click.echo(text, err=error)
        else:
            console = Console(stderr=True, highlight=False) if error else self.console
            rendered = Text()
            for index, line in enumerate(text.split("\n")):
                if index:
                    rendered.append("\n")
                stripped = line.lstrip()
                if stripped.startswith(
                    ("Target: ", "  Selected: ", "Selected: ", "Saved: ", "Effective after: ")
                ):
                    prefix, value = line.split(": ", 1)
                    rendered.append(prefix + ": ", "dim")
                    rendered.append(value, "magenta")
                elif stripped.startswith(("Before: ", "Impact: ", "File: ", "Current (")):
                    rendered.append(line, "dim")
                elif stripped.startswith(("Action: ", "After: ")):
                    rendered.append(line, "yellow")
                elif line.startswith(("Checking ", "Configuration plan:", "Review ")):
                    rendered.append(line, "bold cyan")
                else:
                    rendered.append(line, style)
            console.print(rendered, soft_wrap=False)

    def ask(self, text, default="", secret=False):
        if not secret:
            default = safe_text(default).replace("\n", "?").replace("\t", "?")
        self.say(text, "cyan")
        return click.prompt(
            ">",
            default=default,
            hide_input=secret,
            show_default=not secret,
            type=str,
        )

    def menu(self, text, options, default="q"):
        self.say(text, "bold cyan")
        for key, label in options.items():
            self.say(f"  [{key.upper()}] {label}")
        return click.prompt(
            "Choice", type=click.Choice(list(options), case_sensitive=False), default=default
        ).lower()

    def source(self):
        while True:
            try:
                self.original, self.file_values = read_config(self.path)
                break
            except (ValueError, OSError):
                self.say(
                    "Configuration cannot be read safely. It will not be ignored.", "red", True
                )
                if self.menu("Configuration", {"p": "Choose another file", "q": "Exit"}) == "q":
                    self.code = 2
                    return False
                self.path = Path(self.ask("Configuration path")).absolute()
        self.values = self.file_values | self.environment
        self.effective = dict(self.values)
        self.plain = (
            self.plain
            or self.values.get("PLAIN", "").lower() in {"true", "1"}
            or self.environment.get("TERM") == "dumb"
        )
        if self.values.get("DATABASE_URL"):
            self.say("DATABASE_URL is not supported; use PG* connection settings.", "yellow")
        if self.new:
            self.new_connection()
        self.log = SetupLog(Path(self.values.get("LOG_DIR", "logs")), "interactive", {})
        self.say("Log: " + str(self.log.path), "dim")
        self.say("Source: " + str(self.path), "dim")
        return True

    def new_connection(self):
        if (self.original is not None and self.ctx.obj.get("env_file") is not None) or any(
            self.values.get(k) for k in KEYS
        ):
            # A nonexistent explicit path remains the requested save destination.
            if self.original is not None or self.ctx.obj.get("env_file") is None:
                candidate = self.path.parent / ".env.new"
                index = 0
                while candidate.exists() or candidate.is_symlink():
                    index += 1
                    candidate = self.path.parent / f".env.new.{index}"
                self.path = candidate
                self.original, self.file_values = None, {}
        self.values.pop("PGPASSWORD", None)
        self.credentials = {}
        self.dirty = True
        self.new = True
        self.result = {}
        self.code = 0

    def field(self, field):
        key, label, default, error_key = field
        while True:
            value = self.ask(label, self.values.get(key, default))
            selected = self.values | {key: value}
            errors = connection_errors(
                selected, selected.get("SETUP_READER_USER", "tushare_reader")
            )
            if error_key in errors:
                self.say(errors[error_key], "red", True)
                continue
            if self.values.get(key) != value:
                if key in {"PGHOST", "PGPORT", "PGSSLMODE", "PGDATABASE", "PGUSER"}:
                    self.credentials = {}
                    self.values.pop("PGPASSWORD", None)
                elif key == "SETUP_READER_USER":
                    self.credentials.pop("reader", None)
                self.dirty = True
            self.values[key] = value
            return

    def password(self, role, creation=False):
        if not creation:
            option = self.menu(
                role.capitalize() + " credential (never changes an existing role password)",
                {"k": "Keep", "r": "Replace for this session", "c": "Clear temporary override"},
                "k",
            )
            if option == "k":
                return
            if option == "c":
                self.credentials.pop(role, None)
                return
        while True:
            password = self.ask(role.capitalize() + " password", secret=True)
            if not creation:
                self.credentials[role] = {"password": password}
                if role == "writer":
                    self.dirty = True
                return
            if not password:
                self.say(
                    "Password authentication will not work for a new passwordless role.", "yellow"
                )
                if click.confirm("Explicitly allow passwordless creation?", default=False):
                    self.credentials[role] = {"allow_passwordless_creation": True}
                    return
                continue
            if password == self.ask("Repeat " + role + " password", secret=True):
                self.credentials[role] = {"password": password}
                return
            self.say("Passwords did not match. Retry this account.", "red", True)

    def admin(self):
        self.say(
            "Temporary administrator access; credentials are never saved. Roles are cluster-wide.",
            "yellow",
        )
        while True:
            admin = {
                "user": self.ask("Administrator account", "postgres"),
                "maintenance_database": self.ask("Maintenance database", "postgres"),
            }
            errors = connection_errors(
                self.values, self.values.get("SETUP_READER_USER", "tushare_reader"), admin
            )
            bad = [errors[k] for k in ("admin_user", "maintenance") if k in errors]
            if not bad:
                break
            self.say("; ".join(bad), "red", True)
        admin["password"] = self.ask(
            "Administrator password (blank for other authentication)", secret=True
        )
        self.credentials["admin"] = admin

    def edit(self):
        while True:
            options = {
                str(i): label + ": " + safe_text(self.values.get(key, default))
                for i, (key, label, default, _) in enumerate(FIELDS, 1)
            } | {
                "w": "Writer credentials",
                "r": "Reader credentials",
                "a": "Temporary administrator",
                "n": "New connection",
                "c": "Done — check again",
                "q": "Back",
            }
            choice = self.menu("Edit one setting; other values are retained.", options)
            if choice in {"q", "c"}:
                return
            if choice == "n":
                self.new_connection()
                self.collect(force=True)
                return
            if choice == "a":
                self.admin()
            elif choice in {"w", "r"}:
                self.password("writer" if choice == "w" else "reader")
            else:
                self.field(FIELDS[int(choice) - 1])

    def collect(self, force=False):
        for field in FIELDS:
            if force or not self.values.get(field[0]):
                self.field(field)
        errors = connection_errors(self.values, self.values["SETUP_READER_USER"])
        while errors:
            self.say("; ".join(errors.values()), "red", True)
            self.edit()
            errors = connection_errors(self.values, self.values["SETUP_READER_USER"])

    def event(self, event, fields):
        if event == "step_started":
            self.current_action = fields["action"]
            self.say("Running: " + fields["action"], "cyan")
        elif event == "step_finished":
            action = fields["action"]
            if fields.get("outcome") == "completed":
                self.plan_completed.append(action)
                self.completed_history.append(
                    {"target": self.values["PGDATABASE"], "action": action}
                )
            self.current_action = None
            self.say(
                fields.get("outcome", "unknown").capitalize() + ": " + action,
                "green" if fields.get("outcome") == "completed" else "red",
                fields.get("outcome") != "completed",
            )

    def check(self):
        self.plan_completed = []
        self.current_action = None
        if self.session:
            self.session.close()
        settings = replace(
            selected_settings(self.values), log_dir=Path(self.values.get("LOG_DIR", "logs"))
        )
        self.session = SetupSession(
            settings,
            self.values.get("SETUP_READER_USER", "tushare_reader"),
            self.credentials,
            mode="interactive",
            observer=self.event,
            event_log=self.log,
        )
        self.say("Checking database readiness …", "cyan")
        checked = self.session.inspect()
        self.code = CODES[checked["readiness"]]
        self.say(
            database_preview(settings, self.session.reader, checked),
            "green" if checked["readiness"] == "ready" else "yellow",
        )
        return checked

    def access(self, checked):
        actions = checked["actions"]
        if any(
            a in actions for a in ("create-writer", "create-reader", "create-database", "grants")
        ):
            if not self.credentials.get("admin"):
                self.say("These actions require role/database management privileges.", "yellow")
                if click.confirm("Use a temporary administrator?", default=False):
                    self.admin()
        for role, action in (("writer", "create-writer"), ("reader", "create-reader")):
            if action in actions and not self.credentials.get(role):
                self.password(role, creation=True)
        if (
            "grants" in actions
            and "create-reader" not in actions
            and not self.credentials.get("reader")
        ):
            self.password("reader")

    def save(self):
        if not self.dirty:
            return 0
        updates = {
            k: self.values[k] for k in KEYS + SAVE_KEYS if k in self.values and k != "PGPASSWORD"
        }
        password = self.session.settings.pg_password
        if click.confirm("Save the verified writer password in the private file?", default=False):
            updates["PGPASSWORD"] = password
        elif self.file_values.get("PGPASSWORD") and click.confirm(
            "Explicitly clear the existing file password?", default=False
        ):
            updates["PGPASSWORD"] = ""
        while True:
            preview, matches, overridden = configuration_preview(
                self.file_values,
                self.effective,
                self.values | {"PGPASSWORD": password},
                updates,
                self.environment,
            )
            self.say("Configuration plan: " + str(self.path), "cyan")
            self.say(preview)
            if not click.confirm("Save these settings?", default=False):
                self.say("Database ready. Configuration: not saved.", "yellow")
                self.say("Configure daily writer authentication separately if needed.", "dim")
                return 1 if self.configuration == "failed" else 0
            try:
                save_config(self.path, self.original, updates)
                self.configuration = "saved"
                self.log.emit("configuration_saved", configuration="saved")
                self.say(
                    "Configuration: saved"
                    + (", overridden by environment." if overridden else "."),
                    "green",
                )
                if not matches:
                    self.say(
                        "Daily effective connection differs from this verified session.", "yellow"
                    )
                self.say("Use: tushare-downloader -c " + str(self.path) + " <command>", "dim")
                return 0
            except (ValueError, OSError):
                self.configuration = "failed"
                self.say(
                    "Configuration was not saved safely; database changes remain.", "red", True
                )
                choice = self.menu(
                    "Save recovery",
                    {"r": "Reload and review", "p": "Choose another path", "q": "Exit"},
                )
                if choice == "q":
                    return 1
                if choice == "p":
                    self.path = Path(self.ask("Save path")).absolute()
                try:
                    self.original, self.file_values = read_config(self.path)
                except (ValueError, OSError):
                    continue

    def run(self):
        if not self.source():
            return self.code
        missing = not all(self.values.get(k) for k in ("PGHOST", "PGDATABASE", "PGUSER"))
        if self.new or missing:
            self.collect(force=self.new)
            while True:
                choice = self.menu(
                    "Connection settings",
                    {
                        "c": "Continue",
                        "e": "Edit settings",
                        "a": "Administrator access",
                        "q": "Quit",
                    },
                )
                if choice == "q":
                    return 0
                if choice == "e":
                    self.edit()
                elif choice == "a":
                    self.admin()
                else:
                    break
        while True:
            checked = self.check()
            if checked["readiness"] == "ready":
                self.result = {
                    "readiness": "ready",
                    "writer_verification": "verified",
                    "reader_verification": "not_checked",
                }
                return self.save()
            if checked["readiness"] == "migration_needed":
                return 4
            if checked["readiness"] in {"unknown", "unsupported"}:
                choice = self.menu(
                    "Database not ready",
                    {"r": "Retry", "e": "Edit settings", "a": "Administrator access", "q": "Exit"},
                )
                if choice == "q":
                    return self.code
                if choice == "e":
                    self.edit()
                elif choice == "a":
                    self.admin()
                continue
            choice = self.menu(
                "Review proposed changes", {"c": "Continue", "e": "Edit settings", "q": "Cancel"}
            )
            if choice == "q":
                return 1 if self.completed_history else 0
            if choice == "e":
                self.edit()
                continue
            self.access(checked)
            # Re-read facts after credential changes; never apply the old snapshot.
            checked = self.check()
            if checked["readiness"] != "needs_configuration":
                continue
            typed = self.ask("Type the exact target database name to apply", "")
            if typed != self.values["PGDATABASE"]:
                self.say("Not confirmed. No new database changes.", "yellow")
                continue
            self.result = self.session.apply()
            while self.result["exit_code"] != 0:
                self.code = self.result["exit_code"]
                self.show_result()
                if self.code == 130 or self.result.get("reason_code") == "log_failed":
                    return self.code
                if self.session.verification_pending:
                    choice = self.menu(
                        "Access verification failed",
                        {"r": "Correct credentials and verify only", "q": "Exit"},
                    )
                    if choice == "q":
                        return 1
                    self.password("writer")
                    self.password("reader")
                    self.result = self.session.retry_verification(
                        writer_password=self.credentials.get("writer", {}).get("password"),
                        reader_password=self.credentials.get("reader", {}).get("password"),
                    )
                    continue
                choice = self.menu(
                    "Partial result; recheck before further changes.",
                    {"r": "Recheck", "e": "Edit settings", "q": "Exit"},
                )
                if choice == "q":
                    return self.code
                if choice == "e":
                    self.edit()
                break
            else:
                return self.save()

    def show_result(self):
        for key in (
            "completed",
            "failed",
            "unknown",
            "not_attempted",
            "writer_verification",
            "reader_verification",
        ):
            value = self.result.get(key)
            if value:
                self.say(
                    key.replace("_", " ").capitalize()
                    + ": "
                    + (", ".join(value) if isinstance(value, list) else value)
                )
        if self.result.get("reason_code"):
            self.say("Reason: " + self.result["reason_code"], "red", True)

    def finish(self, code):
        if code == 130 and self.session:
            self.result["completed"] = list(self.plan_completed)
            self.result["not_attempted"] = [
                action
                for action in self.session.actions
                if action not in self.plan_completed and action != self.current_action
            ]
        if self.current_action:
            self.result["unknown"] = list(
                dict.fromkeys(self.result.get("unknown", []) + [self.current_action])
            )
        self.show_result()
        self.say(
            "Database setup: "
            + ("Ready" if code == 0 and self.result.get("readiness") == "ready" else "Closed"),
            "green" if code == 0 and self.result.get("readiness") == "ready" else "yellow",
        )
        self.say("Configuration: " + self.configuration)
        if self.completed_history:
            self.say(
                "Completed in this session: "
                + ", ".join(
                    item["target"] + "/" + item["action"] for item in self.completed_history
                )
            )
        if self.log:
            self.log.emit(
                "session_finished",
                exit_code=code,
                outcome="completed"
                if code == 0 and self.result.get("readiness") == "ready"
                else "incomplete",
                configuration=self.configuration,
                completed_history=self.completed_history,
                readiness=self.result.get(
                    "readiness", getattr(self.session, "readiness", "unknown")
                ),
                completed=self.result.get("completed", []),
                failed=self.result.get("failed", []),
                unknown=self.result.get("unknown", []),
                not_attempted=self.result.get("not_attempted", []),
                writer_verification=self.result.get("writer_verification", "not_checked"),
                reader_verification=self.result.get("reader_verification", "not_checked"),
            )
            self.say("Log: " + str(self.log.path), "dim")


def run_dialogue(ctx, new=False):
    dialogue = Dialogue(ctx, new)
    code = 1
    try:
        code = dialogue.run()
    except (KeyboardInterrupt, EOFError, click.Abort):
        code = 130
        dialogue.say("Interrupted. Previously completed changes remain.", "yellow", True)
    except ValueError:
        code = 2
        dialogue.say(
            "Invalid setup configuration; review field values and time budgets.", "red", True
        )
    except Exception:
        code = 1
        dialogue.say(
            "Setup failed. No further changes will be scheduled; review the log.", "red", True
        )
    finally:
        try:
            dialogue.finish(code)
        except OSError:
            code = 1
            click.echo("Setup log failed; database results above remain valid.", err=True)
        finally:
            if dialogue.session:
                dialogue.session.close()
            if dialogue.log:
                try:
                    dialogue.log.close()
                except OSError:
                    code = 1
    ctx.exit(code)
