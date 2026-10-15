# Failure pattern taxonomy

Use one primary class per failed attempt and preserve the raw error alongside it.

| Class | Typical evidence | Safe interpretation |
| --- | --- | --- |
| `attachment_missing` | manifest path absent or file ID not in the message | Input scope is incomplete; do not rerun with guessed files |
| `attachment_corrupt` | bad magic bytes, unzip/parse error, replacement-character-heavy text | Source quality problem; keep the original and flag it |
| `attachment_mismatch` | query/message ID and attachment owner disagree | Join bug or stale whole-chat manifest |
| `endpoint_auth` | 401/403 or token-expired response | Configuration/auth failure, not a task failure |
| `endpoint_http` | 4xx/5xx with a structured server error | Service or request contract issue |
| `timeout` | no terminal result before deadline | Preserve last status event and retry separately |
| `profile_collision` | two tasks share WPS profile, `publish.xml`, COM app, or output | Concurrency isolation failure |
| `wrong_window` | artifact belongs to another task/session | UI targeting or shared-window failure |
| `ui_hang` | WPS/CEF process alive but no progress | Desktop runner liveness issue |
| `artifact_missing` | terminal response but no expected output | E2E output/publish failure |
| `artifact_invalid` | wrong type, not editable, or parse/render failure | Output acceptance failure |
| `content_acceptance` | artifact exists but fails task-specific checks | Benchmark task failure |
| `trace_missing` | no trace ID/events | Observability gap; do not claim full traceability |
| `token_unattributed` | dashboard total cannot be mapped to one task | Report aggregate usage with attribution uncertainty |

When several tasks show the same class, report the common evidence and affected run IDs. Keep “likely cause” separate from “observed fact”.
