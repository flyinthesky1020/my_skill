# Group @ Initialization Protocol

Use this protocol when the bot/agent receives a Feishu group mention asking to initialize or modify the topic-vote workflow.

## Initialization Slots

Collect these fields before declaring the workflow ready:

| Slot | Example | Required |
|---|---|---|
| `chat_id` | current group `oc_xxx` | yes |
| `collection_form_url` | `/share/base/form/...` URL | yes |
| `base.token` | `/base/{token}` | yes |
| `topic_table_id` | `tbl...` | yes |
| `topic_grid_view_id` | grid view, not form view | yes |
| `result_table_id` | table for raw vote records | yes |
| `public_doc_token` | docx token for date-based summary | yes |
| `schedule.*.time` | `10:00`, `18:00` | yes |
| `copy.*` | message templates | optional |

If the user provides a Base URL, parse:

- `/base/{token}` -> `base.token`
- `?table=tbl...` -> table id
- `?view=vew...` -> view id

If the URL points to a Base docx block, use `base +base-block-list` to resolve block id to `docx_token`.

## Conversation Pattern

1. Acknowledge intent.
2. Extract slots from the message.
3. Ask for missing required slots in one compact message.
4. When all required slots exist, show a concise config preview.
5. Ask for confirmation before writing config or sending messages.
6. After confirmation, update `config.json` and run a dry validation where possible.

## Safe Defaults

- Default schedule:
  - Monday 10:00: collect reminder
  - Tuesday 10:00: missing check
  - Wednesday 10:00: start vote
  - Thursday 18:00: publish result
- Default `top_n`: 3.
- Default dedupe: latest vote per user per poll.
- Only respond in configured/enabled chats.
- Only process write commands from known admins when the deployment supports admin identity checks.

## Supported @ Commands

- `初始化选题投票流程`
- `设置收集表 <url>`
- `设置结果文档 <url>`
- `设置周一提醒 <HH:MM>`
- `设置周二检查 <HH:MM>`
- `设置周三投票 <HH:MM>`
- `设置周四公示 <HH:MM>`
- `发送填表提醒`
- `检查未填`
- `发起本周投票`
- `公示今天结果`

For destructive or broad changes, ask for confirmation.
