"""Sequential download execution; a snapshot is one atomic logical slice."""

import logging
import time
from dataclasses import asdict, replace
from datetime import UTC, date, datetime, timedelta

import click
import psycopg

from .apis.stock_basic import STOCK_STATUSES
from .client import RequestError, TushareClient
from .planning import Block, blocks, request_reason, update_range
from .reporting import Reporter, detail
from .storage import CommitUnknown, Counts, StorageError


def label(api, block):
    return (
        "当前全集"
        if api.query_kind == "snapshot"
        else f"{block.requested_start}..{block.requested_end}"
    )


def plan(store, api, command, settings, start=None, end=None, now=None):
    now = now or datetime.now(UTC)
    if api.query_kind == "snapshot":
        if start is not None or end is not None:
            raise ValueError("快照接口不接受日期范围。")
        selected = (
            Block(0, date(1970, 1, 1), date(1970, 1, 1), date(1970, 1, 1), date(1970, 1, 1)),
        )
    else:
        if command == "update":
            start, end = update_range(api, store.latest(api), settings.lookback_days, now)
        elif start is None or end is None:
            raise ValueError("时间范围接口必须同时指定 --start 和 --end。")
        if start > end:
            raise ValueError("开始日期不能晚于结束日期。")
        # Explicit requests may include provisional dates; future dates cannot be requested.
        today = api.available_end(now) + timedelta(days=1)
        if end > today:
            raise ValueError("结束日期不能晚于上海当前日期。")
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
            "未查"
            if observation is None
            else (
                "失败"
                if observation.failed
                else "本地不一致"
                if not observation.local_consistent
                else "空响应待核实"
                if observation.empty
                else "已取得"
            )
        )
        result.append((block, reason, state))
    return result


