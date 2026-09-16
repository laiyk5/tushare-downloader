# Inherited acceptance audit

Status: **in progress, not accepted**. Candidate production code:
`8a4dd1bd4ab3da3308ac4d944af96eef1b011d9b`; design:
`993d14d4f94d9678f6acb0536e8a8cf512693f05`.

This is the explicit A–J/L audit queue, not a claim that every Not run requirement
lacks tests. The status means the complete requirement has not yet been signed off
against inspected evidence. K is a separate human-authorized release gate.

## Change-impact boundary

Compared with revision 2 candidate `3bb9354f743bd1f2bcbe315d34aa02e02c6c5720`,
revision 3 changes the shared bounded worker, CLI entry, dependencies, setup,
configuration template and documentation. The downloader/storage/inspection/contract
modules themselves are unchanged. This supports bounded reuse of old source-format
and database-layout observations, but **does not** establish runtime equivalence:
CLI, worker and dependency changes still require current regression and affected
performance/terminal checks. Old export-wizard evidence does not verify the new TUI.

Current full regression and installed smoke outputs are linked from the
[implementation record](index.md). No fresh real Tushare request or backup/restore
exercise was performed in this audit checkpoint; their status is not upgraded.

## Requirements

| ID | Status | Evidence or remaining work |
| --- | --- | --- |
| A01 | Pass | Current wheel/sdist build, distribution checker and installed smoke record; Python 3.12 in WSL. |
| A02 | Pass | Current 546-test regression, Ruff and 174-file format check; subsequent test-only addition passed its six-case module. |
| A03 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| A04 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| A05 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| A06 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| B01 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| B02 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| B03 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| B04 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| B05 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| B06 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| B07 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| C01 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| C02 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| C03 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| C04 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| C05 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| C06 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| C07 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| C08 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| D01 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| D02 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| D03 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| D04 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| E01 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| E02 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| E03 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| E04 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| E05 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| E06 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| E07 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| E08 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| E09 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| F01 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| F02 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| F03 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| F04 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| F05 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| F06 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| F07 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| G01 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| G02 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| G03 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| G04 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| G05 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| G06 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| G07 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| G08 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| G09 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| H01 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| H02 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| H03 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| H04 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| I01 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| I02 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| I03 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| I04 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| J01 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| J02 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| J03 | Pass | Current integration and isolated cluster runs use WSL Python to Windows PostgreSQL 18 on port 55433; fixture identity guards inspected. |
| A01 | Pass | Current wheel/sdist build, distribution checker and installed smoke record; Python 3.12 in WSL. |
| L01 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| L02 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| L03 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| L04 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| L05 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| L06 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| L07 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |
| L08 | Not run | Composite requirement still needs explicit assertion/artifact review; passing full regression alone is insufficient. |

## Added v0.4 requirements

- M01–M04: inspect LG/UP/W/DL subconditions and original local evidence;
  rendered browser navigation and old-URL checks remain separate from link validation.
- N01: inspect IN01–IN09. Current timestamp tests add evidence for IN02/03/06;
  permission, partial-result, budget, six-mode and human-layout conditions remain
  composite requirements. Revision 2 benchmark cannot silently cover a changed worker.
- N02: inspect DA01–DA08 and SC01–SC08. Current real cluster tests provide
  permission and old-database evidence, but must be mapped to each full condition.
- N03: current complete regression and actual old-source fixture supplement the
  cross-feature guarantee; English guide/SQL and terminal checks still need mapping.
- O: see the [setup audit](acceptance-audit.md), including its explicitly open
  Windows Terminal + WSL human routes.
