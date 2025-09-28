#!/usr/bin/env python3

"""Simple macOS bridge that connects iMessage threads to the OpenPoke backend."""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from urllib import request as urlrequest


CHAT_DB_PATH = Path.home() / "Library/Messages/chat.db"
STATE_PATH = Path.home() / ".openpoke" / "imessage_state.json"


def load_state() -> int:
    try:
        with STATE_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
            return int(data.get("last_rowid", 0))
    except FileNotFoundError:
        return 0
    except Exception:
        return 0


def save_state(last_rowid: int) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STATE_PATH.open("w", encoding="utf-8") as handle:
        json.dump({"last_rowid": last_rowid}, handle)


def escape_applescript_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\"", "\\\"")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def send_imessage(chat_guid: str, message: str) -> None:
    safe_chat = escape_applescript_text(chat_guid)
    safe_message = escape_applescript_text(message)
    script = f'''
    tell application "Messages"
        set targetChat to first chat whose id is "{safe_chat}"
        send "{safe_message}" to targetChat
    end tell
    '''
    subprocess.run(["osascript", "-e", script], check=True)


def fetch_messages(connection: sqlite3.Connection, last_rowid: int) -> Iterable[Dict[str, Any]]:
    query = """
        SELECT message.rowid, message.text, chat.guid
        FROM message
        JOIN chat_message_join ON chat_message_join.message_id = message.rowid
        JOIN chat ON chat.ROWID = chat_message_join.chat_id
        WHERE message.is_from_me = 0
          AND message.text IS NOT NULL
          AND message.rowid > ?
        ORDER BY message.rowid ASC
    """
    cursor = connection.execute(query, (last_rowid,))
    columns = [col[0] for col in cursor.description]
    for row in cursor.fetchall():
        item = dict(zip(columns, row))
        text = item.get("text")
        guid = item.get("guid")
        if not text or not guid:
            continue
        yield {
            "rowid": int(item["rowid"]),
            "text": str(text),
            "guid": str(guid),
        }


def post_to_backend(endpoint: str, conversation_id: str, message: str, token: Optional[str]) -> str:
    payload = json.dumps({"conversation_id": conversation_id, "message": message}).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urlrequest.Request(endpoint, data=payload, headers=headers, method="POST")
    with urlrequest.urlopen(request, timeout=60) as response:
        response_data = json.loads(response.read().decode("utf-8"))
    return str(response_data.get("reply", ""))


def run_bridge(server: str, poll_interval: float, token: Optional[str]) -> None:
    if sys.platform != "darwin":
        raise SystemExit("iMessage bridge is supported only on macOS")
    if not CHAT_DB_PATH.exists():
        raise SystemExit(f"Messages database not found at {CHAT_DB_PATH}")

    last_rowid = load_state()
    connection = sqlite3.connect(f"file:{CHAT_DB_PATH}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row

    try:
        while True:
            for item in fetch_messages(connection, last_rowid):
                rowid = item["rowid"]
                conversation_id = item["guid"]
                text = item["text"]

                try:
                    reply = post_to_backend(server, conversation_id, text, token)
                except Exception as exc:
                    print(f"[bridge] backend request failed: {exc}", file=sys.stderr)
                    continue

                if reply.strip():
                    try:
                        send_imessage(conversation_id, reply)
                    except subprocess.CalledProcessError as exc:
                        print(f"[bridge] failed to send via Messages: {exc}", file=sys.stderr)
                        continue

                last_rowid = rowid
                save_state(last_rowid)
            time.sleep(poll_interval)
    finally:
        connection.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Relay iMessage threads to OpenPoke")
    parser.add_argument(
        "--server",
        default=os.environ.get("OPENPOKE_BRIDGE_ENDPOINT", "http://localhost:8001/api/v1/bridge/imessage"),
        help="Bridge endpoint to post incoming messages",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=float(os.environ.get("OPENPOKE_BRIDGE_POLL", "1.5")),
        help="Polling interval in seconds",
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("OPENPOKE_BRIDGE_TOKEN"),
        help="Optional bearer token sent to the backend",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_bridge(args.server, args.poll_interval, args.token)


if __name__ == "__main__":
    main()
