# v0.4.0 final local acceptance

Date: 2026-09-17. Software candidate: `277328df07cae64d3d691d4fa87403e4912dae3b`.
Design: `design-v0.4.0-r6` (`225eef2`). Status: **local acceptance passed; remote release gates pending**.
The follow-up documentation commit does not change the tested software.

## Final checks

| Gate | Evidence | Result |
| --- | --- | --- |
| Exact candidate full regression | [Output](regression.txt), unit + integration + cluster, guarded isolated PG18 on port 55434 | 684 passed in 211.63s; no failures or skips |
| Dependency lock / static checks | Offline lock check; Ruff check and format; git whitespace check | Passed |
| Distribution | [Build](build.txt), [package audit](distribution.txt), [installed setup](installed.txt), [SHA-256](artifacts.json) | Wheel/sdist, MIT metadata, sensitive-file exclusions and clean-environment CLI passed |
| Documentation | [Strict build](docs.txt); 131 legacy aliases; archive and relative-link checks | Passed; no broken links |
| Native terminal gap | [PTY results](terminal.json), [reproducible check](terminal_check.py) | Hidden synthetic password; Enter/Ctrl+C/EOF restore echo; 40/80/120 columns at height 10; piped output has no ANSI/OSC/carriage-return animation |
| Upgrade / retention / permissions | Full cluster suite and [revision 6 mapping](../revision-6/acceptance.md) | Actual v0.3.0 source database upgrades through public setup; identity, rows, unrelated objects and reader restrictions verified |

## Inherited evidence and closed historical gaps

The [revision 3 inherited audit](../revision-3/inherited-audit.md) remains a historical checkpoint.
Its unmodified A–N requirements use the cited evidence plus the current complete regression.
The [revision 5 mapping](../revision-5/acceptance.md) supplies the corrected suspend_d contract
and Inspect overview; [revision 6](../revision-6/acceptance.md) supplies ordered setup migration.
The frozen acceptance scope is unchanged.

G05/G09/H01/SC08 combine the native PTY observations here with current terminal selection,
short-height, mode matrix, markup/control sanitization, help and offline-schema assertions.
IN07/IN08 use revision 5 representative Inspect output plus the current read-command suite.
The revision 4 password echo/restoration gap is now closed by the actual Dialogue.ask secret
path in a PTY. This directly tests the production input primitive, not a complete database
creation session; database outcomes and dialogue branches have separate cluster/unit evidence.
The first helper invocation used an incorrect interpreter argv and failed to import the package;
correcting the helper produced the recorded passes, with no product change.

BL-012, BL-013 and BL-018 are complete locally on these combined records. BL-017 uses the
previous browser review, preserved archive manifest, current aliases/link checks and strict build.
Historical records and their former pending labels are retained rather than rewritten.

## Release gates and limits

- K03: MIT/license/package boundaries passed; prior dependency-license evidence is reused for
  unchanged dependencies. The code license grants no Tushare data redistribution rights.
- K04: candidate, design, evidence and artifact hashes are linked here; no software tag is created.
- K01/K02: remote candidate CI, protected-branch integration and final Pages deployment/online
  checks are **not run in this local acceptance**. They remain release-stage gates. If merging
  changes the software tree, reassess the difference before reusing these results.
- Real API observations remain the historical J/L and revision 5 evidence. Its maintainer-accepted
  request-budget deviation stays visible; this run makes no fresh Tushare request.
- No production database was accessed; no push, PR, workflow, tag or release was performed.
- Optional subjective terminal feedback is not an outstanding mechanical acceptance task.

No local functional blocker remains. Proceed to the remote release checks before declaring the
software published; successful local tests are not a claim that deployment already succeeded.
