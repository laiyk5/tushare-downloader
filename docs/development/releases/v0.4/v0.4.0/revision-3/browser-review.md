# Local documentation browser review

Date: 2026-09-17. Source: worktree based on `299ea12`, including the current Inspect
repair and audit updates. Local evidence only; no Pages deployment or remote CI run.
Browser: Codex in-app browser. The existing page initially showed a cached draft;
reloading showed the current revision 3 finalized design and latest implementation record.

## Observed results

| Check | Observed result |
| --- | --- |
| Release navigation | Development → verification records → v0.4.x → v0.4.0 candidate → revision records. The current implementation page shows the latest runtime follow-up. |
| Search | Searching `Read your data` returned the reading guide plus configuration, schema and operations results. The first result described reader access without Tushare credentials. |
| Legacy URL | `/development/acceptance/?review=1#original-anchor` redirected to `/development/releases/v0.1/v0.1.0/acceptance/index.html?review=1#original-anchor`; both query and fragment survived. This tests preservation, not whether an arbitrary fragment names an existing heading. |
| Embedded CLI demo | Actual iframe rendered the simulated progress, rates and five recent events. Static text fallback and independent-page link remained outside the iframe. |
| Six demo modes | Rich/plain × quiet/normal/verbose switched successfully. Quiet kept paths, plain normal showed periodic lines, verbose added request events, Rich showed progress and bounded recent activity. These are prototype observations, not product tests. |
| Playback | Play moved to the completed scene, showing 10 successful blocks, 50,000 input rows and row shares totaling 100%; control changed to replay. |
| Narrow viewport | CLI demo inspected at 390×844; controls and wrapped result content remained visible with scrolling. Browser viewport override reset afterward. This is not a 40-column terminal check. |
| Project subpath | A temporary loopback-only preview served the built site under `/tushare-downloader/`. CLI and setup iframe targets resolved under that prefix and rendered; setup standalone prototype opened successfully. |
| Static fallback | Both demo pages display noninteractive explanations and links outside their iframe. Source/static checks establish availability without JS; JS-disabled browser mode itself was not toggled. GitHub Markdown limitations are explicitly explained. |

The temporary port-8786 prefix server was stopped after inspection; the pre-existing
port-8765 preview was left running and the browser returned to the design index.

## Build and automated evidence

- `uv run --locked zensical build --strict`: passed, 0.71s.
- `scripts/build_legacy_paths.py`: 131 aliases built.
- `scripts/check_cli_demo.py`: embedded iframe resolves; no nested frame/external scripts.
- `scripts/check_version_archives.py`: 131 manifest files and aliases, 7,911 relative links,
  no broken links. Historical file/hash validation remains attached to the manifest.
- Navigation and legacy-path unit modules: seven passed in 0.07s.

This closes R05/H04 and the browser portion of DL05/DL08. It does not sign off native
setup interaction, headless/database execution, production CLI layout or release gates.

## Separate documentation review finding

The standalone setup prototype still labels itself `revision 3 draft`, whereas its wrapper
and authoritative design index say finalized. The CLI prototype separately identifies its
v0.2.0 origin and old log-path differences. The setup draft label must be reconciled or
explicitly identified as a historical prototype label in the H03 documentation review;
no frozen design content was edited during this browser batch.
