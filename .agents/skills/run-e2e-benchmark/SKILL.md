---
name: run-e2e-benchmark
description: Run Office benchmark tasks through a configured E2E HTTP/API interface or Harbor-style task runner, with per-task isolation, attachment manifests, trace preservation, token accounting, artifact checks, concurrency controls, and failure-pattern aggregation. Use when Codex must batch-evaluate WPS/Office tasks, compare serial versus parallel behavior, or produce an auditable execution report.
---

# Run E2E benchmark

Execute benchmark tasks as isolated, reproducible runs. The skill is an orchestration layer: the E2E endpoint/runner is supplied by configuration, never hard-coded into the skill.

## Required inputs

- A validated benchmark plan. Run `$generate-benchmark-tasks` first when the plan has not been audited.
- An explicit E2E endpoint or local runner command. Do not infer a production endpoint from a document or webpage.
- A writable run root and an output policy (where artifacts, traces, logs, and summaries are stored).
- Authentication supplied through environment variables or a protected headers file. Never place API keys in a plan, prompt, result, or trace.

Read [e2e-contract.md](references/e2e-contract.md) before using a non-default endpoint contract.

## Execution workflow

### 1. Preflight

1. Validate the plan and attachment files.
2. Create a run directory and immutable copy of the task manifest.
3. Record host, runner version, endpoint, concurrency, and start time; redact secrets.
4. Check that every task has a unique run directory and that input files are not being modified in place.

For WPS/CEF/GUI tasks, require macOS + WPS GUI when the benchmark declares that requirement. Linux/Docker dry runs are diagnostics, not passes.

### 2. Enforce process isolation

- Default to serial execution for a shared desktop, WPS profile, COM application, `publish.xml`, or CEF profile.
- Permit parallelism only when each worker has an independent application/profile/session/output directory and the endpoint documents concurrency safety.
- A requested `--concurrency 4` means four isolated workers, not four chats in one WPS window. If isolation cannot be proven, run serially and record `concurrency_blocked`.
- Never let two tasks write the same input, output, profile, or temporary directory.

### 3. Submit one task

For each task, send a normalized payload containing:

- `run_id`, `item_id`, `chat_id`, `user_message_id`;
- the original query and derived task prompt;
- a message-scoped attachment manifest with absolute paths, names, MIME types, and checksums;
- task category, expected output, and acceptance checks;
- an isolated `run_dir` and `artifact_dir`.

The helper `scripts/run_e2e.py` sends this JSON contract, records the raw response, and extracts common trace/token/artifact fields. Use `--dry-run` to inspect payloads without contacting the endpoint.

### 4. Preserve evidence

Each task directory must contain, at minimum:

```text
request.json          # redacted request
attachments.json      # exact input set and checksums
response.json         # raw endpoint response
result.json           # normalized status/timing/tokens/traces/artifacts
events.ndjson         # event or progress records when supplied
stdout.log / stderr.log
artifacts/             # outputs copied or linked by the runner
```

Do not replace a failed task with a screenshot or a hand-written PASS. Keep partial artifacts and the failure reason.

### 5. Account for tokens and time

- Prefer authoritative `input_tokens`, `output_tokens`, `total_tokens`, `cached_tokens`, `duration_ms`, and trace IDs returned by the endpoint.
- If token usage is exposed only by a separate token dashboard/API, take a timestamped before/after snapshot and record the lookup method and uncertainty. Never claim per-task attribution when requests overlap and cannot be separated.
- Record `started_at`, `ended_at`, duration, retry count, endpoint status, and artifact completion time.

### 6. Classify failures

Normalize failures using the taxonomy in [failure-patterns.md](references/failure-patterns.md). At least distinguish:

- attachment missing/mismatched/corrupt;
- endpoint/auth/HTTP/timeout;
- session or profile collision;
- UI/WPS hang or wrong-window interaction;
- output missing, wrong type, or not editable;
- content/acceptance failure;
- trace/token accounting unavailable.

Aggregate repeated symptoms into a `failure_patterns.json` with counts, affected task IDs, first/last occurrence, evidence paths, and a concise remediation hypothesis. Do not turn a hypothesis into a confirmed root cause.

### 7. Finish and report

Run `scripts/aggregate_results.py --run-root RUN_ROOT`. The final report must include task status, timings, tokens, trace IDs, artifact paths, retries, failure classes, and a concurrency note. Mark a task `pass` only when the E2E result and required artifacts/acceptance checks are present.

## Safety and reproducibility rules

- Do not send files or prompts to an endpoint until the user has supplied/authorized that endpoint for this benchmark.
- Do not expose auth headers, cookies, provider keys, or signed download URLs in logs.
- Do not delete failed runs. Use a new attempt directory for retries and link it with `retry_of`.
- Do not run parallel tasks in one visible WPS window. Parallelism is a resource-isolation feature, not a request to open multiple chats in one instance.
- Preserve the exact original query; any evaluation-only additions belong in a separate field.
