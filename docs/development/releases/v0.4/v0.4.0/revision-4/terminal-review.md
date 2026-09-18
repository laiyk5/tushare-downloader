# Revision 4 terminal verification

Owner: developer / agent. This is not a user checklist.

The maintainer reported no apparent problems and explicitly accepted revision 4.
This is an acceptance decision and positive usability feedback, not evidence that
all former manual routes were individually performed.

## Evidence and responsibility

- The 626-test regression covers mechanical dialogue branches, database outcomes,
  confirmation, save/recovery, plain output, representative widths and cancellation.
- Existing effective evidence is reused; users do not repeat those tests.
- Real terminal password echo and echo restoration require PTY state/output evidence.
  The current automated mapping does not establish that evidence; this specific gap
  belongs to the agent, not to the user. It must not be relabelled as a human pass.
- Optional host-terminal readability feedback is welcome and does not block delivery.

The isolated local helper remains available for developer checks:

```bash
cd /home/laiyk/projects/tools/tushare-downloader
uv run --locked python logs/revision-4-review/review.py
```

It targets only the guarded test server on port 55433 and its owned review objects;
it does not use the production .env. It is an ignored local helper, not a product command.
See [workflow responsibility](../../../../../design/workflow.md) for the governing rule.
