# Ready inspection performance

Evidence from `test_ready_performance_and_sql_scope_empty_and_100k` against a disposable PostgreSQL cluster.
The fixture verifies its data directory and uses random database/account names. Production data is not used.

- Python: 3.12.3
- Client: Linux-6.18.33.2-microsoft-standard-WSL2-x86_64-with-glibc2.39
- Server: PostgreSQL 18.6 on x86_64-windows, compiled by msvc-19.44.35228, 64-bit
- Six registered data tables; loopback connection; one warm-up before each ten-sample sequence.
- Timings include the shared service and spawned database worker, excluding Textual cold startup.
- p95 uses nearest rank: with ten samples this is the maximum sample. Gate: at most 2 seconds.

| Raw daily rows | Database bytes | p95 seconds | Individual samples (seconds) |
| --- | --- | --- | --- |
| 0 | 8,574,655 | 0.2518 | 0.2310, 0.2458, 0.2518, 0.2240, 0.2478, 0.2279, 0.2266, 0.2432, 0.2288, 0.2284 |
| 100,000 | 20,862,655 | 0.2447 | 0.2324, 0.2349, 0.2244, 0.2447, 0.2266, 0.2264, 0.2248, 0.2242, 0.2305, 0.2240 |

## SQL and mutation checks

A separate traced invocation of the same inspection function captures every connection execute call
for each dataset size. Queries are SELECT statements over system catalogs, information_schema, the
single database identity record, and current login identity. Session timeout settings use set_config;
they do not change persistent database objects. No raw-table SELECT/COUNT/MAX or mutation occurs.
Identity, object owner and object ACL snapshots remain unchanged before and after both tracing and timing.
The parameter-free query text and raw timing samples are available in [JSON evidence](ready-performance.json).

This evidence covers Ready inspection only. It does not establish every repeat-apply, role-password,
configuration-file or upgrade invariant. Those remain separate acceptance items. Remote environments
are governed by configured operation budgets, not this local 2-second target.
