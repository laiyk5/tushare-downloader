"""UI01–UI04: native input and focus, before service integration."""

import asyncio

from textual.widgets import Input

from tushare_downloader.setup_tui import SetupApp


def test_native_edit_resize_and_return_preserve_input():
    async def scenario():
        app = SetupApp()
        async with app.run_test(size=(80, 24)) as pilot:
            field = app.query_one("#host", Input)
            field.focus()
            await pilot.press("ctrl+a", "x", "y")
            assert field.value == "xy"
            await pilot.resize_terminal(40, 20)
            await pilot.pause()
            assert app.focused is field
            assert field.value == "xy"
            app.show_page("access")
            await pilot.pause()
            app.show_page("connection")
            await pilot.pause()
            assert app.query_one("#host", Input) is field
            assert field.value == "xy"

    asyncio.run(scenario())


def test_text_entry_never_applies_and_confirmation_is_modal():
    async def scenario():
        app = SetupApp()
        async with app.run_test(size=(80, 24)) as pilot:
            app.query_one("#host", Input).focus()
            await pilot.press("enter")
            assert not app.applied
            app.confirm_target("research")
            await pilot.pause()
            app.screen.query_one("#confirmation", Input).value = "wrong"
            await pilot.press("tab", "enter")
            assert not app.applied
            await pilot.press("escape")
            assert len(app.screen_stack) == 1

    asyncio.run(scenario())


def test_secret_input_and_minimum_terminal_size():
    async def scenario():
        app = SetupApp()
        async with app.run_test(size=(40, 20)) as pilot:
            app.show_page("access")
            await pilot.pause()
            assert app.query_one("#reader_password", Input).password
            await pilot.resize_terminal(39, 19)
            await pilot.pause()
            assert not app.can_apply
            assert app.query_one("#resize_notice").display
            await pilot.resize_terminal(120, 30)
            await pilot.pause()
            assert not app.query_one("#resize_notice").display

    asyncio.run(scenario())


def test_late_inspection_never_authorizes_edited_target(tmp_path):
    import threading

    started, release = threading.Event(), threading.Event()

    class Fake:
        def __init__(self, *args, **kw):
            self.log = type("Log", (), {"path": tmp_path / "log"})()

        def inspect(self):
            started.set()
            release.wait(2)
            return {"readiness": "needs_configuration", "actions": ["grants"], "facts": {}}

        def close(self):
            pass

    async def scenario():
        app = SetupApp(session_factory=Fake)
        async with app.run_test(size=(80, 24)) as pilot:
            for key, value in {
                "host": "localhost",
                "port": "5432",
                "database": "research",
                "writer": "writer",
                "sslmode": "prefer",
                "reader": "reader",
            }.items():
                app.query_one("#" + key, Input).value = value
            await pilot.pause()
            pending = asyncio.create_task(app.check_connection())
            await asyncio.to_thread(started.wait, 2)
            field = app.query_one("#database", Input)
            field.focus()
            field.value = "other_target"
            await pilot.pause()
            release.set()
            await pending
            assert not app.can_apply
            assert app.focused is field
            assert field.value == "other_target"

    asyncio.run(scenario())


def test_new_connection_preserves_old_file_and_drops_password(tmp_path):
    path = tmp_path / ".env"
    original = "PGHOST=old\nPGPASSWORD=SECRET\n"
    path.write_text(original)

    async def scenario():
        app = SetupApp(config_path=path, values={"PGHOST": "old", "PGPASSWORD": "SECRET"})
        async with app.run_test(size=(80, 24)) as pilot:
            app.new_connection()
            await pilot.pause()
            assert app.config_path == tmp_path / ".env.new"
            assert not app.query_one("#writer_password", Input).value
            assert app.original_password == ""
            assert path.read_text() == original

    asyncio.run(scenario())


class ServiceDouble:
    actions = ["grants"]
    calls = []

    def __init__(self, settings, reader, credentials, **kw):
        self.settings = settings
        self.credentials = credentials
        self.observer = kw.get("observer")
        self.log = type("Log", (), {"path": settings.log_dir / "fake.jsonl"})()
        self.cancelled = False

    def inspect(self):
        return {
            "readiness": "needs_configuration" if self.actions else "ready",
            "actions": list(self.actions),
            "facts": {"reader_exists": True, "writer_exists": True, "kind": "managed"},
        }

    def apply(self):
        self.calls.append("apply")
        return {
            "exit_code": 0,
            "completed": list(self.actions),
            "failed": [],
            "unknown": [],
            "not_attempted": [],
            "writer_verification": "verified",
            "reader_verification": "verified",
        }

    def close(self):
        pass


