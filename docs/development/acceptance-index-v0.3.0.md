# v0.3.0 验收证据索引（本地完成，远端待验）

设计提交：`ea630b65c4c99261f3fcf331f3ee2cb800f10d86`。运行代码基线：`d46b49d`（plain 帮助修复）；3377dcd 与该提交的 src/tests/pyproject/uv.lock 无差异。后续提交仅含文档、证据和 Git 终端文件属性。

2026-09-15：完整本地回归 233 passed，运行环境 WSL Python 3.12.3 → Windows PostgreSQL 18 独立临时实例。完整日志暂存本机 /tmp/v03-final-regression.txt。

本索引逐项对应标准：69 项本地签核完成，H04/K01/K02/K04 仍未完成。运行时修复后完整回归 233 passed；其他补充证据按下文明确范围复用。没有将本地通过解释为远端发布完成。测试文件位于 tests/unit 或 tests/integration，基准/审计记录位于本目录。

## 逐项核对

| 编号 | 要求 | 当前证据 | 状态 |
| --- | --- | --- | --- |
| A01 | Python 3.12、WSL/Linux 环境可按 uv.lock 安装；构建 wheel 后在隔离环境执行 help/version/list，无 Token、无 DB 也能工作 | test_config.py、test_cli_scaffold.py；check_distribution.py；独立库 fixture | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| A02 | Ruff 检查/格式、现有单元与独立 PostgreSQL 18 集成套件通过；coverage 用于找遗漏，不虚设比例门槛 | test_config.py、test_cli_scaffold.py；check_distribution.py；独立库 fixture | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| A03 | 显式 CLI、环境、指定 dotenv、默认值优先级正确；默认只找 cwd/.env，无父目录搜索/插值；显式文件缺失和非法值明确报错 | test_config.py、test_cli_scaffold.py；check_distribution.py；独立库 fixture | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| A04 | .env.example 按设计分组，默认值/单位/允许值与实现一致；整理本地文件保留现值、未知键和重复键的现有有效含义 | test_config.py、test_cli_scaffold.py；check_distribution.py；独立库 fixture | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| A05 | .gitignore 保持原匹配语义并忽略默认日历缓存；保留 .env.example、uv.lock、设计/demo；不批量取消已有跟踪 | test_config.py、test_cli_scaffold.py；check_distribution.py；独立库 fixture | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| A06 | TEST_DATABASE_URL/BENCH_DATABASE_URL 从独立环境读取；缺失/不合规时明确失败，绝不访问正式库作为替代 | test_config.py、test_cli_scaffold.py；check_distribution.py；独立库 fixture | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| B01 | daily_basic fetch/refresh 必须有成对含端点的日期；不接受未来日；stock_basic 拒绝日期；update 拒绝日期与 max-age | test_planning.py、test_cli.py、test_acceptance_matrix.py、test_daily_expansion.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| B02 | fetch 按有效成功记录跳过；有行但无记录、旧 spec、失败、不一致、范围扩大均重查；空结果按复查间隔 | test_planning.py、test_cli.py、test_acceptance_matrix.py、test_daily_expansion.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| B03 | refresh 使用 last_reconciled_at；非空 age 等于 max-age 可跳过，超过则请求；未核对则请求；max-age=0 强制，仍受交易日过滤 | test_planning.py、test_cli.py、test_acceptance_matrix.py、test_daily_expansion.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| B04 | 空记录在 EMPTY_RECHECK_AGE 到期后再查；refresh --max-age 0 优先强制；不误用行 _updated_at 判新鲜 | test_planning.py、test_cli.py、test_acceptance_matrix.py、test_daily_expansion.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| B05 | daily_basic update 从最新 active 日回看至上海昨日，窗口内不按新鲜度跳过；最新日超过昨日先裁剪再回看；空库提示先 fetch | test_planning.py、test_cli.py、test_acceptance_matrix.py、test_daily_expansion.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| B06 | stock_basic update 无需本地数据，每次取得完整快照；不使用日期或 lookback；fetch 不核对缺失键，refresh/update 按规则核对 | test_planning.py、test_cli.py、test_acceptance_matrix.py、test_daily_expansion.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| B07 | 稳定发布前取得的当天暂定数据在后续调用中可被重查；失败重发普通命令即可，不依赖日志或持久任务 | test_planning.py、test_cli.py、test_acceptance_matrix.py、test_daily_expansion.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| C01 | 固定原点、向下取整、端点、跨块、负地址、范围裁剪和去重排序正确；记录实际边界，扩展范围/spec 变化不能误跳过 | test_calendar.py；benchmark-v0.3.0-calendar；五日频接口声明 | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| C02 | 默认 basic 对适用 API 过滤周末，工作日请求；无外部日历访问；stock_basic 不参与过滤 | test_calendar.py；benchmark-v0.3.0-calendar；五日频接口声明 | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| C03 | calendar 以明确记录的来源/规则判定；有效 open 即使在周末也请求，closed 即使工作日也过滤 | test_calendar.py；benchmark-v0.3.0-calendar；五日频接口声明 | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| C04 | 有效缓存命中不刷新；缺失/过期按原 calendar 策略刷新；每年份一轮有限重试；候选日期齐全，快照在本次执行中固定 | test_calendar.py；benchmark-v0.3.0-calendar；五日频接口声明 | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| C05 | 权限/网络重试耗尽、无效日历、候选日期缺失、缓存故障使 calendar 无法执行时，退出 1、数据请求为 0，说明用户可选行动；非法配置退出 2 | test_calendar.py；benchmark-v0.3.0-calendar；五日频接口声明 | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| C06 | --ignore-calendar 绕过周末及日历并不读缓存；仍保留 fetch/refresh 的本地判断；refresh --max-age 0 --ignore-calendar 请求所有选定日期 | test_calendar.py；benchmark-v0.3.0-calendar；五日频接口声明 | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| C07 | 无候选块/不适用/basic/off/绕过均不请求日历；过滤不写成功检查记录、不删行、不标 stale | test_calendar.py；benchmark-v0.3.0-calendar；五日频接口声明 | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| C08 | dry-run 无远端或缓存写操作；calendar 缓存不足标 Plan incomplete 并退出 1；basic/off 或有效缓存可给出完整计划 | test_calendar.py；benchmark-v0.3.0-calendar；五日频接口声明 | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| D01 | HTTPS 不降级；HTTP 状态和业务码分别处理；HTTP 200+错误业务码不入库，即使错误附带数据；成功且行数触顶不自行判错/递归拆块 | test_client.py、test_client_metrics.py、test_daily_apis.py、test_snapshot.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| D02 | 网络、429/5xx 按规则有限重试；4 次含首次，所有尝试限速；超预算 Retry-After 不提前请求；权限/参数/未知协议错误不盲重试 | test_client.py、test_client_metrics.py、test_daily_apis.py、test_snapshot.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| D03 | 字段按名称映射；字段重排可接受，缺失/重复字段、行宽、类型、范围错误失败；前导零、Decimal、SQL NULL 正确 | test_client.py、test_client_metrics.py、test_daily_apis.py、test_snapshot.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| D04 | 同键同值去重且计数，同键异值整块失败；快照跨状态冲突同样失败；响应/缓冲预算超限无半块写入 | test_client.py、test_client_metrics.py、test_daily_apis.py、test_snapshot.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| E01 | raw 数据与 meta.slices 同事务；插入、NULL 覆盖、未变、重新激活和时间字段正确；同值仍更新观察时间 | test_storage.py、test_daily_expansion.py、test_real_faults.py、test_snapshot.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| E02 | daily_basic 独立块失败不影响已提交块；全局错误/连续失败阈值停止；阈值 0 禁用；剩余块明确未尝试 | test_storage.py、test_daily_expansion.py、test_real_faults.py、test_snapshot.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| E03 | stock_basic L/D/P/G/UN 是一个逻辑块；任一必要请求失败/冲突时不合并，后续子请求未尝试；已收到行不能算已提交 | test_storage.py、test_daily_expansion.py、test_real_faults.py、test_snapshot.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| E04 | 单个状态为空但全集非空允许提交；全集为空保留旧行且不刷新完整核对时间；失败/未完分页不能触发 stale | test_storage.py、test_daily_expansion.py、test_real_faults.py、test_snapshot.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| E05 | 只有 refresh/可变 update 的允许范围核对缺失键；fetch、所有只增型接口 update 不标 missing stale；范围外不受影响，重新出现恢复原键 | test_storage.py、test_daily_expansion.py、test_real_faults.py、test_snapshot.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| E06 | COMMIT 确认丢失停止并标 unknown，不断言回滚、不盲重放；新调用从数据库事实重新判断 | test_storage.py、test_daily_expansion.py、test_real_faults.py、test_snapshot.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| E07 | Ctrl+C 保留已提交结果、清理未提交事务，尽力报告，退出 130；HTTP 期间无长数据事务；同库第二写实例退出 3 | test_storage.py、test_daily_expansion.py、test_real_faults.py、test_snapshot.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| E08 | init-db 幂等、校验身份/schema/唯一键；不接管外部同名对象，不自动破坏性迁移；clean 默认预览，名称/UUID 双确认且原子删除，外键阻止时无级联 | test_storage.py、test_daily_expansion.py、test_real_faults.py、test_snapshot.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| E09 | 备份恢复到独立库后，raw/meta、唯一键、stale、身份和读权限符合文档；已有 v0.1.0 数据可用，配置缺项采用新默认值 | test_storage.py、test_daily_expansion.py、test_real_faults.py、test_snapshot.py | 通过：restore-v0.3.0.json、test_daily_expansion.py；v0.1 兼容证据按下文限定复用。 |
| F01 | 成功规划 T=K+W+H+P；执行 P=S+E+F+U+Q；准备失败计划未确定，不伪造 P=0 的成功计划 | test_reporting.py、test_progress_layout.py、test_output_modes.py、test_output_faults.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| F02 | R=Inserted+Updated+Unchanged+Reactivated，四类互斥；stale 单列且分母为实际可靠核对范围的 prior active；unknown 不混入确认写入 | test_reporting.py、test_progress_layout.py、test_output_modes.py、test_output_faults.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| F03 | 成功率含成功空响应，以 P 为分母；跳过/过滤不是成功；零分母不显示 100%；逻辑块与 HTTP 尝试/快照子请求分开 | test_reporting.py、test_progress_layout.py、test_output_modes.py、test_output_faults.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| F04 | 数据请求之前 report.md 已原子写入原计划且 Final result: not recorded；结束原子替换同一路径，保留初始事实，结果在前、异常在计划之前 | test_reporting.py、test_progress_layout.py、test_output_modes.py、test_output_faults.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| F05 | 报告临时写/替换失败不损坏旧文件、不撤销已提交数据；硬终止后不冒充完成；不存在文件时不打印假路径 | test_reporting.py、test_progress_layout.py、test_output_modes.py、test_output_faults.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| F06 | 新执行仅生成单文件报告，旧 before/after 不自动迁移；逐块明细不受终端上限裁剪，长范围流式输出；Markdown 管道/换行安全转义 | test_reporting.py、test_progress_layout.py、test_output_modes.py、test_output_faults.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| F07 | 零计划隐藏无关全零表；快照不显示回看日期；日频显示实际窗口；子请求表记录 received，原子提交行数仅属完整快照 | test_reporting.py、test_progress_layout.py、test_output_modes.py、test_output_faults.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| G01 | 日志文件创建并写启动事件后立即显示路径，早于 DB 检查/日历/数据请求；quiet/plain 也显示；帮助不创建伪运行文件 | test_reporting.py、test_progress_layout.py、test_output_modes.py、test_output_faults.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| G02 | 六种 Rich/plain × quiet/normal/verbose 组合不改变请求、数据、退出码和完整报告语义；quiet 保留警告错误/结果/路径和主动查询主体 | test_reporting.py、test_progress_layout.py、test_output_modes.py、test_output_faults.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| G03 | 最近日志默认 5 条、可配 0..20，队列有界，完整文件不因滚动丢事件；WARN/ERROR 重绘不重复追加；Live 结束清理 | test_reporting.py、test_progress_layout.py、test_output_modes.py、test_output_faults.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| G04 | PROGRESS=off 与 TERMINAL_LOG_LINES=0 各自控制对应区域；plain 无回滚日志区，normal 按配置周期追加、verbose 扩展事件，quiet 无周期进度 | test_reporting.py、test_progress_layout.py、test_output_modes.py、test_output_faults.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| G05 | Rich 可用时默认启用；任一流重定向、TERM=dumb、NO_COLOR 或显式 plain 时无 ANSI/OSC/回车动画；路径完整可复制 | test_reporting.py、test_progress_layout.py、test_output_modes.py、test_output_faults.py | 本地通过：18 组静态 PTY、四种动态尺寸与六模式测试；已查看窄屏/低高度代表图。 |
| G06 | ETA 最近20块、至少5样本且累计10秒；重试/提交/异常长块不虚假倒计时；零计划无 Live，日历准备无数据 ETA；刷新不超4Hz | test_reporting.py、test_progress_layout.py、test_output_modes.py、test_output_faults.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| G07 | 日志 JSONL 可逐行解析，轮转分片保留所有事件，报告列出实际分片；密钥不泄露，关键事件不会被终端 quiet 屏蔽 | test_reporting.py、test_progress_layout.py、test_output_modes.py、test_output_faults.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| G08 | 日志写入故障停止后续数据请求、非零退出，已提交数据保留；报告写失败另报；终端/日志不是数据库账本 | test_reporting.py、test_progress_layout.py、test_output_modes.py、test_output_faults.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| G09 | 英文程序文案、状态文字与颜色配对；外部中文/markup/控制字符不破坏 UI；verbose 内部异常不输出 locals/凭据 | test_reporting.py、test_progress_layout.py、test_output_modes.py、test_output_faults.py | 本地通过：恶意文本测试和动态 PTY 原文/控制序列检查；代表图已查看。 |
| H01 | 主/子帮助无凭据、DB、网络可用；重要日期/快照限制靠前，Examples 有效，全局选项位置正确；错误只给相关 Usage/原因/入口 | test_cli_scaffold.py；language-audit-v0.3.0.md；严格构建与 check_cli_demo.py | 通过：CLI 自动检查与 terminal-v0.3.0 中 18 组实际 PTY 帮助/列表，已查看窄宽代表图；plain eager 问题已修复。 |
| H02 | README/guide/reference/operations 面向用户、英文，与发布实现一致；内部提醒移至 development；中文设计保留 | test_cli_scaffold.py；language-audit-v0.3.0.md；严格构建与 check_cli_demo.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| H03 | 设计一套完整正文，版本和来源可追溯；静态示例计数正确；旧 demo 若未同步须标明版本与差异 | test_cli_scaffold.py；language-audit-v0.3.0.md；严格构建与 check_cli_demo.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| H04 | Zensical 严格构建通过，主要页面/资源存在，导航及相对链接正确；HTML demo 独立打开、嵌入与静态后备可用 | test_cli_scaffold.py；language-audit-v0.3.0.md；严格构建与 check_cli_demo.py | 未完成：严格构建/iframe 解析通过，浏览器连接不可用，尚无当前渲染证据。 |
| I01 | 假 API/解析、真实独立 PG 写入、少量真实 API 分开测；首次补取、全跳过、失败补取、过期/强制刷新、两类 update、空、重复、长报告均覆盖 | benchmark-v0.3.0.json；benchmark-v0.3.0-calendar/output/api；CPU 本地产物 | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| I02 | off/basic/冷缓存 calendar/热缓存 calendar/显式绕过对照；请求集合正确，绕过与 off 等价；准备失败单测停止不计作加速 | benchmark-v0.3.0.json；benchmark-v0.3.0-calendar/output/api；CPU 本地产物 | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| I03 | 每个固定场景至少5轮，保留原始结果，中位数及波动；包含准备/限速/重试/解析/DB/报告开销、响应字节及峰值内存 | benchmark-v0.3.0.json；benchmark-v0.3.0-calendar/output/api；CPU 本地产物 | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| I04 | Rich/plain、进度关闭、DEBUG 和长报告开销有对照；同值观察更新不称零写入，跳过不算下载吞吐 | benchmark-v0.3.0.json；benchmark-v0.3.0-calendar/output/api；CPU 本地产物 | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| J01 | 独立库的小范围 daily_basic 请求与完整 stock_basic 状态组合成功，字段/类型/唯一键及报告一致；业务语义不以人工猜测行数验收 | acceptance-v0.3.0.md 六接口真实冒烟；WSL 到 Windows PostgreSQL 临时库 | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| J02 | trade_cal 真实小范围/缓存准备验证来源参数、字段及选择策略；basic/bypass 不依赖其权限；故障分类由受控夹具补齐 | acceptance-v0.3.0.md 六接口真实冒烟；WSL 到 Windows PostgreSQL 临时库 | 通过：calendar-live-v0.3.0.json 记录真实 SSE 日历冷/热缓存与绕过；受控故障测试补齐异常分支。 |
| J03 | WSL/Linux Python 连接 Windows PostgreSQL 的支持路径验证；独立测试角色与正式数据隔离 | acceptance-v0.3.0.md 六接口真实冒烟；WSL 到 Windows PostgreSQL 临时库 | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| K01 | 候选提交的检查/集成/docs-build 成功，必需检查设置符合设计；PR 只构建，不获得正式部署权限 | 待远端发布检查；check_distribution.py；check_site_notices.py | 未完成：PR 尚未创建，无远端候选 CI 证据。 |
| K02 | main 发布同一构建产物，过期 SHA 不部署；站点项目子路径、搜索、页面和 demo 可访问；失败构建不发布，revert 回退流程有有效证据 | 待远端发布检查；check_distribution.py；check_site_notices.py | 未完成：本版尚未部署 main，缺少 Pages/搜索/资源验证。 |
| K03 | 落实已选 MIT，核对依赖授权/项目代码/数据权利边界，LICENSE、README、元数据及分发内容一致 | 待远端发布检查；check_distribution.py；check_site_notices.py | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| K04 | 发布记录关联设计版本/commit、软件 commit、证据和剩余限制；设计与软件标签独立，不改写已有标签 | 待远端发布检查；check_distribution.py；check_site_notices.py | 未完成：最终软件提交和发布记录尚未确定。 |
| L01 | 语言范围表落地；公开教程/配置/程序文案一致，原始数据与中文设计例外不被误改 | test_daily_apis.py、test_daily_expansion.py、test_output_modes.py；真实冒烟与 benchmark-v0.3.0.md | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| L02 | 四个新增 API 的字段、类型、键、请求参数、权限限制及 stale 能力均已明确；数据集章未决项全部解决 | test_daily_apis.py、test_daily_expansion.py、test_output_modes.py；真实冒烟与 benchmark-v0.3.0.md | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| L03 | 四个新接口可独立 fetch/refresh/update；list/reference 列全六个接口，帮助和报告准确呈现；同范围重复下载、强制修正、回看、过滤与显式绕过符合规范 | test_daily_apis.py、test_daily_expansion.py、test_output_modes.py；真实冒烟与 benchmark-v0.3.0.md | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| L04 | 键冲突、完全重复、乱序字段、NULL、非法类型、空响应、显式 API 错误、限速重试和中段失败均可判定；到上限但无错误不自行报错 | test_daily_apis.py、test_daily_expansion.py、test_output_modes.py；真实冒烟与 benchmark-v0.3.0.md | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| L05 | suspend_d 同日同键同值去重、异值抛 duplicate_conflict 且整日不写；跨请求修正正常 upsert；空结果准确计数与解释 | test_daily_apis.py、test_daily_expansion.py、test_output_modes.py；真实冒烟与 benchmark-v0.3.0.md | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| L06 | 已有 v0.2.0 数据库可无损增加新表；重复初始化、冲突结构和事务失败行为明确 | test_daily_apis.py、test_daily_expansion.py、test_output_modes.py；真实冒烟与 benchmark-v0.3.0.md | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| L07 | 代表性 A 股日频数据准备流程完成，报告能定位每 API 的成功、空与失败；权限不足记录未执行 | test_daily_apis.py、test_daily_expansion.py、test_output_modes.py；真实冒烟与 benchmark-v0.3.0.md | 通过：当前自动回归与所列本地实证；复用范围见下文。 |
| L08 | 扩展共用规划、执行、存储和呈现，无复制整套 pipeline 或新增任务系统；性能比较使用相同输入与环境 | test_daily_apis.py、test_daily_expansion.py、test_output_modes.py；真实冒烟与 benchmark-v0.3.0.md | 通过：当前自动回归与所列本地实证；复用范围见下文。 |

