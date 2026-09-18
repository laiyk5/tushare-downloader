# Three bounded user experience sessions

Date: 2026-09-18 (Asia/Shanghai). Software/document baseline: `bb89e06`.
These are agent-led, user-perspective explorations through real CLI invocations in a 100-column
PTY, not three independent human participants and not replacements for acceptance testing.
Each session ended after useful feedback was obtained; no minimum duration or command count was required.
The [reference](../experience-reference.md) limits each to 20 minutes / 25 invocations,
two live downloads and four HTTP attempts. Sessions were sequential; each feedback was written
before selecting the next direction. Timings in each report include exploration and feedback;
shared harness preparation and later site publication are outside those session timings.

| Session | Direction | Invocations | HTTP attempts | Feedback |
| --- | --- | ---: | ---: | --- |
| 1 | First contact, setup, datasets and schema | 5 | 0 | [First contact](session-1.md) |
| 2 | One-day plan, download preparation and report | 4 | 0 | [Download path](session-2.md) |
| 3 | Common mistakes, plain/quiet and headless | 6 | 0 | [Recovery and output](session-3.md) |

Total: 15 downloader invocations. One live download invocation failed before networking because
no Tushare token was supplied. The helper intentionally cleared inherited Tushare/PG/setup values
and selected the verified development configuration. No production configuration or credentials
were copied. Thus this is a credential-missing experience, not evidence that a configured user's
normal download would fail. The developer database identity was checked before each session.
No database/configuration mutations occurred; only local logs and reports were created.

## Most useful follow-ups

1. Preserve safe, actionable preparation-error reasons in report.md and JSONL; the terminal-only
   missing-token explanation was lost from the saved artifacts.
2. Explain Ready versus untested reader credentials and why an unchanged configuration was not saved.
3. Help users correct global-option placement, and describe datasets in user terms before internal policy labels.

These are observed findings and suggestions, not implemented fixes or automatically added release
gates. Successful remote downloads, repeat-skip behavior, nonempty data, long-running progress/ETA
and fresh database provisioning were not experienced. All three sessions stayed below their limits.
