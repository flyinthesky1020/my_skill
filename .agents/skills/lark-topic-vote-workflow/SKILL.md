---
name: lark-topic-vote-workflow
description: Configure, deploy, and operate a fixed Feishu/Lark group workflow for weekly topic collection, missing-submission reminders, interactive voting, result recording, and date-based publication. Use when the user wants a Feishu group bot/agent to initialize or maintain this service through @mentions, configure trigger groups, collection forms, Base tables, schedule times, message copy, card callbacks, or run Monday/Tuesday/Wednesday/Thursday topic-vote steps.
---

# Lark Topic Vote Workflow

Use this skill to turn a Feishu/Lark bot into a fixed, configurable topic collection and voting service. The service is intentionally deterministic: LLMs may help interpret initialization messages, but execution uses explicit config and scripts.

## Core Files

- `scripts/config.template.json`: copy to the deployed service as `config.json`, then fill in group, Base, form, schedule, and copy settings.
- `scripts/server.py`: card callback service. It records real button clicks to the configured Base result table.
- `scripts/workflow.py`: fixed workflow runner for `monday`, `tuesday`, `wednesday`, and `thursday`.
- `references/group-init-protocol.md`: @群机器人初始化/修改配置的 conversation protocol.
- `references/deployment.md`: local/server deployment and callback URL notes.

## Standard Workflow

1. **Collect configuration**
   - Trigger group chat IDs.
   - Collection form URL.
   - Base token, topic table/view, result table, public result doc token.
   - Weekly schedule times.
   - Message copy for each step.
   - Lark app ID and app secret file path.

2. **Create service config**
   - Copy `scripts/config.template.json` to the deployment directory as `config.json`.
   - Fill all fields. Do not store app secrets directly in JSON; store a filesystem path in `app.app_secret_file`.

3. **Authorize identity**
   - Use `lark-cli auth login` with the service `HOME` to grant user scopes for Base, Docx, IM, and block reads.
   - Required minimum scopes:
     - `base:app:read base:table:read base:field:read base:record:read base:record:create base:record:update base:block:read`
     - `docx:document:readonly docx:document:write_only`
     - `im:chat.members:read im:message`

4. **Run callback service**
   - Start `scripts/server.py` with `CONFIG_FILE=/path/to/config.json`.
   - Expose `/lark/card` as a public HTTPS card callback URL.
   - Configure this URL in the Feishu app card callback setting.

5. **Run workflow steps**
   - Monday: `python3 scripts/workflow.py monday`
   - Tuesday: `python3 scripts/workflow.py tuesday`
   - Wednesday: `python3 scripts/workflow.py wednesday`
   - Thursday: `python3 scripts/workflow.py thursday --poll-id <poll-id>`

## Behavior Rules

- Result publication is date-based for users. Do not expose internal poll IDs in the public doc or group summary.
- Keep poll IDs in the Base result table for filtering and de-duplication.
- Count at most one effective vote per person per poll: latest click wins.
- The callback service writes raw vote records only. It must not update the public doc on each click.
- The Thursday workflow refreshes the public doc and sends the descriptive summary to the group.
- When a user asks to change schedule/copy/form/group, update `config.json`; do not edit script constants unless the behavior itself changes.

## Group @ Initialization

When the bot/agent is @mentioned for initialization, follow `references/group-init-protocol.md`.

Minimal supported commands:

- `@机器人 初始化选题投票流程`
- `@机器人 设置收集表 <url>`
- `@机器人 设置群聊 当前群`
- `@机器人 设置周三投票 10:00`
- `@机器人 设置周四公示 18:00`
- `@机器人 发送本周填表提醒`
- `@机器人 发起本周投票`
- `@机器人 公示今天结果`

For write actions that change config or send messages, summarize the action and ask for confirmation unless the user explicitly says this is a test run.

## Validation

After setup:

1. Run `python3 scripts/workflow.py monday` against a test group.
2. Run `python3 scripts/workflow.py wednesday` and click a card button.
3. Verify the result table has a new row with `投票人` in Chinese.
4. Run `python3 scripts/workflow.py thursday --poll-id <poll-id>`.
5. Verify the public doc is grouped by date and the group receives the same descriptive summary.
