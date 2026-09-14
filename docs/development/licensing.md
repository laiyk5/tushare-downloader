# License decision and distribution review

The maintainer selected MIT for original project code and documentation. The root
LICENSE uses the existing project author, Yikai Lai. Third-party components retain
their own licenses. The code license grants no rights to redistribute Tushare data;
data access, use and redistribution are governed separately by applicable provider terms.

The standard MIT text is available from the [Open Source Initiative](https://opensource.org/license/mit).
No data-specific restriction was inserted into the standard license text; the scope
statement is documented separately in README and the design.

## Initial runtime dependency inventory

Read from installed package METADATA matching the current environment, 2026-09-14.
This is an initial inventory, not a certification of every transitive dependency or artifact.

| Distribution | Version | Declared license |
| --- | --- | --- |
| click | 8.5.0 | BSD-3-Clause |
| requests | 2.34.2 | Apache-2.0 |
| psycopg | 3.3.5 | LGPL-3.0-only |
| psycopg-binary | 3.3.5 | LGPL-3.0-only |
| python-dotenv | 1.2.3 | BSD-3-Clause |
| rich | 15.0.0 | MIT |
| tzdata | 2026.4 | Apache-2.0 (additional bundled data notices must be preserved) |

Dependencies are installed as separate distributions; declaring project MIT does not
relicense them. In particular, preserve Psycopg's LGPL terms and notices when distributing
its components. Binary distributions may include additional native libraries.
See [Psycopg binary installation](https://www.psycopg.org/psycopg3/docs/basic/install.html#binary-installation).

## v0.2.0 artifact review

The [runtime inventory](runtime-distribution-v0.2.0.json) traverses active dependency requirements, including the Psycopg binary extra, and matches installed versions to uv.lock. It lists each distribution's declared license, notice files and native libraries. Runtime dependency artifacts remain separately installed; none are embedded in the project wheel or sdist. This project does not publish a combined runtime bundle or container image.

`scripts/check_distribution.py` verifies the exact project wheel/sdist contents, matching MIT text and metadata, and exclusion of credentials, logs, market data and native libraries. The isolated wheel checks are recorded in [acceptance evidence](acceptance-v0.2.0.md).

The generated documentation redistributes Zensical theme assets. [Third-party notices](../third-party/index.md) include unchanged supplier and exact JavaScript package license texts, with source URLs and hashes. `scripts/check_site_notices.py` checks the locked supplier version and both source and built-site files before CI uploads an artifact. The CLI demo uses project-local HTML/CSS/JavaScript with no third-party script dependency.

These findings apply to the current package and documentation artifacts. Shipping separate dependency wheels or a combined runtime in a future release requires reviewing that new distribution, including its native-library obligations. The original project MIT license does not relicense dependencies or grant Tushare data redistribution rights.
