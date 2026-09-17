# Session 2 — Plan a one-day download

Direction chosen from session 1: follow the download path and look for recovery guidance.
Agent-led exploration; budget 20 minutes / 25 invocations / two live invocations / four HTTP attempts.
Actual: 66 seconds through feedback, 4 invocations, one live invocation rejected before HTTP,
0 HTTP attempts and no database writes. Local logs/reports were created. Development credentials
were isolated; no Tushare token was supplied or copied from production.

Route: fetch --help → one-day dry-run → same fetch without dry-run → inspect daily_basic;
then read the printed report and log. Date: 2026-01-05; MAX_ATTEMPTS=2, CALENDAR_FILTER=basic.

- **Easy:** Dry-run needs no token, states one planned block, and provides log/report paths. The live attempt names the missing TUSHARE_TOKEN and explicitly says no requests started.
- **Hesitation:** Suggested fetch --help does not explain where to set the token. Inspect still says last recorded attempt Never: reasonable for no request, but the distinction from a failed command could be clearer.
- **Most useful improvement:** Preserve a safe actionable failure reason in report.md and JSONL. The report only says ConfigError and has empty result/block sections; the log has invocation_started and calendar_plan but no failure event. Someone opening the files later cannot recover the missing-token explanation shown in the terminal.

Failure report: reports/20260917T164039Z-43e6ed0a/report.md; log:
logs/fetch/20260917T164039Z-43e6ed0a.jsonl. These are local private artifacts, not published data.
No successful download, duplicate skip, throughput or ETA experience is claimed.
Next direction: see whether normal errors and plain/quiet output help a user recover without guessing.
