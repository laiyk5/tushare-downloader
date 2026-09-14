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

## Release checks still required

- Inspect the exact wheel/sdist, lockfile, transitive dependencies and any bundled native libraries.
- Preserve the notices and other obligations applicable to components actually redistributed.
- Review documentation site assets and the exported CLI demo separately: the CLI demo now uses only its own local HTML/CSS/JavaScript; unused generated scaffolding and CDN scripts have been removed.
  Do not label third-party material MIT solely because the repository has a root MIT license.
- Verify that package metadata declares MIT and that LICENSE is included in the wheel and sdist.
- Keep downloaded market data and credentials out of distributions.

These checks correspond to [K03 in the acceptance standard](../design/acceptance.md).
The choice of MIT is complete; final artifact review remains a release requirement.
