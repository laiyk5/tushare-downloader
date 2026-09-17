# Revision 4 terminal review

Status: **Not run by a human**. Automated CLI tests do not replace this check.

Run in Windows Terminal + WSL/Linux Python:

    cd /home/laiyk/projects/tools/tushare-downloader
    uv run --locked python logs/revision-4-review/review.py

The local helper clears inherited credentials and guards the prefilled isolated server
(127.0.0.1:55433), database tdw_r4review_7f2c and its _w/_r roles. It uses the actual
dialogue and DatabaseBackend, without simulated results. It restricts configuration saves
to its own ignored directory; the production .env and port 5432 are not used.

- Keep the prefilled target. If initial writer access fails, choose Administrator access,
  account postgres, maintenance database postgres, and leave its password blank for this
  isolated trust-authentication fixture.
- New writer/reader passwords may be dummy values; repeat each when prompted. Check the
  consequence summary, numbered edits and exact target-name confirmation.
- Test a wrong name at confirmation, then return to the plan. No changes should start.
- Complete setup, optionally save the dummy writer password, then rerun: Ready should
  exit without asking for administrator/reader credentials.
- Read plans/results at 40/80/120 columns; run the same helper with --plain once.
  Verify password hiding, Ctrl+C and restored shell echo. During questions, cancel once,
  restart, edit a field without losing other values, and return to checking.
- Real authentication, uncertain commits and remaining-action recovery are automated
  isolated PostgreSQL tests; the helper does not pretend that trust tests rejected passwords.

Record terminal/version, routes actually performed, widths, readability and any problem.
Do not record real passwords. Report failures before retrying outside this isolated scope.
The helper and configuration are local ignored files, not product deliverables.
After review, clean only these exact owned objects and stop the isolated server when no
other validation needs it. Until feedback arrives, human acceptance remains Not run.
