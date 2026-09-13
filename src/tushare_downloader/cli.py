"""Human-readable commands; persistent preferences live in configuration."""

from dataclasses import replace
from pathlib import Path

import click
import psycopg

from .apis import APIS, get_api
from .config import ConfigError, duration, load_settings
from .download import execute
from .storage import BusyError, StorageError, Store, connect


class Commands(click.Group):
    def get_command(self, ctx, name):
        return super().get_command(
            ctx, {"ls": "list", "f": "fetch", "u": "update", "init": "init-db"}.get(name, name)
        )


@click.group(
    cls=Commands,
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option(package_name="tushare-downloader")
@click.option("-c", "--env-file", type=click.Path(path_type=Path, dir_okay=False))
@click.option("-q", "--quiet", is_flag=True, help="减少常规进度和成功摘要。")
@click.option("-v", "--verbose", count=True, help="显示分段执行详情。")
@click.option("--plain", is_flag=True, help="纯文本输出，不使用动态进度。")
@click.pass_context
def main(ctx, env_file, quiet, verbose, plain):
    """Tushare Pro → PostgreSQL 下载工具。

    fetch/refresh/update 分别用于补齐、核对与更新。固定缩写 f/u/ls/init。
    """
    if quiet and verbose:
        raise click.UsageError("-q 与 -v 不能同时使用。")
    ctx.obj = {"env_file": env_file, "plain": plain, "quiet": quiet, "verbose": verbose}
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


def settings(ctx):
    try:
        return load_settings(ctx.obj["env_file"], plain=ctx.obj["plain"])
    except ConfigError as error:
        raise click.UsageError(str(error)) from None


def guarded(ctx, action):
    try:
        return action()
    except BusyError as error:
        click.echo(str(error), err=True)
        ctx.exit(3)
    except (ConfigError, ValueError) as error:
        raise click.UsageError(str(error)) from None
    except StorageError as error:
        raise click.ClickException(str(error)) from None
    except psycopg.Error as error:
        raise click.ClickException(
            f"数据库操作失败（SQLSTATE={error.sqlstate or 'connection'}）；请检查连接、权限和表结构。"
        ) from None
    except OSError:
        raise click.ClickException("日志/报告或配置文件无法读写；请检查路径和权限。") from None


@main.command("list")
@click.pass_context
def list_apis(ctx):
    """列出接口、分类和核对能力。不连接数据库或 Tushare。"""
    settings(ctx)
    for api in APIS.values():
        kind = "只增型" if api.change_kind == "append-only" else "可变型"
        shape = "时间范围" if api.query_kind == "time-range" else "当前快照"
        click.echo(
            f"{api.name}: {kind} / {shape}; key={','.join(api.unique_key)}; "
            f"stale 核对={'已启用' if api.stale_scope_verified else '待验证'}"
        )


@main.command("init-db")
@click.pass_context
def init_db(ctx):
    """原子初始化受管理表；重复执行时校验结构。"""
    config = settings(ctx)

    def action():
        with connect(config) as conn:
            store = Store(conn)
            with store.writer():
                identity = store.initialize()
            click.echo(f"初始化完成：{conn.info.dbname}；database_id={identity}")

    guarded(ctx, action)


def run(ctx, command, api_name, start=None, end=None, dry_run=False, max_age=None):
    def action():
        api = get_api(api_name)
        config = settings(ctx)
        if max_age is not None:
            config = replace(config, max_age=duration(max_age))
        first, last = start.date() if start else None, end.date() if end else None
        if command != "update":
            if api.query_kind == "time-range" and (first is None or last is None):
                raise ValueError("时间范围接口必须同时指定 --start 和 --end。")
            if api.query_kind == "snapshot" and (first or last):
                raise ValueError("快照接口不接受日期范围。")
            if first and last and first > last:
                raise ValueError("开始日期不能晚于结束日期。")
        with connect(config) as conn:
            store = Store(conn)
            # Dry-run does not acquire the writer lock and issues no data mutations.
            if dry_run:
                code = execute(
                    store,
                    api,
                    command,
                    config,
                    start=first,
                    end=last,
                    dry_run=True,
                    quiet=ctx.obj["quiet"],
                    verbose=ctx.obj["verbose"],
                )
            else:
                with store.writer():
                    code = execute(
                        store,
                        api,
                        command,
                        config,
                        start=first,
                        end=last,
                        quiet=ctx.obj["quiet"],
                        verbose=ctx.obj["verbose"],
                    )
        ctx.exit(code)

    guarded(ctx, action)


def range_options(func):
    func = click.option("--dry-run", is_flag=True, help="只做本地检查和计划。")(func)
    func = click.option("-e", "--end", type=click.DateTime(formats=["%Y-%m-%d"]))(func)
    func = click.option("-s", "--start", type=click.DateTime(formats=["%Y-%m-%d"]))(func)
    return click.argument("api_name", type=click.Choice(list(APIS)))(func)


@main.command("fetch")
@range_options
@click.pass_context
def fetch(ctx, **kwargs):
    """补齐指定范围；有有效成功记录的块跳过。"""
    run(ctx, "fetch", **kwargs)


@main.command("refresh")
@range_options
@click.option("--max-age", help="核对最大年龄，例如 24h；0 强制。")
@click.pass_context
def refresh(ctx, **kwargs):
    """重新核对指定范围，更新源字段并按接口能力标 stale。"""
    run(ctx, "refresh", **kwargs)


@main.command("update")
@click.argument("api_name", type=click.Choice(list(APIS)))
@click.option("--dry-run", is_flag=True)
@click.pass_context
def update(ctx, **kwargs):
    """只增型按本地最新日期回看；可变型核对当前全集。"""
    run(ctx, "update", **kwargs)


@main.command("clean")
@click.argument("api_name", type=click.Choice(list(APIS)))
@click.option("--apply", is_flag=True, help="实际清空，需要两项数据库身份确认。")
@click.option("--confirm-database")
@click.option("--confirm-database-id", type=click.UUID)
@click.pass_context
def clean(ctx, api_name, apply, confirm_database, confirm_database_id):
    """默认预览清理范围；不级联删除下游数据。"""
    config = settings(ctx)

    def action():
        with connect(config) as conn:
            store = Store(conn)
            with store.writer():
                result = store.clean(
                    get_api(api_name),
                    apply=apply,
                    database=confirm_database,
                    database_id=confirm_database_id,
                )
            click.echo("清理完成" if apply else "清理预览（未删除）")
            for key, value in result.items():
                click.echo(f"{key}: {value}")

    guarded(ctx, action)