## 复用边界

相对 v0.2.0，storage.py、配置模板、忽略规则、Demo 资产和 CI/CD 工作流未变；这只说明需要检查的变更范围，不能将旧版所有证据直接签成新版通过。元数据版本不变，增表路径已由当前集成测试验证。供应方材料与依赖版本未变，已运行 check_site_notices.py；软件包版本变更后已重新构建并隔离安装。

完整阶段记录见 [验收记录](acceptance-v0.3.0.md)；语言逐页审计见 [语言审计](language-audit-v0.3.0.md)；性能数据见 [基准](benchmark-v0.3.0.md)。


## 本地最终审计与证据复用

- A01/A02：d46b49d 后重新构建 wheel/sdist 并执行 check_distribution.py；隔离环境 help/version/list 成功且含六接口。完整单元与 PostgreSQL 集成合并回归 233 passed，无 skip/xfail；后续 src/tests/pyproject/uv.lock 无差异。当前 Ruff check/format 和严格构建再次通过。
- A04/A05：.env.example、.gitignore 及配置加载器未改动；本轮没有改写本地 .env。既有配置边界测试仍通过。新增 .gitattributes 只保护终端 .ansi 原始字节，不改变忽略规则。
- E09：当前六表及 meta 的恢复和读权限有独立实证。v0.1→v0.2 的 upgrade-v0.2.0.json 证明旧 schema、身份和默认配置兼容；v0.2→当前 storage.py、meta schema 版本和原有两个 ApiSpec 字段/键/spec_version 未改变（仅新增日历声明），当前增表及数据保持集成测试补齐第二段。这是特定兼容路径的复用，不是复用旧版全部验收结论。
- G/H：真实 PTY 18 组静态及四种动态尺寸已检查；计时使用合成块时钟的动态渲染不用于性能结论。重试 ETA 由现有时钟边界测试及 PTY 验证。H04 的源码/构建/静态 iframe 检查通过，当前浏览器渲染仍缺失，整条保持未完成。
- I01–I04：本版 cpu、database、api、calendar、output 五组分层样本及五接口 flow 全部保留；固定场景至少五次，不把假网络速度当实际下载速度。独立数据库模式于 3377dcd 执行，补齐纯写入分层；CPU 测量后仅 benchmark 提示和测试扩展，不改变其被测解析/规划路径。
- J01–J03：六接口真实短样本、当前真实 trade_cal 冷/热缓存与 bypass，以及 WSL→Windows PG 18 恢复/集成验证均有本版记录。该证据只覆盖实际请求范围和环境。
- K03：依赖版本及第三方材料相对 v0.2.0 未改变；当前 wheel/sdist 许可证隔离检查和 11 项供应方字节核对通过；代码 MIT 不授予数据再分发权的声明保留。
- L01–L08：语言审计、四 API 契约、真实解析/执行/DB 冲突边界、12 组新增命令组合、五日频六显示模式对照、六接口真实请求和 300 次 flow 样本已核对。无后台任务、插件框架或新增恢复协议。

## 外部阻塞

当前 GitHub 集成创建 PR 返回 403 Resource not accessible by integration；浏览器桥接持续 nodeRepl.fetch request failed。远端检索无该分支 PR，main 仍为 87717741fd47fa307e2b502eaebd434c32c6ac09。
待恢复浏览器连接或由维护者创建 PR 后，检查候选 CI、当前页面渲染、main 部署、在线搜索/资源，再更新 K04 发布记录。此前不合并、不打软件标签、不声明 v0.3.0 已通过完整验收。
