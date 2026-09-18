"""MG02: independently specified finite version-chain expectations."""

import pytest

from tushare_downloader.migration_chain import Migration, MigrationPlanError, plan


def step(api, source, target, dependencies=()):
    return Migration(f"{api}-{source}-{target}", api, source, target, dependencies)


@pytest.fixture
def chain():
    return (step("event", "1", "2"), step("event", "2", "3"), step("event", "3", "4"))


@pytest.mark.parametrize("start,expected", [("1", ["1", "2", "3"]), ("2", ["2", "3"]), ("4", [])])
def test_continuous_path_from_actual_version(chain, start, expected):
    assert [s.source for s in plan({"event": start}, {"event": "4"}, chain)] == expected


def test_missing_dataset_is_initialization_not_migration(chain):
    assert plan({}, {"event": "4"}, chain) == ()


@pytest.mark.parametrize("installed", ["0", "5", "unknown"])
def test_unknown_or_newer_version_has_no_path(chain, installed):
    with pytest.raises(MigrationPlanError):
        plan({"event": installed}, {"event": "4"}, chain)


@pytest.mark.parametrize(
    "registry",
    [
        (step("event", "1", "2"), step("event", "3", "4")),
        (step("event", "1", "2"), step("event", "2", "1")),
        (step("event", "1", "2"), step("event", "1", "3")),
        (step("other", "1", "2", ("event-1-2",)), step("event", "1", "2")),
    ],
)
def test_invalid_chain_rejected_before_execution(registry):
    with pytest.raises(MigrationPlanError):
        plan({"event": "1", "other": "1"}, {"event": "4", "other": "2"}, registry)


def test_independent_datasets_have_stable_registered_order():
    registry = (step("b", "1", "2"), step("a", "1", "2", ("b-1-2",)))
    result = plan({"a": "1", "b": "1"}, {"a": "2", "b": "2"}, registry)
    assert result == registry
    assert plan({"a": "1", "b": "2"}, {"a": "2", "b": "2"}, registry) == (registry[1],)


def test_duplicate_ids_and_unknown_dependencies_rejected():
    for registry in (
        (step("a", "1", "2"), step("a", "1", "2")),
        (step("a", "1", "2", ("missing",)),),
    ):
        with pytest.raises(MigrationPlanError):
            plan({"a": "1"}, {"a": "2"}, registry)
