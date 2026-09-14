# 总体设计与验收

**设计版本：v0.2.0-draft.5**

## 目标与范围

本版改善日常使用和维护体验，减少可以可靠识别的休市日请求。保留单 shell 前台运行方式。
不增加任务管理、status、resume、后台服务、通用插件框架或额外机器输出模式。
本轮只编写设计；以下清单都是后续实现要求。

| 工作项 | 本版交付 |
| --- | --- |
| 配置与忽略规则 | 注释分组、稳定排序、示例与实现一致 |
| 文档 | 按读者分层，用户文档不夹带维护提醒 |
| CLI | 英文提示、帮助和报告；窄屏、plain、非交互布局 |
| 日历过滤 | 默认 basic 周末过滤；可选 calendar，失败不自动降级，用户可主动绕过 |
| License | 维护者选定后同步授权文件与项目元数据 |

`daily_basic` 仍是通常只增、允许历史修正的只增型数据；`stock_basic` 仍是可变快照。
fetch 根据成功请求记录跳过；refresh 根据新鲜度决定重拉，`--max-age 0` 强制重拉；
只增型 update 覆盖回看窗口至截止日期，可变型 update 获取整个快照再更新、插入和标记 stale。
分块提交、部分失败保留已提交结果、API 错误分类重试和退出码保持不变。
API 未报错且响应解析成功，按现有成功规则处理，不根据达到行数上限自行推断失败。
日历过滤和显式绕过规则唯一来源是[请求规划](request-planning.md)。

## 配置与代码边界

继续使用 dotenv，不新增配置框架。`.env.example` 依次分组为凭据、数据库、请求与重试、刷新策略、日历、日志报告、终端、测试与 benchmark。
注释用英文，注明必填性、默认值、单位和取值约束；真实 `.env` 整理只改变注释和顺序，保留全部现值及未知自定义键。
不输出凭据内容，不把本地配置提交到 Git。
测试与 benchmark 连接继续独立，绝不回落正式数据库。

`.gitignore` 按 Python/构建、虚拟环境、工具缓存、测试覆盖率、凭据、日志报告、文档、benchmark 分组。
整理不改变原匹配规则；新增日历缓存路径单独说明，并保留 `.env.example` 例外。
配置优先级、相对路径基于 cwd 的规则不变。

| 新配置 | 默认值 | 规则 |
| --- | --- | --- |
| TERMINAL_LOG_LINES | 5 | 0..20；Rich 最近日志条数，具体规则见 [CLI 体验](cli-experience.md) |
| CALENDAR_FILTER | basic | basic/calendar/off；仅适用接口生效，支持 --ignore-calendar 主动绕过 |
| CALENDAR_CACHE_DIR | .cache/tushare-downloader/calendar | 相对 cwd；可删除的非业务缓存 |
| CALENDAR_MAX_AGE | 24h | 正时长；超过期限的缓存不能用于过滤 |

只新增小型 `calendar.py`，负责日历读取、校验、缓存与日期分类；复用现有 HTTP 客户端的限速和重试。
planning 保持纯规划，接收已取得的日期分类；download 协调准备和执行；reporting/cli 负责呈现。
缓存使用原子替换的 JSON 文件，不建任务表，不引入数据库迁移或外部缓存服务。
业务 raw 表、meta 成功请求记录、唯一键和 stale 规则不因本版变化。

完整报告改用单个 `report.md`，保留原计划并在结束时原子写入结果；具体生命周期及帮助 Examples 见 [帮助页与完整报告](help-and-reports.md)。

## 配置及文档整理方案

实际配置文件暂不修改。dotenv 按 Credentials、Database、Requests & retries、Refresh & update、Trading-day filter、Logs & reports、Terminal output、Development only 分组。英文注释标注默认值、单位及必要约束，不逐行重复键名。新项以代码默认值兼容旧配置；不覆盖已有值。

.gitignore 按 Credentials & local configuration、Python & environments、Build artifacts、Tests & coverage、Tool caches、Runtime output、Documentation、Benchmarks 分组；保留现有匹配语义和 .env.example 例外，只新增明确的日历缓存路径。

沿用 guide/reference/operations/development/design 目录。README 主入口按快速开始、配置、下载、参考排列；设计、验收与部署维护链接归入贡献者入口。无需新增目录层级或配置框架。

## 文档与部署

| 读者 | 入口及内容 | 不应出现的内容 |
| --- | --- | --- |
| 使用者 | README、guide、reference：安装、命令、配置、限制、故障处理 | 内部提醒、未完成验收清单 |
| 运维人员 | operations：初始化、权限、备份恢复、维护清理 | 实现过程流水账 |
| 贡献者 | development：环境、测试、benchmark、贡献流程、backlog | 冒充已交付功能的计划 |
| 设计评审者 | design：规范、理由、边界、待决项 | 运行状态的唯一记录 |

本版拟将面向使用者及运维的文档统一为英文，与 CLI 术语一致；设计文档保持中文。
历史验收与设计记录保持原语言和内容，贡献者文档不强制全量翻译。
维护提醒迁入 development，必要的用户限制保留。既有 URL 保留，移动页面保留导航页或重定向。
每条规则只有一处详细定义，其他页面链接引用；帮助例子和 reference 以实际命令验证。

继续使用 Zensical 和 GitHub Pages。PR 只构建；main 构建通过后部署同一产物；`docs-build` 保持必需检查。
新增设计页面加入导航和 CI 页面存在性检查。文档改动不触发生产数据访问。
Excel Power Query 只作为使用示例，不作为版本验收门槛。

## 许可证决策

本草案不选择或授予许可证。实现前整理直接与随分发产物携带的依赖授权清单，列出维护者希望允许的商用、修改、分发及衍生项目条件，再比较候选文本。
由维护者确定最终许可证后，添加 LICENSE、版权声明，并同步 README 和 pyproject 元数据。
代码授权与 Tushare 数据/接口使用权分开说明。未作出选择时，此项保持未完成，不能宣称已发布开源授权。

## 实施顺序与验收

1. 配置及文档整理，保留行为；完成 License 决策材料。
2. 英文提示、帮助和输出布局，验证原命令行为兼容。
3. 日历能力和适用性探测；完成主动绕过、失败诊断、统计与 benchmark。
4. 完整回归、文档构建与部署验证；记录验收证据，再决定软件发布。

- [ ] 原单元/独立 PostgreSQL 集成测试、格式检查、打包检查通过；不新增 Windows 原生 Python 门槛。
- [ ] 配置默认值与优先级不变；忽略规则用代表路径前后比对，新增缓存规则有说明；凭据未泄露。
- [ ] 英文帮助和报告覆盖全部命令及故障路径，布局检查见 CLI 文档。
- [ ] 日历单元、集成和请求数对照通过；basic 无外部依赖；calendar 无静默降级；主动绕过保留原本地记录判断。验证规则适用性和来源假设，不要求证明所有市场日历永久完整。
- [ ] License 已由维护者确认并完成一致性检查，或在发布前明确延期并调整范围。
- [ ] 新旧文档链接、严格构建、Pages 部署通过；旧设计四篇内容哈希不变。

采用等价类和边界值构造有代表性的用例，不声称有限用例证明所有输入正确。
只对有行为风险的逻辑增加测试；注释整理不建立逐行镜像测试。
软件目标采用 0.2.0，反映新增过滤行为和英文输出变化；0.1.x 留给兼容修复。
JSONL 既有键和事件语义保持稳定，新增字段向后兼容；调用方不应解析人类报告措辞。