def connection_values(tmp_path):
    return {
        "PGHOST": "localhost",
        "PGPORT": "5432",
        "PGDATABASE": "research",
        "PGUSER": "writer",
        "PGSSLMODE": "prefer",
        "LOG_DIR": str(tmp_path),
    }


def test_confirmed_apply_uses_shared_service_once(tmp_path):
    async def scenario():
        ServiceDouble.calls = []
        app = SetupApp(values=connection_values(tmp_path), session_factory=ServiceDouble)
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await app.check_connection()
            assert app.can_apply
            app.confirmed(True)
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert ServiceDouble.calls == ["apply"]
            assert app.page == "result"
            assert not app.can_apply

    asyncio.run(scenario())


def test_ready_connection_saves_independently_without_database_apply(tmp_path):
    class Ready(ServiceDouble):
        actions = []

    async def scenario():
        Ready.calls = []
        path = tmp_path / ".env"
        path.write_text("# User settings\nPGHOST=old\nPGPASSWORD=old_secret\nOTHER=keep\n")
        app = SetupApp(config_path=path, values=connection_values(tmp_path), session_factory=Ready)
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await app.check_connection()
            assert not app.can_apply
            app.save_configuration(True)
            assert "PGHOST='localhost'" in path.read_text()
            assert "PGPASSWORD=old_secret" in path.read_text()
            assert "OTHER=keep" in path.read_text()
            assert Ready.calls == []

    asyncio.run(scenario())


def test_changed_endpoint_discards_temporary_credentials(tmp_path):
    async def scenario():
        app = SetupApp(values=connection_values(tmp_path) | {"PGPASSWORD": "old_secret"})
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            app.query_one("#admin_password", Input).value = "temporary"
            app.query_one("#host", Input).value = "another-host"
            await pilot.pause()
            assert app.original_password == ""
            assert not app.query_one("#admin_password", Input).value

    asyncio.run(scenario())


def test_new_reader_requires_matching_password_confirmation(tmp_path):
    class NewReader(ServiceDouble):
        actions = ["create-reader", "grants"]

        def inspect(self):
            result = super().inspect()
            result["facts"]["reader_exists"] = False
            return result

    async def scenario():
        app = SetupApp(values=connection_values(tmp_path), session_factory=NewReader)
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            app.query_one("#reader_password", Input).value = "new_password"
            app.query_one("#reader_confirm", Input).value = "different"
            await pilot.pause()
            await app.check_connection()
            assert not app.can_apply
            app.query_one("#reader_confirm", Input).value = "new_password"
            await pilot.pause()
            await app.check_connection()
            assert app.can_apply

    asyncio.run(scenario())


def test_writer_password_clear_does_not_fall_back_to_saved_secret(tmp_path):
    from textual.widgets import Select

    async def scenario():
        app = SetupApp(
            values=connection_values(tmp_path) | {"PGPASSWORD": "saved_secret"},
            session_factory=ServiceDouble,
        )
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            app.query_one("#writer_password_mode", Select).value = "clear"
            await pilot.pause()
            await app.check_connection()
            assert app.session.settings.pg_password == ""

    asyncio.run(scenario())


def test_native_authentication_recovery_does_not_reapply(tmp_path):
    class FailedVerification(ServiceDouble):
        verification_pending = False

        def apply(self):
            self.calls.append("apply")
            self.verification_pending = True
            return {
                "exit_code": 1,
                "reason_code": "verification_failed",
                "completed": ["grants"],
                "failed": [],
                "unknown": [],
                "not_attempted": [],
            }

        def retry_verification(self, **credentials):
            assert credentials["reader_password"] == "corrected"
            self.calls.append("verify")
            self.verification_pending = False
            return {
                "exit_code": 0,
                "completed": ["grants"],
                "failed": [],
                "unknown": [],
                "not_attempted": [],
                "writer_verification": "verified",
                "reader_verification": "verified",
            }

    async def scenario():
        FailedVerification.calls = []
        app = SetupApp(values=connection_values(tmp_path), session_factory=FailedVerification)
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await app.check_connection()
            app.confirmed(True)
            await app.workers.wait_for_complete()
            app.query_one("#reader_password", Input).value = "corrected"
            await pilot.pause()
            await app.retry_access()
            assert FailedVerification.calls == ["apply", "verify"]
            assert app.final_result["completed"] == ["grants"]
            assert app.final_result["exit_code"] == 0

    asyncio.run(scenario())


