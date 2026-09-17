# Session 3 — Recover from mistakes and compare output

Direction chosen from session 2: errors and output preferences, without acquiring credentials or
retrying the failed download. Agent-led exploration; 20-minute / 25-invocation limit.
Actual: 92 seconds through feedback, 6 invocations, 0 live downloads, 0 HTTP attempts,
no database/configuration writes. Dry-run and setup created local reports/logs.

Route: fetch with missing end date → corrected plain dry-run → quiet dry-run → inspect with
misplaced --plain → corrected plain inspect → setup --headless. All database calls used .env.dev.

- **Easy:** Missing --end gives a precise error. Plain output is readable and preserves the plan and paths. No-change headless setup finishes quickly and says no database changes.
- **Hesitation:** `inspect daily_basic --plain` says No such option, despite --plain being available globally. The message points to subcommand help rather than explaining placement. Quiet dry-run preserves almost all normal plan output; that is consistent with its contract but is not obvious to someone expecting a shorter preview.
- **Most useful improvement:** Recognize misplaced global flags in error guidance and show the corrected command, without silently changing parser rules. Explain briefly that quiet retains explicitly requested previews.

The headless Ready result shows writer and reader not_checked, whereas interactive setup verified
the writer in session 1. This is an observed wording distinction, not proof that permissions are
incorrect. Label the scope of readiness versus credential verification clearly.
No product changes or new acceptance gates were introduced during exploration.
