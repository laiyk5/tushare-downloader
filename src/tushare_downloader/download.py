"""Sequential download execution; a snapshot is one atomic logical slice."""

import logging
import time
from dataclasses import asdict, replace
from datetime import UTC, date, datetime, timedelta

import click
import psycopg

from .apis.stock_basic import STOCK_STATUSES
from .calendar import CalendarError, filter_requests
from .client import RequestError, TushareClient
from .planning import Block, blocks, request_reason, update_range
from .reporting import Reporter, detail
from .storage import CommitUnknown, Counts, StorageError


def label(api, block):
    return (
        "Full snapshot"
        if api.query_kind == "snapshot"
        else f"{block.requested_start}..{block.requested_end}"
    )


def plan(store, api, command, settings, start=None, end=None, now=None):
    now = now or datetime.now(UTC)
    if api.query_kind == "snapshot":
        if start is not None or end is not None:
            raise ValueError("Snapshot APIs do not accept dates.")
        selected = (
            Block(0, date(1970, 1, 1), date(1970, 1, 1), date(1970, 1, 1), date(1970, 1, 1)),
        )
    else:
        if command == "update":
            start, end = update_range(api, store.latest(api), settings.lookback_days, now)
        elif start is None or end is None:
            raise ValueError("Time-range APIs require both --start and --end.")
        if start > end:
            raise ValueError("Start date must not be after end date.")
        # Explicit requests may include provisional dates; future dates cannot be requested.
        today = api.available_end(now) + timedelta(days=1)
        if end > today:
            raise ValueError("End date must not be after today in Asia/Shanghai.")
        selected = blocks(
            start,
            end,
            origin=api.block_origin,
            size=api.block_days,
            available_start=date(1900, 1, 1),
            available_end=today,
        )
    result = []
    for block in selected:
        observation = store.observation(api, block)
        # Yesterday's success obtained before its stable endpoint must be rechecked.
        if api.query_kind == "time-range" and observation and observation.last_success_at:
            if block.requested_end > api.available_end(observation.last_success_at):
                observation = replace(observation, local_consistent=False)
        reason = request_reason(
            command,
            block,
            observation,
            spec_version=api.spec_version,
            now=now,
            max_age=settings.max_age,
            empty_recheck_age=settings.empty_recheck_age,
        )
        state = (
            "Not checked"
            if observation is None
            else (
                "Failed"
                if observation.failed
                else "Locally inconsistent"
                if not observation.local_consistent
                else "Empty / unverified"
                if observation.empty
                else "Fetched"
            )
        )
        result.append((block, reason, state))
    return result


def retrieve(client, api, block, budget, on_result=None, on_subrequest=None):
    if api.query_kind == "time-range":
        if block.requested_start != block.requested_end:
            raise ValueError("daily_basic requires one date per request block.")
        result = client.query(api, {"trade_date": block.requested_start.strftime("%Y%m%d")})
        if on_result:
            on_result(result.received_rows)
        return result
    # All declared status requests belong to one snapshot, not five independent commits.
    from .client import ApiResult

    seen, received, duplicates, attempts, size = {}, 0, 0, 0, 0
    key_positions = [api.field_names.index(name) for name in api.unique_key]
    for status in STOCK_STATUSES:
        try:
            result = client.query(api, {"list_status": status})
        except (RequestError, KeyboardInterrupt):
            if on_subrequest:
                on_subrequest(status, "Failed", 0)
            raise
        if on_subrequest:
            on_subrequest(status, "Received", result.received_rows)
        if on_result:
            on_result(result.received_rows)
        status_position = api.field_names.index("list_status")
        if any(row[status_position] != status for row in result.rows):
            raise RequestError("scope", "Snapshot listing status does not match the request.")
        received += result.received_rows
        duplicates += result.duplicate_rows
        attempts += result.attempts
        for row in result.rows:
            key = tuple(row[pos] for pos in key_positions)
            if key in seen:
                if seen[key] != row:
                    raise RequestError(
                        "duplicate_conflict",
                        "Conflicting values for the same key across snapshot requests.",
                    )
                duplicates += 1
            else:
                size += sum(len(str(value).encode()) for value in row) + 128
                if size > budget:
                    raise RequestError(
                        "response_size", "Snapshot exceeds the configured buffer budget."
                    )
                seen[key] = row
    return ApiResult(tuple(seen.values()), received, duplicates, attempts)


