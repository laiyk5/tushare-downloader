"""Setup-only private event stream; correlation is not persisted task state."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

EVENTS = {
    "config_loaded",
    "inspection_finished",
    "plan_created",
    "step_started",
    "step_finished",
    "verification_finished",
    "configuration_saved",
    "session_finished",
}
DETAILS = {
    "step_id",
    "actor_role",
    "exit_code",
    "actions",
    "before",
    "after",
    "readiness",
    "writer_verification",
    "reader_verification",
    "configuration",
    "completed",
    "completed_history",
    "failed",
    "not_attempted",
    "unknown",
}
TARGET_KEYS = {"host", "port", "database", "writer", "reader"}


class SetupLog:
    def __init__(self, directory, mode, target):
        folder = Path(directory) / "setup"
        folder.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.session_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex[:12]
        self.path = folder / (self.session_id + ".jsonl")
        fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        self.stream = os.fdopen(fd, "w", encoding="utf-8")
        self.mode = mode
        self.target = {k: v for k, v in target.items() if k in TARGET_KEYS}
        self.seq = 0
        self.plan_seq = 0

    def plan(self, actions, before=None, after=None):
        self.plan_seq += 1
        self.emit("plan_created", actions=actions, before=before, after=after)
        return self.plan_seq

    def emit(
        self, event, *, action=None, outcome=None, reason_code=None, duration_ms=None, **details
    ):
        if event not in EVENTS or set(details) - DETAILS:
            raise ValueError("Unsupported setup event field.")
        self.seq += 1
        plan_event = event in {
            "plan_created",
            "step_started",
            "step_finished",
            "verification_finished",
            "session_finished",
        }
        record = dict(
            event_version=1,
            timestamp=datetime.now(UTC).isoformat(),
            session_id=self.session_id,
            seq=self.seq,
            mode=self.mode,
            event=event,
            action=action,
            outcome=outcome,
            reason_code=reason_code,
            duration_ms=duration_ms,
            target=self.target,
            plan_seq=self.plan_seq if plan_event and self.plan_seq else None,
        )
        record.update(details)
        self.stream.write(json.dumps(record, ensure_ascii=True) + "\n")
        self.stream.flush()

    def close(self):
        self.stream.close()