def test_wide_sidebar_and_narrow_stacking_use_same_input_controls():
    async def scenario():
        app = SetupApp()
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            host = app.query_one("#host", Input)
            assert app.query_one("#navigation").region.width <= 20
            assert app.query_one("#connection_summary").region.x > host.region.x
            await pilot.resize_terminal(40, 20)
            await pilot.pause()
            assert app.query_one("#host", Input) is host
            assert app.query_one("#connection_summary").region.y > host.region.y

    asyncio.run(scenario())


def test_ready_and_independent_table_do_not_request_admin_or_reader_secret(tmp_path):
    async def scenario(actions):
        class Limited(ServiceDouble):
            pass

        Limited.actions = actions
        app = SetupApp(values=connection_values(tmp_path), session_factory=Limited)
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await app.check_connection()
            app.show_page("access")
            await pilot.pause()
            assert not app.query_one("#admin_password", Input).display
            assert not app.query_one("#reader_password", Input).display

    asyncio.run(scenario([]))
    asyncio.run(scenario(["initialize"]))


def test_bad_port_is_explained_at_field_before_any_connection(tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError("Invalid input must not reach the database service")

    async def scenario():
        app = SetupApp(values=connection_values(tmp_path), session_factory=forbidden)
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            field = app.query_one("#port", Input)
            field.value = "not_a_port"
            await pilot.pause()
            await app.check_connection()
            await pilot.pause()
            assert app.focused is field
            assert "65535" in str(field.border_subtitle)
            field.value = "5432"
            await pilot.pause()
            assert not field.border_subtitle

    asyncio.run(scenario())


def test_confirmed_exit_during_execution_is_not_success():
    class Session:
        def request_cancel(self):
            pass

        def close(self):
            pass

    async def scenario():
        app = SetupApp()
        async with app.run_test(size=(80, 24)) as pilot:
            app.session = Session()
            app.busy = app.executing = True
            app.exit_confirmed(True)
            app.present_result(
                {
                    "exit_code": 130,
                    "completed": ["create-reader"],
                    "unknown": ["grants"],
                    "not_attempted": [],
                }
            )
            await pilot.pause()
        assert app.return_value == 130
        assert app.final_result["completed"] == ["create-reader"]
        assert app.final_result["unknown"] == ["grants"]

    asyncio.run(scenario())


def test_modal_resize_cannot_authorize_small_terminal(tmp_path):
    async def scenario():
        app = SetupApp(values=connection_values(tmp_path), session_factory=ServiceDouble)
        async with app.run_test(size=(80, 24)) as pilot:
            await app.check_connection()
            app.confirm_target("research")
            await pilot.pause()
            await pilot.resize_terminal(39, 19)
            await pilot.pause()
            app.screen.query_one("#confirmation", Input).value = "research"
            await pilot.pause()
            app.screen.confirm()
            await pilot.pause()
            assert not app.applied
            assert not app.can_apply

    asyncio.run(scenario())


def test_execution_locks_all_editable_controls(tmp_path):
    import threading

    from textual.widgets import Checkbox, Select

    release = threading.Event()

    class Slow(ServiceDouble):
        def apply(self):
            release.wait(3)
            return super().apply()

    async def scenario():
        app = SetupApp(values=connection_values(tmp_path), session_factory=Slow)
        async with app.run_test(size=(80, 24)) as pilot:
            await app.check_connection()
            app.confirmed(True)
            await pilot.pause()
            try:
                assert app.busy
                for field in app.query("Input, Select, Checkbox"):
                    assert field.disabled, field.id
            finally:
                release.set()
            for _ in range(40):
                await pilot.pause(0.02)
                if not app.busy:
                    break
            assert not app.busy
            assert not app.query_one("#writer_password_mode", Select).disabled
            assert not app.query(Checkbox).first().disabled

    asyncio.run(scenario())
