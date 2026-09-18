# Setup authentication regression

The reader verification failure reported during terminal testing exposed two gaps: a new role
could be created without a password without a separate warning, and the worker discarded useful
authentication diagnostics. Completed database steps were also missing from the verification error.

The correction preserves the existing design: no automatic password reset, no rollback of completed
setup steps, and no change to server authentication. Passwordless role creation now needs explicit
confirmation. Verification failures name the account and completed steps, and provide recovery
guidance. Driver diagnostics use allowlisted messages rather than raw connection error text.

## Validation

- Before implementation: five new regression cases failed; the generic-error redaction case passed.
- After implementation: 333 unit, integration and disposable-cluster tests passed.
- Ruff check and format check passed; strict Zensical build passed.
- Additional real SCRAM authentication experiment on the isolated PostgreSQL test cluster, port
  55433: an empty reader password failed with the safe missing-password diagnostic; assigning a
  password restored reader verification; an incorrect password produced the safe rejected-password
  diagnostic. Replanning after recovery required no database mutations.
- The experiment checked the cluster data directory before changes, used random role/database names,
  and restored its temporary reader-specific authentication rule and removed its objects afterward.
  The production database on port 5432 was not used or modified.

The SCRAM experiment was an additional manual automation check; the regular cluster fixture still
uses trust authentication. This correction does not close the remaining acceptance items listed in
the [revision record](index.md), and does not constitute a software release.
