"""Explicit, version-based migrations; no schema inference or persisted jobs."""

from dataclasses import dataclass
from time import monotonic

from psycopg.types.json import Jsonb

from .storage import StorageError, Store


class MigrationPlanError(StorageError, ValueError):
    pass


@dataclass(frozen=True)
class Migration:
    id: str
    api: str
    source: str
    target: str
    dependencies: tuple[str, ...] = ()


def plan(installed, expected, registry):
    registry = tuple(registry)
    by_id, edges = {}, {}
    for item in registry:
        if item.id in by_id or (item.api, item.source) in edges:
            raise MigrationPlanError("Duplicate or ambiguous migration registration.")
        if item.source == item.target or any(dep not in by_id for dep in item.dependencies):
            raise MigrationPlanError("Invalid migration order or dependency.")
        by_id[item.id] = item
        edges[item.api, item.source] = item
    for item in registry:
        seen, version = set(), item.source
        while (item.api, version) in edges:
            if version in seen:
                raise MigrationPlanError("Cyclic migration registration.")
            seen.add(version)
            version = edges[item.api, version].target
    current = dict(installed)
    selected = []
    for item in registry:
        if current.get(item.api) != item.source or current.get(item.api) == expected.get(item.api):
            continue
        if item.api not in expected:
            continue
        for dep in item.dependencies:
            required = by_id[dep]
            version = required.target
            satisfied_versions = {version}
            while (required.api, version) in edges:
                version = edges[required.api, version].target
                satisfied_versions.add(version)
            if current.get(required.api) not in satisfied_versions:
                raise MigrationPlanError("Migration dependency is not satisfied.")
        selected.append(item)
        current[item.api] = item.target
    if any(current[api] != version for api, version in expected.items() if api in installed):
        raise MigrationPlanError("No complete supported migration path.")
    return tuple(selected)


REGISTRY = (Migration("suspend_d-spec-1-to-2", "suspend_d", "1", "2"),)


def execute_steps(conn, steps, expected_identity, expected_specs, handlers, emit):
    store = Store(conn)
    versions = dict(expected_specs)
    with store.writer():
        identity, actual = store.identity()
        if str(identity) != expected_identity or actual != versions:
            raise StorageError("Database changed since preview; review a new plan.")
        for index, step in enumerate(steps):
            fields = dict(
                action=step.id,
                step_id=index + 1,
                migration_id=step.id,
                scope=step.api,
                from_version=step.source,
                to_version=step.target,
                database_id=expected_identity,
            )
            emit("step_started", fields)
            started = monotonic()
            with store.transaction():
                conn.execute("LOCK TABLE meta.schema_info IN ACCESS EXCLUSIVE MODE")
                identity, actual = store.identity()
                if (
                    str(identity) != expected_identity
                    or actual != versions
                    or versions.get(step.api) != step.source
                ):
                    raise StorageError("Database changed since preview; review a new plan.")
                handlers[step.id](store, step)
                versions[step.api] = step.target
                conn.execute("UPDATE meta.schema_info SET specs=%s", (Jsonb(versions),))
            emit(
                "step_finished",
                fields
                | dict(outcome="completed", duration_ms=round((monotonic() - started) * 1000)),
            )
    return versions
