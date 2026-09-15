# Documentation development and deployment

```bash
uv sync --locked --all-groups
uv run zensical serve
uv run zensical build --strict --clean
```

The current complete design lives in design/. Its [entry page](../design/index.md) records the version in Chinese.

## GitHub Pages

The repository is [laiyk5/tushare-downloader](https://github.com/laiyk5/tushare-downloader).
Pages Source uses GitHub Actions. docs.yml builds pull requests without deployment permissions and deploys successful main builds.
No PAGES_ENABLED variable is required.

The project URL is derived from GITHUB_REPOSITORY. Deployment uses the same build artifact and checks that the commit remains main's current head.
To roll back, revert the documentation commit and push main to trigger a new build; do not upload an unchecked site directory.

Checks runs unit and real PostgreSQL integration tests on Linux. Local validation also covers WSL Python connecting to Windows PostgreSQL;
native Windows Python is outside the acceptance scope. Actions are pinned by SHA with corresponding tags in scripts/action-refs.json.
Record actual CI, Pages subpath, assets and rollback evidence. A local build does not prove deployment succeeded.

## Organization and maintenance

- guide/: everyday usage.
- reference/: commands and API contracts.
- operations/: database administration.
- development/: contributor methods and separate historical acceptance evidence.
- design/: versioned design specifications, maintained in Chinese.

Contributor tutorials and product documentation use English. Design, backlog and internal acceptance analysis use Chinese;
historical records retain their original language. Navigation labels follow the destination's purpose and language.
See the [language policy](../design/language-policy.md) for original-source exceptions.

Describe implemented behavior, not an unimplemented design as fact. Update user guides and references with command/configuration changes.
Changes to finalized design require an authorized revision with its own version history. Keep historical links working.

After local strict builds, check the pull request's docs-build result. Only merging to main deploys the public site.
