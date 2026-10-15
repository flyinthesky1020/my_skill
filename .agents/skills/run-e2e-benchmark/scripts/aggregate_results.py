#!/usr/bin/env python3
"""Aggregate per-task E2E result.json files into a report and failure patterns."""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", required=True, type=Path)
    args = parser.parse_args()
    results = []
    for path in sorted(args.run_root.glob("**/result.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            value["result_path"] = str(path)
            results.append(value)
        except Exception as exc:
            results.append({"status": "error", "failure_class": "malformed_result", "result_path": str(path), "error": str(exc)})
    counts = collections.Counter(str(x.get("status", "unknown")) for x in results)
    failures: dict[str, dict[str, Any]] = {}
    for item in results:
        failure = item.get("failure_class")
        if not failure:
            continue
        entry = failures.setdefault(failure, {"count": 0, "item_ids": [], "run_ids": [], "evidence": []})
        entry["count"] += 1
        if item.get("item_id") is not None:
            entry["item_ids"].append(item["item_id"])
        if item.get("run_id") is not None:
            entry["run_ids"].append(item["run_id"])
        entry["evidence"].append(item.get("result_path"))
    total_usage = collections.defaultdict(float)
    for item in results:
        for key, value in (item.get("usage") or {}).items():
            if isinstance(value, (int, float)):
                total_usage[key] += value
    summary = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "run_root": str(args.run_root),
        "task_count": len(results),
        "status_counts": dict(counts),
        "token_totals": dict(total_usage),
        "failure_patterns": failures,
        "results": results,
    }
    (args.run_root / "aggregate.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.run_root / "failure_patterns.json").write_text(json.dumps(failures, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"task_count": len(results), "status_counts": dict(counts), "failure_classes": list(failures)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
