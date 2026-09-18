# v0.4.0 release

Release date: 2026-09-18. Publication was explicitly requested by the maintainer.
Design baseline: `design-v0.4.0-r7` / `5925e8a`. Tested implementation: `b51eba3`;
release preparation changes documentation and corrects password propagation in an integration-test fixture; application code is unchanged. The immutable software
commit is identified by [tag v0.4.0](https://github.com/laiyk5/tushare-downloader/releases/tag/v0.4.0).

## Changes since v0.3.0

- Guided database setup with existing-configuration discovery, editable choices,
  explicit change review and a non-interactive headless path.
- Versioned, ordered migrations through setup; standalone migrate is removed.
  The suspend_d key now includes suspend_type so multiple event kinds on the same
  stock/date can coexist without overwriting each other.
- Dataset Inspect overview and details, documented stable reader access and schema
  contracts, plus writer/reader role configuration and verification.
- Logs grouped by canonical command, clearer preparation failures and setup outcomes,
  safer option-placement hints, dataset purposes in list, and clearer quiet help.
- Upgrade guides, version-grouped development records and a local-first workflow.

## Upgrade

Follow the [v0.3.0 upgrade guide](../../../../operations/upgrading.md).
Keep the existing database and configuration; back up before structural migration.
Run setup to plan and confirm the supported suspend_d migration. Do not delete and
recreate the database. Existing data and database identity are preserved. A previous
major-line upgrade does not apply to this pre-1.0 release; the supported predecessor
is v0.3.0. Older versions require their documented intermediate upgrade path.

## Verification

- Final full regression: see [release regression](release-regression.txt).
  **723 passed in 253.90 seconds, no failures or skips.** Unit tests, database integration and database-administration integration tests run
  against isolated PostgreSQL 18; no production access or Tushare calls.
- Revision 7 [acceptance](revision-7/index.md) and earlier linked evidence cover the
  frozen requirements. This release run supersedes the earlier combined regression
  evidence for the final source tree; it does not rewrite historical results.
- A bounded real one-year download on 2026-09-18 wrote 5,342,909 rows to the development
  database in 1,317.96 seconds: 1,310 HTTP attempts, no failures, retries or unknown
  commits. All five previously reported suspend_d conflict dates succeeded. The five
  historical APIs each returned data on 242 dates and empty responses on the same 19
  weekday scopes. Raw data, credentials and private logs are not distributed.
- Offline lock check, Ruff check/format, wheel/sdist build, package-license/sensitive-file audit and isolated installation checks passed.
- Remote CI and Pages are release gates. Their actual status is recorded by the
  repository [Actions](https://github.com/laiyk5/tushare-downloader/actions) and GitHub
  Release; this document does not claim a remote result before its run completes.
- The existing same-artifact Pages deployment, obsolete-main guard and revert
  mechanism are retained. Local archive/legacy-path checks and online principal,
  legacy, search and demo checks apply to this publication.

## Limits and follow-ups

Successful API calls do not prove source completeness; empty responses remain
unverified. The real download did not exercise transient-error recovery because no
retries occurred. No production database was upgraded by the release procedure.
BL-022 through BL-027 are unplanned follow-ups, not delivered features.
MIT covers the project code; it grants no rights to redistribute Tushare data.

## Release CI correction

The first PR CI run (35323474339) exposed 23 failures in the inspection integration tests: nine Settings constructions omitted the password from TEST_DATABASE_URL. Local test connections did not require it. The fixture now passes the explicitly supplied test password; assertions, database isolation and application code are unchanged. The failing CI record is preserved; subsequent CI must pass before release.
