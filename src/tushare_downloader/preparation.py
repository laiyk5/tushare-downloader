"""Small safe descriptions for failures before dataset execution."""

from .config import ConfigError


class PreparationFailure(ConfigError, RuntimeError):
    def __init__(self, message, exit_code=1):
        super().__init__(message)
        self.exit_code = exit_code


def describe(error, calendar=False):
    missing = isinstance(error, ConfigError) and error.args == (
        "Remote requests require TUSHARE_TOKEN.",
    )
    if missing:
        return dict(
            code="missing_tushare_token",
            message="TUSHARE_TOKEN is not configured. No remote requests started.",
            hint="Set TUSHARE_TOKEN in your selected configuration file or environment, then retry.",
        )
    return dict(
        code="preparation_error",
        message="Calendar preparation failed. No data requests started."
        if calendar
        else "Download preparation failed. No data requests started.",
        hint="Check the calendar source/cache or explicitly select basic/off or --ignore-calendar."
        if calendar
        else "Check configuration, connection permissions and the database schema before retrying.",
    )
