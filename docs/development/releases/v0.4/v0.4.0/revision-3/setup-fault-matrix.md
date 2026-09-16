# Setup action fault matrix

This is implementation evidence for DBW05 and H08, not a change to the finalized design.

## Scope and isolation

The tests use a disposable PostgreSQL 18 cluster on port 55433. The fixture checks the exact
server data directory before mutation and uses randomly named databases and roles. The user's
configuration and production database are not used. Fixture cleanup is separate from setup:
setup never drops previously completed objects to roll back a partial plan.

Both tests below are in `tests/cluster/test_setup_cluster.py`. Each is parameterized over
`create-writer`, `create-reader`, `create-database`, `initialize`, and `grants`.

| Fault | Injection and authoritative checks |
| --- | --- |
| Pre-execution refusal | Controlled StorageError before the selected action; real catalog snapshot retains earlier actions and shows the refused action still pending. |
| SQL rejection | Actual PostgreSQL error inside the transaction; snapshot proves rollback of the selected action. CREATE DATABASE instead fails before creation because it is nontransactional. Initialization injects the error before Store's COMMIT. |
| Lost acknowledgement | Execute the real action, then discard its response; catalog shows it committed while the service reports Unknown and stops subsequent actions. |
| Client timeout | A spawned worker commits the real action, writes a test-only marker, and stalls before delivering its result. The five-second client deadline terminates it; the marker and catalog prove the commit preceded termination. |
| User cancellation | The same worker is cancelled after its commit marker appears. The service returns 130 and reports the current action as Unknown; previous completed actions remain separately reported. |

`test_each_action_preserves_real_transaction_outcomes` covers the first three rows (15 cases).
`test_each_action_bounded_termination_preserves_commits` covers the final two rows (10 cases).
The targeted matrix passed: **25 cases in 82.46 seconds**.

## Bounded termination and retry

For timeout/cancel cases, the measured failed worker call must finish in less than seven seconds:
a shortened five-second test budget plus the design's two-second termination allowance. This is
not the default configured timeout and does not include the service's separate read-only recheck.
No child process remains after the call. The test holds the result after commit; it does not claim
to reproduce every possible server-side network or in-flight SQL failure.

Every fault checks completed/failed/unknown/not-attempted lists and the exact dispatched action
sequence, so no unattended replay or next action can hide behind the final catalog state.
After timeout/cancel, a new user-requested inspection derives only the remaining operations.
Those operations complete successfully; an existing database identity remains unchanged.
A further Ready inspect/apply dispatches no writes. This is a fresh plan, not persisted resume state.

The native terminal restoration and human partial-failure presentation remain separate UI gates.
This matrix does not claim those gates passed.
