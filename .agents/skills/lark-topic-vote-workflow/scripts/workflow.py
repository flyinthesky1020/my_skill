#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"


def load_config():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def run_lark(config, args):
    env = os.environ.copy()
    env["HOME"] = config["lark_cli_home"]
    result = subprocess.run(
        ["lark-cli", *args],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def tenant_token(config):
    app = config["app"]
    secret = Path(app["app_secret_file"]).read_text(encoding="utf-8").strip()
    req = Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=json.dumps({"app_id": app["app_id"], "app_secret": secret}).encode("utf-8"),
        headers={"content-type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urlopen(req, timeout=20) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    if body.get("code") != 0:
        raise RuntimeError(f"tenant token failed: {body}")
    return body["tenant_access_token"]


def send_text(config, chat_id, text):
    token = tenant_token(config)
    payload = {
        "receive_id": chat_id,
        "msg_type": "text",
        "content": json.dumps({"text": text}, ensure_ascii=False),
    }
    req = Request(
        "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with urlopen(req, timeout=20) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    if body.get("code") != 0:
        raise RuntimeError(f"send text failed: {body}")
    return body["data"]


def send_poll_card(config, chat_id, poll_id, topics):
    token = tenant_token(config)
    actions = []
    for index, topic in enumerate(topics[: config["poll"]["max_options"]]):
        actions.append(
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": f"{index + 1}. {topic}"},
                        "type": "primary" if index == 0 else "default",
                        "value": {"poll_id": poll_id, "option": topic, "topic_title": topic},
                    }
                ],
            }
        )
    card = {
        "config": {"wide_screen_mode": True},
        "header": {"template": "blue", "title": {"tag": "plain_text", "content": "本周选题投票"}},
        "elements": [
            {
                "tag": "div",
                "text": {"tag": "lark_md", "content": config["copy"]["wednesday_start_poll"]},
            },
            *actions,
        ],
    }
    payload = {
        "receive_id": chat_id,
        "msg_type": "interactive",
        "content": json.dumps(card, ensure_ascii=False),
    }
    req = Request(
        "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with urlopen(req, timeout=20) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    if body.get("code") != 0:
        raise RuntimeError(f"send poll failed: {body}")
    return body["data"]


def enabled_chats(config):
    return [chat for chat in config["chats"] if chat.get("enabled", True)]


def list_chat_members(config, chat_id):
    result = run_lark(
        config,
        [
            "im",
            "chat.members",
            "get",
            "--params",
            json.dumps({"chat_id": chat_id, "member_id_type": "open_id", "page_size": 100}),
            "--as",
            "user",
            "--format",
            "json",
        ],
    )
    return result["data"]["items"]


def list_topics(config):
    base = config["base"]
    result = run_lark(
        config,
        [
            "base",
            "+record-list",
            "--base-token",
            base["token"],
            "--table-id",
            base["topic_table_id"],
            "--view-id",
            base["topic_grid_view_id"],
            "--as",
            "user",
            "--limit",
            "200",
            "--format",
            "json",
        ],
    )
    fields = result["data"]["fields"]
    title_index = fields.index("选题标题")
    submitter_index = fields.index("人员")
    topics = []
    submitters = {}
    for row in result["data"]["data"]:
        title = row[title_index]
        if title:
            topics.append(title)
        for person in row[submitter_index] or []:
            submitters[person["id"]] = person.get("name") or person["id"]
    return topics, submitters


def list_votes(config):
    base = config["base"]
    result = run_lark(
        config,
        [
            "base",
            "+record-list",
            "--base-token",
            base["token"],
            "--table-id",
            base["result_table_id"],
            "--as",
            "user",
            "--limit",
            "500",
            "--format",
            "json",
        ],
    )
    fields = result["data"]["fields"]
    return [dict(zip(fields, row)) for row in result["data"]["data"]]


def poll_id_for_today(prefix="weekly-topic"):
    return f"{prefix}-{datetime.now().strftime('%Y-%m-%d')}"


def step_monday(config):
    for chat in enabled_chats(config):
        text = config["copy"]["monday_collect_reminder"].format(
            form_url=config["base"]["collection_form_url"]
        )
        send_text(config, chat["chat_id"], text)


def step_tuesday(config):
    _, submitters = list_topics(config)
    for chat in enabled_chats(config):
        members = list_chat_members(config, chat["chat_id"])
        missing = [m for m in members if m["member_id"] not in submitters]
        if missing:
            mentions = "\n".join(
                f'<at user_id="{member["member_id"]}">{member.get("name", member["member_id"])}</at>'
                for member in missing
            )
            text = config["copy"]["tuesday_missing_check"].format(
                mentions=mentions,
                form_url=config["base"]["collection_form_url"],
            )
        else:
            text = config["copy"]["tuesday_all_done"]
        send_text(config, chat["chat_id"], text)


def step_wednesday(config):
    topics, _ = list_topics(config)
    poll_id = poll_id_for_today()
    for chat in enabled_chats(config):
        send_poll_card(config, chat["chat_id"], poll_id, topics)
    return poll_id


def summarize_votes(config, poll_id):
    topics, _ = list_topics(config)
    votes = [vote for vote in list_votes(config) if vote.get("投票ID") == poll_id]
    latest_by_user = {}
    for vote in votes:
        user = vote.get("投票人OpenID")
        if not user:
            continue
        if user not in latest_by_user or str(vote.get("投票时间", "")) >= str(
            latest_by_user[user].get("投票时间", "")
        ):
            latest_by_user[user] = vote

    voters_by_topic = defaultdict(list)
    for vote in latest_by_user.values():
        voters_by_topic[vote.get("选题标题") or vote.get("选项")].append(vote.get("投票人") or vote.get("投票人OpenID"))

    ranked = sorted(
        ((topic, len(voters_by_topic.get(topic, [])), voters_by_topic.get(topic, [])) for topic in topics),
        key=lambda item: (-item[1], topics.index(item[0])),
    )
    return topics, ranked[: config["poll"]["top_n"]], len(latest_by_user)


def render_summary_text(date_label, topics, top_results, valid_count):
    topic_lines = "\n".join(f"{idx + 1}. {topic}" for idx, topic in enumerate(topics))
    result_lines = "\n".join(
        f"{idx + 1}. {topic}：{count} 票（投票人：{'、'.join(voters) if voters else '—'}）"
        for idx, (topic, count, voters) in enumerate(top_results)
    )
    return (
        f"{date_label} 投票结果\n\n"
        f"本次选题：\n{topic_lines}\n\n"
        f"Top {len(top_results)}：\n{result_lines}\n\n"
        f"有效投票人数：{valid_count}"
    )


def render_summary_xml(date_label, topics, top_results, valid_count):
    topic_items = "".join(f'<li seq="auto">{escape_xml(topic)}</li>' for topic in topics)
    rows = "".join(
        "<tr>"
        f"<td>{idx + 1}</td>"
        f"<td>{escape_xml(topic)}</td>"
        f"<td>{count}</td>"
        f"<td>{escape_xml('、'.join(voters) if voters else '—')}</td>"
        "</tr>"
        for idx, (topic, count, voters) in enumerate(top_results)
    )
    return (
        "<title>投票结果公示</title>"
        '<callout emoji="✅" background-color="light-green" border-color="green">'
        "<p>本页按日期分组公示投票结果。统计口径：同一天同一轮投票中，每位投票人只保留最新一次选择。</p>"
        "</callout>"
        f"<h2>{date_label}</h2>"
        "<h3>本次选题</h3>"
        f"<ol>{topic_items}</ol>"
        "<h3>Top 3 投票结果</h3>"
        '<table><thead><tr><th background-color="light-gray">排名</th><th background-color="light-gray">选题</th><th background-color="light-gray">票数</th><th background-color="light-gray">投票人</th></tr></thead>'
        f"<tbody>{rows}</tbody></table>"
        f"<p>有效投票人数：{valid_count}。</p>"
    )


def escape_xml(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def update_public_doc(config, content):
    run_lark(
        config,
        [
            "docs",
            "+update",
            "--api-version",
            "v2",
            "--doc",
            config["base"]["public_doc_token"],
            "--command",
            "overwrite",
            "--content",
            content,
            "--as",
            "user",
            "--format",
            "json",
        ],
    )


def step_thursday(config, poll_id=None):
    poll_id = poll_id or poll_id_for_today()
    date_label = poll_id.rsplit("-", 3)[-3:]
    if len(date_label) == 3 and all(part.isdigit() for part in date_label):
        date_label = "-".join(date_label)
    else:
        date_label = datetime.now().strftime("%Y-%m-%d")
    topics, top_results, valid_count = summarize_votes(config, poll_id)
    summary = render_summary_text(date_label, topics, top_results, valid_count)
    update_public_doc(config, render_summary_xml(date_label, topics, top_results, valid_count))
    for chat in enabled_chats(config):
        send_text(config, chat["chat_id"], config["copy"]["thursday_publish_result"].format(summary=summary))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=["monday", "tuesday", "wednesday", "thursday"])
    parser.add_argument("--poll-id")
    args = parser.parse_args()
    config = load_config()
    if args.step == "monday":
        step_monday(config)
    elif args.step == "tuesday":
        step_tuesday(config)
    elif args.step == "wednesday":
        print(step_wednesday(config))
    elif args.step == "thursday":
        step_thursday(config, args.poll_id)


if __name__ == "__main__":
    main()
