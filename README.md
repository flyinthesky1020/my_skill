# my_skill

我的 Kimi Code / Claude Code 等 agent 工具的 skill 备份仓库。目录结构与本地 `~` 下的路径一一对应，方便直接还原：

| 仓库内路径 | 本地路径 |
| --- | --- |
| `.agents/skills/` | `~/.agents/skills/` |
| `.kimi-code/skills/` | `~/.kimi-code/skills/` |

## Skill 清单（共 37 个）

最新修改时间取自本地文件的最后修改时间。

### 自制（6 个）

| Skill | 介绍 | 最新修改时间 |
| --- | --- | --- |
| ai-game-dev | AI 辅助 3D 小游戏生产线：ChatGPT 出概念图、Tripo3D 图生 3D、Blender 后处理、Godot 4 集成与玩法工程 | 2026-09-16 |
| feishu-doc-writing | 按个人风格写飞书云工作文档：测试记录、评测 bench、方案、复盘、周报、调研记录、协作台账 | 2026-09-17 |
| prd-writing | 问答式信息采集后撰写符合个人风格的产品 PRD（飞书文档），含竞品调研对比取证 | 2026-09-02 |
| social-buzz-research | 社媒爆款与叙事风向调研（X/Twitter、B站、YouTube），热度筛选 + 截图取证 + 飞书沉淀 | 2026-09-23 |
| volc-bi-extraction | 从火山引擎增长分析（DataFinder）和火山智能数据洞察后台批量取数、转化率复盘 | 2026-10-12 |
| run-e2e-benchmark | 通过 E2E HTTP/API 接口或 Harbor 风格 runner 批量跑 Office benchmark 任务，含隔离、trace、token 统计 | 2026-09-07 |

### lark-cli 配套 · 飞书全家桶（28 个）

| Skill | 介绍 | 最新修改时间 |
| --- | --- | --- |
| lark-approval | 飞书审批：查询/处理审批待办已办，搜索审批定义并发起原生审批实例 | 2026-08-20 |
| lark-apps | 妙搭（Spark/Miaoda）应用开发与托管：创建、本地/云端开发、UI 设计、日志监控、协作者管理 | 2026-08-20 |
| lark-attendance | 飞书考勤打卡：查询自己的打卡记录 | 2026-08-20 |
| lark-base | 飞书多维表格（Base）：建表、字段、记录、视图、公式、仪表盘、BaseApp、权限 | 2026-08-20 |
| lark-calendar | 飞书日历：日程管理、参会人、忙闲查询、会议室预定 | 2026-08-20 |
| lark-contact | 飞书通讯录：姓名/邮箱 ↔ open_id 解析，查部门、状态、签名，搜索机器人 | 2026-08-20 |
| lark-doc | 飞书云文档（Docx/Wiki）：读取、创建、编辑，图片附件，思维笔记 | 2026-08-20 |
| lark-drive | 飞书云空间：文件/文件夹管理、上传下载、权限、评论、版本、本地文件导入 | 2026-08-20 |
| lark-event | 飞书实时事件订阅：以 NDJSON 流式消费 IM、审批、任务、会议等事件 | 2026-08-20 |
| lark-im | 飞书即时通讯：收发消息、群聊管理、文件图片、表情回复、加急、交互卡片 | 2026-08-20 |
| lark-mail | 飞书邮箱：起草/发送/回复/转发邮件，搜索、文件夹、标签、收信规则 | 2026-08-20 |
| lark-markdown | 飞书 Markdown 文件的查看、创建、上传、编辑和比较 | 2026-08-20 |
| lark-minutes | 飞书妙记：搜索、下载/上传音视频、读取编辑纪要产物、本地音视频转纪要 | 2026-08-20 |
| lark-note | 飞书会议纪要（Note）直查：纪要详情、关联文档、原始逐字记录 | 2026-08-20 |
| lark-okr | 飞书 OKR：周期、目标、关键结果、对齐关系、进展记录 | 2026-08-20 |
| lark-openapi-explorer | 飞书原生 OpenAPI 探索：挖掘未被 CLI 封装的原生接口 | 2026-08-20 |
| lark-shared | lark-cli 安装与认证：登录/登出、身份、权限域、scope 缺失处理 | 2026-08-20 |
| lark-sheets | 飞书电子表格：建表、工作表结构、单元格读写、图表、透视表、财务建模 | 2026-08-20 |
| lark-skill-maker | 创建 lark-cli 的自定义 Skill：包装原子 API 或编排多步流程 | 2026-08-20 |
| lark-slides | 飞书幻灯片：创建演示文稿、读取/管理页面、局部替换 | 2026-08-20 |
| lark-task | 飞书任务：待办、清单、子任务、协作成员、附件、任务智能体 | 2026-08-20 |
| lark-topic-vote-workflow | 飞书群「话题征集 → 催交 → 投票 → 结果记录 → 发布」固定工作流配置与运营 | 2026-07-01 |
| lark-vc | 飞书视频会议：查询进行中会议、会中实时内容、历史会议与纪要搜索 | 2026-08-20 |
| lark-vc-agent | 飞书视频会议会中能力：机器人真实入会/离会、会中消息与表情 | 2026-08-20 |
| lark-whiteboard | 飞书画板：查询/编辑画板，导出预览图片与原始节点结构 | 2026-08-20 |
| lark-wiki | 飞书知识库：知识空间、成员、文档节点层级管理 | 2026-08-20 |
| lark-workflow-meeting-summary | 会议纪要整理工作流：汇总指定时间范围的会议纪要并生成结构化报告 | 2026-08-20 |
| lark-workflow-standup-report | 日程待办摘要：生成指定日期的日程与未完成任务摘要 | 2026-08-20 |

### 第三方 GitHub（2 个）

| Skill | 来源 | 介绍 | 最新修改时间 |
| --- | --- | --- | --- |
| joinquant-skill | [gaaiyun/joinquant-skill](https://github.com/gaaiyun/joinquant-skill) | 生成聚宽（JoinQuant）平台可运行的股票/ETF/期货量化回测与实盘策略代码 | 2026-08-01 |
| reverse-engineer-anything | [morluto/rea](https://github.com/morluto/rea)（REA，经 `npx rea-agents setup` 安装） | 逆向工程工具箱：无源码时分析二进制/安装包/固件/浏览器目标，给出带证据的结论 | 2026-10-13 |

### Kimi Code 官方（1 个）

| Skill | 介绍 | 最新修改时间 |
| --- | --- | --- |
| kimi-webbridge | Kimi 浏览器扩展配套：控制用户真实浏览器（带登录态）做网页浏览、点击、填表、截图、抓取等自动化 | 2026-10-13 |

## 同步（本地 → 云端）

```bash
./sync.sh
```

把本地 skill 全量镜像到仓库（多余文件会删除，保证云端与本地完全一致），提交并推送到 GitHub。

## 还原（云端 → 本地）

```bash
git clone git@github.com:flyinthesky1020/my_skill.git
cd my_skill
./restore.sh
```

把仓库内容还原到 `~/.agents/skills/` 和 `~/.kimi-code/skills/`。注意：`--delete` 会删除本地同名目录下不在仓库中的文件，如需保留请先备份。

## 备注

- git 推送使用 `~/.ssh/id_ed25519_xhs` 这把 key 认证 GitHub（账号 flyinthesky1020）。
