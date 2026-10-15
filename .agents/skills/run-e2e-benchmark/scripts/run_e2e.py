#!/usr/bin/env python3
"""Submit benchmark tasks to a configured E2E JSON endpoint."""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any


TOKEN_KEYS = ("input_tokens", "prompt_tokens", "output_tokens", "completion_tokens", "total_tokens", "cached_tokens")
TRACE_KEYS = ("trace_id", "traceId", "trace_ids", "traceIds", "session_id", "job_id")
SENSITIVE_ATTACHMENT_KEYS = {
    "url",
    "download_url",
    "signed_url",
    "presigned_url",
    "access_token",
    "token",
    "cookie",
    "authorization",
}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def load_tasks(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("tasks", "items", "selected"):
            if isinstance(data.get(key), list):
                return [x for x in data[key] if isinstance(x, dict)]
    raise ValueError("plan must be a JSON array or contain tasks/items/selected")


def attachments(task: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(task.get("attachments"), list):
        return [x for x in task["attachments"] if isinstance(x, dict)]
    return [{"path": x, "name": Path(x).name} for x in task.get("input_files", []) if isinstance(x, str)]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def attachment_manifest(task: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for item in attachments(task):
        # Keep the manifest useful for replay while avoiding signed URLs and
        # bearer material in request/attachment logs.
        raw = {key: value for key, value in dict(item).items() if key.lower() not in SENSITIVE_ATTACHMENT_KEYS}
        path_value = raw.get("path") or raw.get("local_path")
        if isinstance(path_value, str):
            path = Path(path_value).expanduser().resolve()
            raw["path"] = str(path)
            raw["exists"] = path.is_file()
            if path.is_file():
                raw["size_bytes"] = path.stat().st_size
                raw["sha256"] = raw.get("sha256") or sha256(path)
        out.append(raw)
    return out


def extract_values(value: Any, keys: tuple[str, ...], out: list[Any] | None = None) -> list[Any]:
    out = [] if out is None else out
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys and item not in (None, ""):
                out.append(item)
            extract_values(item, keys, out)
    elif isinstance(value, list):
        for item in value:
            extract_values(item, keys, out)
    return out


def normalize_status(response: Any, http_status: int | None, error: str | None) -> str:
    if error:
        return "error"
    values = [str(x).lower() for x in extract_values(response, ("status", "state", "result_status"))]
    if any(x in {"passed", "pass", "success", "succeeded", "complete", "completed", "ok"} for x in values):
        return "passed"
    if any(x in {"failed", "failure", "error", "cancelled", "canceled", "timeout"} for x in values):
        return "failed"
    if http_status is not None and http_status >= 400:
        return "error"
    return "unknown"


def classify_failure(status: str, response: Any, error: str | None) -> str | None:
    if status == "dry_run":
        return None
    text = (error or "") + " " + json.dumps(response, ensure_ascii=False).lower()
    patterns = [
        ("endpoint_auth", r"401|403|unauthori|forbidden|token.?expir"),
        ("timeout", r"timeout|timed out|deadline"),
        ("attachment_missing", r"attachment.*(missing|not found)|file.*(missing|not found)"),
        ("attachment_corrupt", r"corrupt|bad zip|parse error|invalid file"),
        ("attachment_mismatch", r"attachment.*mismatch|message.*(mismatch|not owner)|wrong chat.?id"),
        ("profile_collision", r"profile|publish\.xml|com application|already in use|collision"),
        ("wrong_window", r"wrong window|another task|session mismatch"),
        ("ui_hang", r"hang|no progress|unresponsive"),
        ("artifact_missing", r"artifact.*missing|output.*missing|no output"),
        ("artifact_invalid", r"artifact.*(invalid|wrong type|not editable)|not editable|parse/render failure"),
        ("trace_missing", r"trace.*missing|no trace"),
        ("token_unattributed", r"token.*unattribut|usage.*unattribut"),
    ]
    if status in {"passed", "unknown"} and not error:
        return None
    for name, pattern in patterns:
        if re.search(pattern, text):
            return name
    return "endpoint_http" if status == "error" else "content_acceptance"


def post_json(endpoint: str, payload: dict[str, Any], headers: dict[str, str], timeout: float) -> tuple[int, Any, str | None]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(endpoint, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    for key, value in headers.items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            try:
                value = json.loads(raw.decode("utf-8"))
            except Exception:
                value = {"body_text": raw.decode("utf-8", errors="replace")}
            return resp.status, value, None
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            value = json.loads(raw.decode("utf-8"))
        except Exception:
            value = {"body_text": raw.decode("utf-8", errors="replace")}
        return exc.code, value, str(exc)
    except Exception as exc:
        return 0, {}, str(exc)


def run_one(task: dict[str, Any], args: argparse.Namespace, headers: dict[str, str], blocked: bool) -> dict[str, Any]:
    item_id = str(task.get("item_id") or task.get("id") or uuid.uuid4().hex[:8])
    run_id = f"{args.run_label}-{item_id}-{uuid.uuid4().hex[:8]}"
    run_dir = args.out_dir / item_id / run_id
    artifact_dir = run_dir / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    manifest = attachment_manifest(task)
    payload = {
        "run_id": run_id,
        "item_id": item_id,
        "chat_id": task.get("chat_id") or task.get("chatId"),
        "user_message_id": task.get("user_message_id") or task.get("message_id"),
        "query": task.get("original_query") or task.get("query"),
        "task_prompt": task.get("task_prompt") or task.get("query"),
        "attachments": manifest,
        "expected_output": task.get("expected_output"),
        "acceptance_checks": task.get("acceptance_checks", []),
        "run_dir": str(run_dir.resolve()),
        "artifact_dir": str(artifact_dir.resolve()),
    }
    (run_dir / "request.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (run_dir / "attachments.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # These files make the per-task evidence layout stable even when the
    # endpoint is synchronous or the dry-run does not emit events.
    (run_dir / "events.ndjson").write_text("", encoding="utf-8")
    (run_dir / "stdout.log").write_text("", encoding="utf-8")
    (run_dir / "stderr.log").write_text("", encoding="utf-8")
    started = time.monotonic()
    started_at = now()
    status_code: int | None = None
    response: Any = {}
    error: str | None = None
    if args.dry_run:
        response = {"status": "dry_run"}
        status_code = 0
    else:
        status_code, response, error = post_json(args.endpoint, payload, headers, args.timeout)
    ended_at = now()
    elapsed_ms = round((time.monotonic() - started) * 1000)
    status = "dry_run" if args.dry_run else normalize_status(response, status_code, error)
    traces = extract_values(response, TRACE_KEYS)
    usage = {}
    for key in TOKEN_KEYS:
        values = extract_values(response, (key,))
        if values:
            usage[key] = values[0]
    artifacts = extract_values(response, ("artifacts", "artifact_paths", "output_paths"))
    result = {
        "run_id": run_id,
        "item_id": item_id,
        "status": status,
        "http_status": status_code,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_ms": elapsed_ms,
        "trace_ids": traces,
        "usage": usage,
        "artifacts": artifacts,
        "error": error,
        "failure_class": classify_failure(status, response, error),
        "concurrency_blocked": blocked,
    }
    (run_dir / "response.json").write_text(json.dumps(response, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (run_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--endpoint", default="")
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--allow-parallel", action="store_true")
    parser.add_argument("--timeout", type=float, default=3600)
    parser.add_argument("--headers-json", type=Path)
    parser.add_argument("--auth-env")
    parser.add_argument("--run-label", default="e2e")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not args.dry_run and not args.endpoint:
        parser.error("--endpoint is required unless --dry-run is used")
    if args.concurrency < 1:
        parser.error("--concurrency must be at least 1")
    headers: dict[str, str] = {}
    if args.headers_json:
        headers.update(json.loads(args.headers_json.read_text(encoding="utf-8")))
    if args.auth_env:
        token = os.environ.get(args.auth_env)
        if token:
            headers["Authorization"] = f"Bearer {token}"
    tasks = load_tasks(args.plan)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    effective = args.concurrency if args.allow_parallel else 1
    blocked = args.concurrency > 1 and not args.allow_parallel
    run_meta = {"plan": str(args.plan), "endpoint": args.endpoint, "requested_concurrency": args.concurrency, "effective_concurrency": effective, "concurrency_blocked": blocked, "started_at": now()}
    (args.out_dir / "run.json").write_text(json.dumps(run_meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    results: list[dict[str, Any]] = []
    if effective == 1:
        for task in tasks:
            results.append(run_one(task, args, headers, blocked))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=effective) as pool:
            futures = [pool.submit(run_one, task, args, headers, blocked) for task in tasks]
            for future in futures:
                results.append(future.result())
    summary = {"run": run_meta, "ended_at": now(), "task_count": len(results), "results": results}
    (args.out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out_dir": str(args.out_dir), "task_count": len(results), "effective_concurrency": effective, "concurrency_blocked": blocked}, ensure_ascii=False))
    return 0 if all(r["status"] in {"passed", "dry_run"} for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
