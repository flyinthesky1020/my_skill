# E2E request and response contract

The bundled runner uses a deliberately small JSON-over-HTTP contract so it can sit in front of different E2E services. Adapt only the endpoint URL and documented field mapping.

## Request

```json
{
  "run_id": "serial-20260907-W04-attempt-01",
  "item_id": "W04",
  "chat_id": "19fd…",
  "user_message_id": "1a066…",
  "query": "原始用户 query",
  "task_prompt": "评测提示",
  "attachments": [{"name": "input.docx", "path": "/abs/input.docx", "sha256": "…"}],
  "expected_output": "可编辑 DOCX",
  "acceptance_checks": ["artifact_exists", "editable_docx"],
  "run_dir": "/abs/runs/W04/attempt-01",
  "artifact_dir": "/abs/runs/W04/attempt-01/artifacts"
}
```

The endpoint may return a synchronous JSON response or an accepted job. If it returns a job ID, the adapter must poll the documented status endpoint and save every status event to `events.ndjson`. Do not guess undocumented endpoints.

## Response normalization

The runner searches common names but keeps the raw response. Prefer these fields when available:

```json
{
  "status": "passed|failed|running",
  "trace_id": "…",
  "trace_ids": ["…"],
  "started_at": "2026-09-07T10:00:00Z",
  "ended_at": "2026-09-07T10:04:00Z",
  "duration_ms": 240000,
  "usage": {"input_tokens": 1000, "output_tokens": 500, "total_tokens": 1500, "cached_tokens": 0},
  "artifacts": [{"path": "/abs/out.docx", "kind": "docx"}],
  "error": {"code": "…", "message": "…"}
}
```

Do not infer a pass from HTTP 200 alone. A pass requires a terminal success status, the expected artifact, and any configured acceptance checks.

## Configuration

Use `--headers-json` for non-secret headers stored outside the repository, or `--auth-env ENV_NAME` to read one bearer token from an environment variable. The runner writes a redacted request; it never writes auth headers.
