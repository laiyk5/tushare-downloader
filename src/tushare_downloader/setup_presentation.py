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
