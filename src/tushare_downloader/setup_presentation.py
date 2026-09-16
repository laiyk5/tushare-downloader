"""Human-readable setup summaries built from explicit, secret-safe inputs."""

from .setup_config import KEYS, SAVE_KEYS


def configuration_preview(file_values, effective, selected, updates, environment):
    saved = file_values | updates
    after = saved | environment
    keys = [key for key in KEYS + SAVE_KEYS if key in selected or key in updates]
    matches = all(str(after.get(key, "")) == str(selected.get(key, "")) for key in keys)
    overridden = any(key in environment for key in keys)

    def display(key, value):
        if key == "PGPASSWORD":
            return "[set]" if value else "[empty]"
        return str(value) if value is not None else "(absent)"

    rows = []
    for key in keys:
        source = (
            "environment"
            if key in environment
            else ("file" if key in file_values else "default/input")
        )
        rows.extend(
            [
                key,
                "  File: " + display(key, file_values.get(key)),
                "  Current (" + source + "): " + display(key, effective.get(key)),
                "  Selected: " + display(key, selected.get(key)),
                "  Saved: " + display(key, saved.get(key)),
                "  Effective after: " + display(key, after.get(key)),
            ]
        )
        if key == "PGPASSWORD" and key not in updates:
            rows.append(
                "  Existing file password retained."
                if key in file_values
                else "  Password not stored."
            )
        rows.append("")
    if overridden:
        rows.append("Saved values remain overridden by environment where shown.")
    if not matches:
        rows.append("The resulting effective configuration differs from the verified selection.")
    return "\n".join(rows), matches, overridden


def database_preview(settings, reader, inspection):
    rows = [
        "Target: " + settings.pg_host + ":" + str(settings.pg_port) + "/" + settings.pg_database,
        "State: " + inspection["readiness"].replace("_", " ").capitalize(),
        "",
    ]
    facts = inspection.get("facts") or {}
    message = inspection_message(inspection.get("reason_code"))
    if message:
        rows.extend([message, ""])
    if not inspection["actions"]:
        rows.append(
            "No changes needed."
            if inspection["readiness"] == "ready"
            else "No executable plan. Unknown facts do not mean that objects are absent."
        )
    descriptions = {
        "create-writer": (
            "Role " + settings.pg_user,
            "Absent" if facts.get("writer_exists") is False else "Not confirmed",
            "Restricted LOGIN role",
            "New cluster-wide account; password is supplied privately.",
        ),
        "create-reader": (
            "Role " + reader,
            "Absent" if facts.get("reader_exists") is False else "Not confirmed",
            "Restricted LOGIN role",
            "New cluster-wide account; existing passwords are never reset.",
        ),
        "create-database": (
            "Database " + settings.pg_database,
            "Absent" if facts.get("kind") == "missing" else "Not confirmed",
            "Database owned by " + settings.pg_user,
            "Database creation commits independently.",
        ),
        "initialize": (
            "Registered API tables",
            "Missing: " + ", ".join(facts["missing"])
            if facts.get("missing")
            else "Not initialized",
            "Required registered tables present",
            "Existing data and registered table identities are preserved.",
        ),
        "grants": (
            "Reader access for " + reader,
            "Required access incomplete",
            "CONNECT; raw/meta USAGE; registered tables SELECT; future raw tables SELECT",
            "Grants affect this database; the account is cluster-wide. Other privileges are not revoked.",
        ),
    }
    for action in inspection["actions"]:
        title, before, after, impact = descriptions[action]
        rows.extend(
            [
                title,
                "  Action: " + action,
                "  Before: " + before,
                "  After: " + after,
                "  Impact: " + impact,
                "",
            ]
        )
    if facts.get("kind") == "empty":
        rows.append("Adopt empty database: initialize the existing writer-owned database.")
    rows.append(
        "Review scope: this target database and selected roles; other application dependencies are not enumerated."
    )
    return "\n".join(rows)


def inspection_message(reason):
    return {
        "unmanaged_objects": "The database contains unmanaged objects. Setup will not take ownership; select a different target or review it manually.",
        "ownership_conflict": "The database has a different owner. Select the intended writer-owned database; setup will not change ownership.",
        "incompatible_schema": "The schema or object ownership is incompatible. No supported migration is available; setup will not guess a repair.",
        "role_privilege_conflict": "A selected role has conflicting privileges or memberships. Review the shared account or choose another role; setup will not revoke privileges.",
        "unsupported_database": "This database state is unsupported. Review the target before continuing.",
        "inspection_unavailable": "Database facts could not be verified. Check connectivity, authentication and inspection permissions, then check again.",
    }.get(reason, "")
