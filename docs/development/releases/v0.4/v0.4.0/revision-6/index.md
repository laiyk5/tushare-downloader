# Revision 6 implementation and verification

Design baseline: `design-v0.4.0-r6` / `225eef2`. This candidate is local and unreleased.
Production was not accessed; no Tushare HTTP requests were made.

## Delivered changes

- Setup now inspects actual schema/spec versions and plans registered migrations in order.
  The separate migrate command is removed. New tables start at their current schema.
- The chain keeps one writer lock across per-step transactions. A failed step rolls back;
  earlier commits remain. Subsequent setup runs read actual versions and plan remaining work.
- Interactive setup reviews changes and asks for the database name once. Headless checks are
  read-only; migration apply requires --confirm-database. Logs use logs/setup and carry step versions.
- A persistent resettable development database, tushare_dev, is configured in private .env.dev.
  Automated tests retain independent disposable databases. Production use is restricted by
  development policy to officially released, unmodified code.

## Test-first and corrections

The planner first produced 13 behavioral failures; the transaction runner produced four;
acknowledged worker events produced three; setup confirmation/order produced two. Import-only
scaffolding failures were corrected before recording the behavioral red tests. Those records
are [planning](test-first-planning.txt), [transactions](test-first-execution.txt),
[worker events](test-first-bounded.txt), and [setup](test-first-setup.txt).

Real database tests found an old-schema snapshot was skipping the existing reader ACL check,
incorrectly planning a grants action after migration. Both schema states now use the same ACL
inspection. The subsequent actual v0.3.0 public CLI route passed.

Terminal review exposed a stale migration_needed reason after successful Ready. The new
independent assertion first failed, then passed after clearing the resolved reason. The same
terminal scenario was repeated for this concrete defect; no additional platform matrix was added.
Migration previews also display database identity. The final affected suite is
[97 passing tests](terminal-fix-tests.txt); [terminal output](terminal-migration.txt) and
[PTY result](terminal-review.json) reflect the correction.

## Environment and evidence boundaries

The isolated PostgreSQL service was stopped. Windows refused to bind its previous port 55433;
the same positively identified test data directory was started on 55434. No production server
or cluster directory was substituted. [Development database evidence](development-database.json)
records the endpoint, application identity, one reset/rebuild and unchanged other database OIDs.
[Creation](development-create.txt) and [recreation](development-recreate.txt) used the public setup command.
Roles use this isolated cluster's existing authentication policy; no production credentials are copied.

The [first full regression](regression-initial.txt) reported 680 passes and two environment failures
because SETUP_TEST_PSQL was missing. Providing the existing PostgreSQL 18 client path resolved both;
[the focused run](focused-final.txt) passed five cases, including actual old-version upgrade.
The [final full regression](regression.txt) and [final unit run](unit-final.txt) retain their exact output.
The narrow terminal-reason/presentation correction has the separate 97-case evidence above; results
are not falsely described as all using an identical tree. Unaffected data/HTTP semantics retain
revision 5 evidence at its original commit, including its accepted budget deviation.

[Acceptance mapping](acceptance.md) links every MG requirement to its primary evidence.
[Installed package smoke](installed-setup.txt) and candidate fingerprint accompany the local commit.
No push, PR, GitHub workflow, software tag or release is part of this work.

## Acceptance closure

Revision 6 is implemented and accepted locally. The complete regression passed **683 tests in
198.79 seconds**. The final terminal reason/identity presentation correction passed its **97-test
affected suite** and the same real PTY scenario; the enriched old-tag active/stale/coverage/index
fixture passed in [the final old-version run](old-version-final.txt). These evidence boundaries are
explicit; no claim is made that the earlier full run contained the later additional assertion.

Final Ruff, format and whitespace checks passed. Wheel/sdist and isolated installed setup checks
passed. Strict Zensical build and archive/link checks passed. The [candidate fingerprint](candidate-fingerprint.json)
identifies code/test/build inputs. The only endpoint adjustment was the isolated service port,
recorded above; no product requirement or request budget was relaxed.

For development, use `uv run tushare-downloader -c .env.dev setup` after checking that inherited
PG* variables do not override the development file. No production migration or release occurred.

Stored text transcripts have trailing whitespace removed for repository hygiene; result content is unchanged.
