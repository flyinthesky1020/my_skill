# Deployment Notes

## Local Test

```bash
cd /path/to/service
cp scripts/config.template.json config.json
python3 scripts/server.py
python3 scripts/workflow.py monday
```

Expose the card callback through HTTPS:

```bash
cloudflared tunnel --url http://127.0.0.1:8787
```

Configure Feishu card callback URL:

```text
https://<public-host>/lark/card
```

## Persistent Service

For production, deploy to a server with a stable domain and HTTPS. Avoid account-less temporary tunnels for long-running service.

Run `server.py` as a service with:

```bash
CONFIG_FILE=/path/to/config.json python3 scripts/server.py
```

Schedule weekly steps with cron/systemd timers:

```bash
python3 scripts/workflow.py monday
python3 scripts/workflow.py tuesday
python3 scripts/workflow.py wednesday
python3 scripts/workflow.py thursday
```

Pass `--poll-id` for test or backfill:

```bash
python3 scripts/workflow.py thursday --poll-id weekly-topic-2026-07-01
```

## Required Feishu Permissions

User identity scopes:

- `base:app:read`
- `base:table:read`
- `base:field:read`
- `base:record:read`
- `base:record:create`
- `base:record:update`
- `base:block:read`
- `docx:document:readonly`
- `docx:document:write_only`
- `im:chat.members:read`
- `im:message`

Bot identity/app permissions:

- Send IM messages.
- Receive card callback.

## Important Behavior

- `server.py` only records raw votes to Base.
- `workflow.py thursday` refreshes the public doc and sends the group summary.
- Public summaries are grouped by date only; internal poll IDs stay in the result table.
