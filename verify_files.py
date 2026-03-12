#!/usr/bin/env python3
"""
Verify important files daily: compute hashes, compare with VerifyFile,
report changes via Telegram. Run at 1am via cron or systemd timer.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlencode

# Default paths (relative to script directory)
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = SCRIPT_DIR / "config.json"
DEFAULT_VERIFY_FILE = SCRIPT_DIR / "VerifyFile"


def load_config(config_path: Path) -> dict:
    """Load JSON config: important_files (list of {path, label}), telegram_bot_token, telegram_chat_id."""
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_verify_file(verify_path: Path) -> dict:
    """Load VerifyFile: returns dict path -> hash. Empty if file missing or empty."""
    if not verify_path.exists():
        return {}
    out = {}
    with open(verify_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "|" not in line:
                continue
            parts = line.split("|", 1)
            if len(parts) == 2:
                path, h = parts[0].strip(), parts[1].strip()
                if path and h:
                    out[path] = h
    return out


def save_verify_file(verify_path: Path, path_to_hash: dict) -> None:
    """Write VerifyFile: one line per path as path|hash."""
    with open(verify_path, "w", encoding="utf-8") as f:
        for path in sorted(path_to_hash):
            f.write(f"{path}|{path_to_hash[path]}\n")


def file_hash(file_path: Path) -> Optional[str]:
    """Compute SHA256 hash of file. Returns None if file missing or unreadable."""
    if not file_path.exists() or not file_path.is_file():
        return None
    try:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def normalize_path(p: str) -> str:
    """Normalize path for consistent key in VerifyFile."""
    return str(Path(p).resolve())


def send_telegram_message(token: str, chat_id: str, text: str) -> bool:
    """Send text to Telegram via Bot API. Returns True on success."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = urlencode({"chat_id": chat_id, "text": text, "parse_mode": "HTML"}).encode("utf-8")
    req = Request(url, data=body, method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except (URLError, HTTPError, OSError):
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify important files and notify via Telegram.")
    parser.add_argument("--config", "-c", type=Path, default=DEFAULT_CONFIG, help="Config JSON path")
    parser.add_argument("--verify-file", "-v", type=Path, default=DEFAULT_VERIFY_FILE, help="VerifyFile path")
    parser.add_argument("--dry-run", action="store_true", help="Do not update VerifyFile or send Telegram")
    args = parser.parse_args()

    if not args.config.exists():
        print(f"Config not found: {args.config}", file=sys.stderr)
        return 1

    config = load_config(args.config)
    files_config = config.get("important_files") or []
    bot_token = (config.get("telegram_bot_token") or "").strip()
    chat_id = (config.get("telegram_chat_id") or "").strip()

    if not files_config:
        print("No important_files in config.", file=sys.stderr)
        return 1

    path_to_label = {}
    for item in files_config:
        path = item.get("path") or item.get("file")
        label = item.get("label") or path or "(unnamed)"
        if path:
            path_to_label[normalize_path(path)] = label

    previous = load_verify_file(args.verify_file)
    current_hashes = {}
    changed = []  # list of (label, path, status)  status: "new" or "changed"

    for path_str, label in path_to_label.items():
        path = Path(path_str)
        new_hash = file_hash(path)
        if new_hash is None:
            if path_str in previous and previous[path_str]:
                changed.append((label, path_str, "missing"))
            # Keep previous hash in VerifyFile for missing files (don't overwrite)
            if path_str in previous:
                current_hashes[path_str] = previous[path_str]
            continue
        current_hashes[path_str] = new_hash
        if path_str not in previous or not previous[path_str]:
            changed.append((label, path_str, "new"))
        elif previous[path_str] != new_hash:
            changed.append((label, path_str, "changed"))

    if not args.dry_run:
        save_verify_file(args.verify_file, current_hashes)

    if not changed:
        if not args.dry_run and bot_token and chat_id:
            send_telegram_message(bot_token, chat_id, "✅ File verify: no changes detected.")
        return 0

    lines = ["📋 <b>File verify – changes detected</b>\n"]
    for label, path_str, status in changed:
        if status == "new":
            lines.append(f"• <b>{label}</b> (new)\n  <code>{path_str}</code>")
        elif status == "changed":
            lines.append(f"• <b>{label}</b> (changed)\n  <code>{path_str}</code>")
        else:
            lines.append(f"• <b>{label}</b> (missing)\n  <code>{path_str}</code>")
    message = "\n".join(lines)

    if args.dry_run:
        print(message)
        return 0

    if bot_token and chat_id:
        if send_telegram_message(bot_token, chat_id, message):
            return 0
        print("Failed to send Telegram message.", file=sys.stderr)
        return 1
    else:
        print(message)
        return 0


if __name__ == "__main__":
    sys.exit(main())