def retrieve(client, api, block, budget, on_result=None):
    if api.query_kind == "time-range":
        if block.requested_start != block.requested_end:
            raise ValueError("daily_basic 当前只支持每日一个请求块。")
        result = client.query(api, {"trade_date": block.requested_start.strftime("%Y%m%d")})
        if on_result:
            on_result(result.received_rows)
        return result
    # All declared status requests belong to one snapshot, not five independent commits.
    from .client import ApiResult

    seen, received, duplicates, attempts, size = {}, 0, 0, 0, 0
    key_positions = [api.field_names.index(name) for name in api.unique_key]
    for status in STOCK_STATUSES:
        result = client.query(api, {"list_status": status})
        if on_result:
            on_result(result.received_rows)
        status_position = api.field_names.index("list_status")
        if any(row[status_position] != status for row in result.rows):
            raise RequestError("scope", "快照响应的上市状态与请求不符。")
        received += result.received_rows
        duplicates += result.duplicate_rows
        attempts += result.attempts
        for row in result.rows:
            key = tuple(row[pos] for pos in key_positions)
            if key in seen:
                if seen[key] != row:
                    raise RequestError("duplicate_conflict", "快照不同请求出现同键不同值。")
                duplicates += 1
            else:
                size += sum(len(str(value).encode()) for value in row) + 128
                if size > budget:
                    raise RequestError("response_size", "整个快照超过配置的缓冲预算。")
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
):
    reconcile = command == "refresh" or (command == "update" and api.change_kind == "mutable")
    if reconcile and not api.stale_scope_verified:
        raise ValueError(f"{api.name} 的完整核对能力尚未验证，暂不能执行 {command}。")
    invocation_started = time.monotonic()
    store.validate(api)
    selected = plan(store, api, command, settings, start, end)
    check_plan_seconds = time.monotonic() - invocation_started
    pending = [(block, reason) for block, reason, _ in selected if reason]
    skipped = len(selected) - len(pending)
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
            f"{min(b.requested_start for b, _ in pending)}..{max(b.requested_end for b, _ in pending)}（详细范围见下）"
            if pending and api.query_kind == "time-range"
            else "当前全集"
            if pending
            else "无"
        )
        lines = [
            f"API：{api.name}",
            f"命令：{command}；分类：{api.change_kind}/{api.query_kind}",
            f"用户范围：{start}..{end}" if start else "用户范围：按接口/更新规则确定",
            f"实际请求范围：{actual}",
            f"本地全表：active={active}；stale={stale}",
            f"计划请求={len(pending)}；跳过={skipped}",
            f"核对最大年龄：{settings.max_age}；回看：{settings.lookback_days} 天",
        ]
        before_sections = [
            (
                "需请求",
                [
                    detail(api, b, f"{state}；请求依据={reason}")
                    for b, reason, state in selected
                    if reason
                ],
            ),
            (
                "可跳过",
                [
                    detail(api, b, f"{state}；成功记录有效")
                    for b, reason, state in selected
                    if not reason
                ],
            ),
        ]
        reporter.report(
            "before", "本地检查与计划", lines, explicit=dry_run, sections=before_sections
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
            click.echo("仅完成本地计划；未请求远端、未修改数据库。")
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
            click.echo(f"请求重试：{category}；已尝试 {attempt} 次，等待 {delay:.1f}s。", err=True)

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
                try:
                    result = retrieve(
                        client, api, block, settings.max_response_bytes, reporter.receive
                    )
                    attempts += result.attempts
                    reporter.phase("合并提交")
                    prior_active = store.counts(api, block)[0] if reconcile and result.rows else 0
                    db_started = time.monotonic()
                    try:
                        counts = store.merge(api, block, result.rows, stamp, reconcile=reconcile)
                    finally:
                        db_seconds += time.monotonic() - db_started
                    active_considered += prior_active
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
                    click.echo(f"{scope} 失败：{error}", err=True)
                    stop = error.category in {"business", "http", "tls", "retry_deferred"}
                    stop |= bool(
                        settings.max_consecutive_failed_slices
                        and consecutive >= settings.max_consecutive_failed_slices
                    )
                except CommitUnknown as error:
                    interrupted = error.interrupted
                    unknown += 1
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
                        "数据库写入失败，停止后续请求；未确认提交的结果不计入成功。", err=True
                    )
                    stop = True
                attempts = getattr(client, "attempts", attempts)
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
            outcomes.append((active_block, "failed: interrupted"))
    finally:
        reporter.stop_progress()
        if not dry_run:
            remaining = len(pending) - success - empty - failed - unknown
            conclusion = (
                "输出失败，已确认提交的数据保留"
                if reporter.io_failed
                else "中断"
                if interrupted
                else "部分失败/提前停止"
                if failed or unknown or remaining
                else "完成，有空响应待核实"
                if empty
                else "完成"
            )

            def pct(value, denominator):
                return f"{value / denominator:.1%}" if denominator else "不适用"

            lines = [
                conclusion,
                f"请求段 {len(pending)}：成功非空 {success}；空 {empty}；失败 {failed}；提交未知 {unknown}；未尝试 {remaining}；跳过 {skipped}",
                f"请求成功比例：{pct(success + empty, len(pending))}；失败比例：{pct(failed, len(pending))}",
                f"已确认写入输入行：{written}",
                *[
                    f"{name}：{value}（{pct(value, written)}）"
                    for name, value in [
                        ("新增", total_counts.inserted),
                        ("源字段更新", total_counts.changed),
                        ("未变", total_counts.unchanged),
                        ("重新激活", total_counts.reactivated),
                    ]
                ],
                f"新标 stale：{total_counts.stale} / 核对前 active {active_considered}（{pct(total_counts.stale, active_considered)}）",
            ]
            sections = [
                (
                    "失败",
                    [
                        detail(api, b, o)
                        for b, o in outcomes
                        if o.startswith("failed") or o == "database_failed"
                    ],
                ),
                ("提交未知", [detail(api, b, o) for b, o in outcomes if o == "commit_unknown"]),
                (
                    "未尝试/未完成",
                    [detail(api, b, "未尝试/未完成") for b, _ in pending[len(outcomes) :]],
                ),
                (
                    "空响应待核实",
                    [detail(api, b, o) for b, o in outcomes if o == "empty_unverified"],
                ),
                ("成功", [detail(api, b, o) for b, o in outcomes if o == "success"]),
            ]
            if failed or unknown or remaining:
                lines.append("失败范围可用 fetch 重新请求；历史核对使用 refresh。")
            try:
                reporter.report(
                    "after",
                    "执行结果",
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
