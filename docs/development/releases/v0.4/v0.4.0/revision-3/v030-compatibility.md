# Actual v0.3.0 database compatibility

Result: **Pass for DBW10's old baseline retention and scoped reader-grant scenario**.

Baseline: local `v0.3.0`, commit `db806c60eb7d080406aec358a243f331c1f4fc13`.
Test: `tests/cluster/test_setup_cluster.py::test_actual_v030_database_retains_identity_data_and_user_objects`.
Result: **1 passed in 2.26s** against the identity-checked disposable PostgreSQL cluster.

The test extracts the baseline Python sources into a temporary directory and runs their actual
Store.initialize in a separate Python process. It does not synthesize old tables with current code.
Current code creates only the fixture accounts/database beforehand, not the baseline table structure.
Shared installed dependencies are used; this proves schema compatibility with actual old source,
not reproducibility of the entire historic dependency environment.

The fixture adds one daily row and an analysis.saved_daily view. Before applying current setup it
captures the complete schema identity record, row values, view definition and result, and role
password state. Setup proposes only grants. After application all captured values match. Reinspection
reports Ready and repeated apply issues no additional database mutations.

Conclusion: **No migration required** for this supported baseline. Only planned reader grants are
added. Existing database identity, source data, user objects and passwords survive. The independent
reader-CONNECT repair test additionally proves that PUBLIC privileges are not broadened.

This does not prove arbitrary external schemas are compatible. Unknown structures must still be
rejected, and other composite acceptance requirements remain open. No production configuration or
database was read, and no software release was performed.
