#!/usr/bin/env python3
import json
import os
import subprocess
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = Path(os.environ.get("CONFIG_FILE", BASE_DIR / "config.json"))
DATA_FILE = BASE_DIR / "votes.json"
PORT = int(os.environ.get("PORT", "8787"))
HOST = os.environ.get("HOST", "127.0.0.1")
TOAST_ONLY = os.environ.get("TOAST_ONLY", "") == "1"
CONFIG = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
BASE_HOME = os.environ.get("BASE_HOME", CONFIG["lark_cli_home"])
BASE_TOKEN = os.environ.get("BASE_TOKEN", CONFIG["base"]["token"])
RESULT_TABLE_ID = os.environ.get("RESULT_TABLE_ID", CONFIG["base"]["result_table_id"])
CHAT_ID = os.environ.get("CHAT_ID", CONFIG["chats"][0]["chat_id"])
DOC_TOKEN = os.environ.get("DOC_TOKEN", CONFIG["base"]["public_doc_token"])
VOTER_NAMES = {
    "ou_1a78f29cae21e1852c99ec0fa68a8773": "Zero",
    "ou_1c9751103a8225053c6742e6df995e75": "陈俊",
    "ou_test_base_write": "测试用户",
}
VOTER_NAMES.update(CONFIG.get("voter_names", {}))

POLL = {
    "id": "poll-2026-07-01-demo",
    "title": "投票器测试",
    "question": "请选择一个选项：",
    "options": [
        {"id": "A", "label": "选项 A"},
        {"id": "B", "label": "选项 B"},
    ],
}


def read_votes():
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"poll_id": POLL["id"], "votes": {}}


def save_votes(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def counts_from_votes(data):
    counts = {option["id"]: 0 for option in POLL["options"]}
    for vote in data.get("votes", {}).values():
        option = vote.get("option")
        if option in counts:
            counts[option] += 1
    return counts


def pick(payload, *paths):
    for path in paths:
        cur = payload
        for key in path:
            if not isinstance(cur, dict) or key not in cur:
                cur = None
                break
            cur = cur[key]
        if cur:
            return cur
    return None


def voter_id(payload):
    return pick(
        payload,
        ("operator", "open_id"),
        ("operator", "open_id_v2"),
        ("open_id",),
        ("user_id",),
        ("user", "open_id"),
        ("event", "operator", "open_id"),
    ) or "anonymous"


def voter_name(payload):
    open_id = voter_id(payload)
    return VOTER_NAMES.get(open_id, open_id)


def selected_option(payload):
    return pick(
        payload,
        ("action", "value", "option"),
        ("action", "value", "vote"),
        ("action", "option"),
        ("event", "action", "value", "option"),
        ("event", "action", "value", "vote"),
    )


def poll_id(payload):
    return pick(payload, ("action", "value", "poll_id"), ("event", "action", "value", "poll_id")) or POLL["id"]


def topic_title(payload, option):
    return pick(payload, ("action", "value", "topic_title"), ("event", "action", "value", "topic_title")) or option


def message_id(payload):
    return pick(payload, ("context", "open_message_id"), ("context", "message_id"), ("event", "context", "open_message_id")) or ""


def write_vote_to_base(payload, option):
    fields = {
        "投票ID": poll_id(payload),
        "选题标题": topic_title(payload, option),
        "选项": option,
        "投票人OpenID": voter_id(payload),
        "投票人": voter_name(payload),
        "投票时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "群ID": CHAT_ID,
        "消息ID": message_id(payload),
    }
    env = os.environ.copy()
    env["HOME"] = BASE_HOME
    subprocess.run(
        [
            "lark-cli",
            "base",
            "+record-upsert",
            "--base-token",
            BASE_TOKEN,
            "--table-id",
            RESULT_TABLE_ID,
            "--json",
            json.dumps(fields, ensure_ascii=False),
            "--as",
            "user",
            "--format",
            "json",
        ],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def result_card(data, choice=None):
    counts = counts_from_votes(data)
    total = sum(counts.values())
    rows = []
    for option in POLL["options"]:
        count = counts.get(option["id"], 0)
        percent = round((count / total) * 100) if total else 0
        rows.append(f"**{option['label']}**：{count} 票 ({percent}%)")

    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "template": "blue",
            "title": {"tag": "plain_text", "content": POLL["title"]},
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"{POLL['question']}\n\n" + "\n".join(rows) + f"\n\n当前总票数：{total}",
                },
            },
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": option["label"]},
                        "type": "primary" if choice == option["id"] else "default",
                        "value": {"poll_id": POLL["id"], "option": option["id"]},
                    }
                    for option in POLL["options"]
                ],
            },
            {
                "tag": "note",
                "elements": [
                    {
                        "tag": "plain_text",
                        "content": f"已记录本次选择：{choice}" if choice else "点击按钮即可投票；重复点击会更新你的选择。",
                    }
                ],
            },
        ],
    }


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, body):
        raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/results":
            data = read_votes()
            self.send_json(200, {"poll": POLL, "counts": counts_from_votes(data), "votes": data.get("votes", {})})
            return
        self.send_json(200, {"ok": True, "callback": "/lark/card", "results": "/results"})

    def do_POST(self):
        length = int(self.headers.get("content-length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            payload = json.loads(raw or "{}")
        except Exception:
            self.send_json(400, {"ok": False, "error": "invalid json"})
            return

        if self.path != "/lark/card":
            self.send_json(404, {"ok": False, "error": "not found"})
            return

        if payload.get("challenge"):
            self.send_json(200, {"challenge": payload["challenge"]})
            return

        option = selected_option(payload)
        if not option:
            self.send_json(200, {"toast": {"type": "warning", "content": "没有识别到投票选项"}})
            return

        data = read_votes()
        data["poll_id"] = POLL["id"]
        data.setdefault("votes", {})[voter_id(payload)] = {
            "option": option,
            "voted_at": datetime.now(timezone.utc).isoformat(),
        }
        save_votes(data)
        try:
            write_vote_to_base(payload, option)
        except Exception as exc:
            print(f"base write failed: {exc}", flush=True)
        counts = counts_from_votes(data)
        total = sum(counts.values())
        summary = "，".join(f"{item['label']} {counts.get(item['id'], 0)}" for item in POLL["options"])

        if TOAST_ONLY:
            self.send_json(
                200,
                {
                    "toast": {
                        "type": "success",
                        "content": f"已投：{option}。当前 {summary}，共 {total} 票",
                    }
                },
            )
            return

        self.send_json(
            200,
            {
                "toast": {"type": "success", "content": f"已投：{option}"},
                "card": result_card(data, option),
            },
        )

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}", flush=True)


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"poll callback listening on http://{HOST}:{PORT}", flush=True)
    server.serve_forever()