def execute(store, api, command, settings, *, reporter=None, **kwargs):
    if reporter is not None:
        return _execute(store, api, command, settings, reporter=reporter, **kwargs)
    with Reporter(
        settings, api, command, quiet=kwargs.get("quiet", False), verbose=kwargs.get("verbose", 0)
    ) as owned:
        return _execute(store, api, command, settings, reporter=owned, **kwargs)


def _execute(
    store,
    api,
    command,
    settings,
    *,
    start=None,
    end=None,
    dry_run=False,
    quiet=False,
    verbose=0,
    client_factory=TushareClient,
    reporter=None,
    ignore_calendar=False,
):
    reconcile = command == "refresh" or (command == "update" and api.change_kind == "mutable")
    if reconcile and not api.stale_scope_verified:
        raise ValueError(f"{api.name} reconciliation is unverified; cannot execute {command}.")
    invocation_started = time.monotonic()
    store.validate(api)
    selected = plan(store, api, command, settings, start, end)
    check_plan_seconds = time.monotonic() - invocation_started
    pending = [(block, reason) for block, reason, _ in selected if reason]
    skipped = len(selected) - len(pending)
    calendar_attempts = 0

    def calendar_attempt(name, attempt):
        nonlocal calendar_attempts
        calendar_attempts += 1
        reporter.event("calendar_http_attempt", attempt=attempt)

    try:
        calendar = filter_requests(
            api,
            pending,
            settings,
            ignore=ignore_calendar,
            dry_run=dry_run,
            client_factory=client_factory,
            on_attempt=calendar_attempt,
        )
    except CalendarError as error:
        reporter.report(
            "after",
            "Calendar preparation failed",
            [
                str(error),
                "Plan: incomplete; filtering decisions not determined",
                f"Candidate blocks: {len(pending)}",
                "Data requests: 0",
                f"Calendar HTTP attempts: {calendar_attempts}",
            ],
            explicit=True,
            sections=[("Undetermined", [detail(api, b, reason) for b, reason in pending])],
        )
        reporter.event(
            "invocation_finished",
            preparation_failed=True,
            calendar_requests=calendar_attempts,
            data_requests=0,
        )
        return 1
    pending = calendar.requested
    reporter.event(
        "calendar_plan",
        mode=calendar.mode,
        bypassed=calendar.bypassed,
        sources=calendar.sources,
        filtered=len(calendar.filtered),
    )
    if pending and not dry_run:
        settings.require_token()
    outcomes, total_counts = [], Counts()
    success = empty = failed = unknown = attempts = written = 0
    interrupted = False
    db_seconds = 0.0
    client = None
    active_considered = 0
    active_block = None
    try:
        active, stale = store.counts(api)
        actual = (
            f"{min(b.requested_start for b, _ in pending)}..{max(b.requested_end for b, _ in pending)} (see detailed ranges)"
            if pending and api.query_kind == "time-range"
            else "Full snapshot"
            if pending
            else "none"
        )
        lines = [
            f"API: {api.name}",
            f"Command: {command}; kind: {api.change_kind}/{api.query_kind}",
            f"Scope: {start}..{end}" if start else "Scope: determined by API update policy",
            f"Request scope: {actual}",
            f"Local table: active={active}; stale={stale}",
            f"Planned blocks: {len(pending)}; skipped={skipped}",
        ]
        if api.query_kind == "snapshot":
            lines[2] = "Scope: full snapshot"
        if command == "refresh":
            lines.append(f"Max age: {settings.max_age}")
        if command == "update" and api.query_kind == "time-range":
            lines.append(f"Lookback: {settings.lookback_days} days from latest local date")
        if api.name == "daily_basic":
            lines.extend(
                [
                    f"Calendar: {calendar.mode}; bypassed={calendar.bypassed}",
                    f"Filtered: {len(calendar.filtered)}; calendar HTTP attempts={calendar_attempts}",
                ]
            )
            if calendar.sources:
                lines.append(
                    f"Calendar source: {calendar.sources}; SSE represents regular A-share trading days"
                )
        before_sections = [
            ("Filtered", [detail(api, b, calendar.mode) for b, _ in calendar.filtered]),
            (
                "Request",
                [
                    detail(api, b, f"{state}; request reason={reason}")
                    for b, reason, state in selected
                    if reason
                ],
            ),
            (
                "Skipped",
                [
                    detail(api, b, f"{state}; valid successful record")
                    for b, reason, state in selected
                    if not reason
                ],
            ),
        ]
        filtered_ids = {b.id for b, _ in calendar.filtered}
        for block, reason, state in selected:
            decision = (
                "Filtered" if block.id in filtered_ids else "Request" if reason else "Skipped"
            )
            reporter.plan_block(
                label(api, block),
                decision,
                calendar.mode if decision == "Filtered" else reason or state,
            )
        if api.query_kind == "snapshot" and pending:
            reporter.subrequests = {status: ("Not attempted", 0) for status in STOCK_STATUSES}
        reporter.report(
            "before", "Local check and plan", lines, explicit=dry_run, sections=before_sections
        )
        for block, reason, state in selected:
            reporter.event(
                "coverage_before", scope=label(api, block), reason=reason, local_state=state
            )
        if reporter.io_failed:
            return 1
        if dry_run:
            reporter.event(
                "invocation_finished", dry_run=True, planned=len(pending), skipped=skipped
            )
            click.echo("Plan only; no remote requests or database changes.")
            return 0
        reporter.begin(len(pending))
        consecutive = 0

        def retry(category, attempt, delay):
            reporter.event(
                "retry",
                level=logging.WARNING,
                category=category,
                attempt=attempt,
                delay_seconds=delay,
            )
            click.echo(f"Retry: {category}; attempt {attempt}, waiting {delay:.1f}s.", err=True)

        def attempt_event(name, attempt):
            reporter.attempt()
            reporter.event("http_attempt", attempt=attempt, scope=reporter.scope)

        def phase(stage):
            reporter.phase(stage)
            reporter.event("phase", level=logging.DEBUG, stage=stage, scope=reporter.scope)

        with (
            client_factory(settings, on_retry=retry, on_attempt=attempt_event, on_phase=phase)
            if pending
            else _NoClient() as client
        ):
            for block, reason in pending:
                active_block = block
                stamp = datetime.now(UTC)
                scope = label(api, block)
                stop = False
                reporter.begin_slice(scope)
                start_attempts = getattr(client, "attempts", attempts)
                committed_rows = 0
                try:
                    result = retrieve(
                        client,
                        api,
                        block,
                        settings.max_response_bytes,
                        reporter.receive,
                        reporter.subrequest,
                    )
                    attempts += result.attempts
                    reporter.phase("Committing")
                    prior_active = store.counts(api, block)[0] if reconcile and result.rows else 0
                    db_started = time.monotonic()
                    try:
                        counts = store.merge(api, block, result.rows, stamp, reconcile=reconcile)
                    finally:
                        db_seconds += time.monotonic() - db_started
                    active_considered += prior_active
                    committed_rows = len(result.rows)
                    written += len(result.rows)
                    for field, value in asdict(counts).items():
                        setattr(total_counts, field, getattr(total_counts, field) + value)
                    if result.rows:
                        success += 1
                        outcome = "success"
                    else:
                        empty += 1
                        outcome = "empty_unverified"
                    consecutive = 0
                    reporter.event(
                        "slice_result",
                        scope=scope,
                        outcome=outcome,
                        received_rows=result.received_rows,
                        duplicate_rows=result.duplicate_rows,
                        committed_rows=len(result.rows),
                        attempts=result.attempts,
                        **asdict(counts),
                    )
                except RequestError as error:
                    failed += 1
                    consecutive += 1
                    store.failed(api, block, stamp)
                    outcome = f"failed: {error.category}"
                    reporter.event(
                        "slice_result",
                        level=logging.ERROR,
                        scope=scope,
                        outcome="failed",
                        category=error.category,
                    )
                    click.echo(f"{scope} Failed: {error}", err=True)
                    stop = error.category in {"business", "http", "tls", "retry_deferred"}
                    stop |= bool(
                        settings.max_consecutive_failed_slices
                        and consecutive >= settings.max_consecutive_failed_slices
                    )
                except CommitUnknown as error:
                    interrupted = error.interrupted
                    unknown += 1
                    committed_rows = "unknown"
                    outcome = "commit_unknown"
                    reporter.event(
                        "slice_result", level=logging.ERROR, scope=scope, outcome=outcome
                    )
                    stop = True
                except (psycopg.Error, StorageError):
                    failed += 1
                    outcome = "database_failed"
                    reporter.event(
                        "slice_result", level=logging.ERROR, scope=scope, outcome=outcome
                    )
                    click.echo(
                        "Database write failed; stopping requests. Unconfirmed commits are not counted as successful.",
                        err=True,
                    )
                    stop = True
                attempts = getattr(client, "attempts", attempts)
                reporter.finish_block(
                    scope, outcome, max(0, attempts - start_attempts), committed_rows
                )
                outcomes.append((block, outcome))
                active_block = None
                stop |= reporter.io_failed
                if verbose:
                    click.echo(f"{scope} | {outcome}", err=True)
                reporter.advance(
                    len(outcomes), len(pending), written, attempts, failed, empty, stopped=stop
                )
                if stop:
                    break
    except KeyboardInterrupt:
        interrupted = True
        if active_block is not None:
            failed += 1
            reporter.finish_block(
                label(api, active_block),
                "failed: interrupted",
                max(0, getattr(client, "attempts", attempts) - start_attempts),
                0,
            )
            outcomes.append((active_block, "failed: interrupted"))
    finally:
        reporter.stop_progress()
        if not dry_run:
            remaining = len(pending) - success - empty - failed - unknown
            conclusion = (
                "Output failed; confirmed commits retained"
                if reporter.io_failed
                else "Interrupted"
                if interrupted
                else "Completed with failures or stopped early"
                if failed or unknown or remaining
                else "Completed with empty responses"
                if empty
                else "Nothing to download"
                if not pending
                else "Completed"
            )

            def pct(value, denominator):
                return f"{value / denominator:.1%}" if denominator else "not applicable"

            lines = [
                conclusion,
                f"Blocks: {len(pending)} planned; {success} non-empty; {empty} empty; {failed} failed; {unknown} unknown; {remaining} unattempted; {skipped} skipped",
                f"Success rate: {pct(success + empty, len(pending))}; failure rate: {pct(failed, len(pending))}",
                f"Committed input rows: {written}",
                *[
                    f"{name}: {value} ({pct(value, written)})"
                    for name, value in [
                        ("Inserted", total_counts.inserted),
                        ("Updated", total_counts.changed),
                        ("Unchanged", total_counts.unchanged),
                        ("Reactivated", total_counts.reactivated),
                    ]
                ],
                f"Newly stale: {total_counts.stale} / prior active {active_considered} ({pct(total_counts.stale, active_considered)})",
            ]
            if not reconcile:
                lines[-1] = "Missing-key reconciliation: not applied"
            if not pending and not reporter.io_failed:
                lines = [
                    conclusion,
                    f"Blocks: 0 planned; {skipped} skipped",
                    f"Data requests: 0; calendar HTTP attempts: {calendar_attempts}. No rows written.",
                ]
            sections = [
                (
                    "Failed",
                    [
                        detail(api, b, o)
                        for b, o in outcomes
                        if o.startswith("failed") or o == "database_failed"
                    ],
                ),
                (
                    "Commit outcome unknown",
                    [detail(api, b, o) for b, o in outcomes if o == "commit_unknown"],
                ),
                (
                    "Not attempted / unfinished",
                    [
                        detail(api, b, "Not attempted / unfinished")
                        for b, _ in pending[len(outcomes) :]
                    ],
                ),
                (
                    "Empty / unverified",
                    [detail(api, b, o) for b, o in outcomes if o == "empty_unverified"],
                ),
                ("Success", [detail(api, b, o) for b, o in outcomes if o == "success"]),
            ]
            if failed or unknown or remaining:
                lines.append(
                    "Retry failed ranges with fetch; use refresh for historical reconciliation."
                )
            try:
                reporter.report(
                    "after",
                    "Result",
                    lines,
                    explicit=bool(
                        failed or empty or unknown or remaining or interrupted or reporter.io_failed
                    ),
                    sections=sections,
                )
                reporter.event(
                    "invocation_finished",
                    success=success,
                    empty=empty,
                    failed=failed,
                    unknown=unknown,
                    unattempted=remaining,
                    skipped=skipped,
                    filtered=len(calendar.filtered),
                    calendar_requests=calendar_attempts,
                    data_requests=getattr(client, "attempts", attempts),
                    interrupted=interrupted,
                    committed_rows=written,
                    http_attempts=getattr(client, "attempts", attempts),
                    response_bytes=getattr(client, "response_bytes", 0),
                    total_seconds=time.monotonic() - invocation_started,
                    check_plan_seconds=check_plan_seconds,
                    db_seconds=db_seconds,
                    report_seconds=reporter.report_seconds,
                    log_seconds=reporter.handler.seconds,
                    **getattr(client, "timings", {}),
                    **asdict(total_counts),
                )
                for block, outcome in outcomes:
                    reporter.event("coverage_after", scope=label(api, block), outcome=outcome)
            finally:
                reporter.close()
        else:
            reporter.close()
    return (
        130
        if interrupted
        else 1
        if failed or unknown or reporter.io_failed or len(outcomes) < len(pending)
        else 0
    )


class _NoClient:
    def __enter__(self):
        return None

    def __exit__(self, *_):
        pass
