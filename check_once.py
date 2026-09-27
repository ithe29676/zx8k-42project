#!/usr/bin/env python3
"""
Cityline ticket-release watcher - single-run version for GitHub Actions.

Runs ONE check, compares to the last saved snapshot (last_seen.json in
this repo), sends a Telegram message ONLY if the page changed, then exits.
GitHub Actions calls this on a schedule (see .github/workflows/watch.yml)
so it behaves like a continuous watcher without needing your own PC on.

Telegram bot credentials are read from environment variables (set as
GitHub repo secrets), NOT hardcoded here.
"""

import os
import json
import hashlib
import requests

from playwright.sync_api import sync_playwright

# ============ CONFIG ============

URL = "https://shows.cityline.com/tc/2027/babymonsterworldtour.html"
TOP_CHARACTERS_TO_WATCH = 3000
STATE_FILE = "last_seen.json"

# these come from GitHub Actions secrets (see README.md)
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# ============ end config ============


def fetch_rendered_text(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)
        text = page.inner_text("body")
        browser.close()
        return text


def load_last_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_state(snippet: str, digest: str):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"digest": digest, "snippet": snippet}, f, ensure_ascii=False, indent=2)


def send_telegram_message(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    # Telegram messages have a ~4096 character limit
    resp = requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text[:4000],
    }, timeout=30)
    resp.raise_for_status()


def main():
    last = load_last_state()
    full_text = fetch_rendered_text(URL)
    snippet = full_text[:TOP_CHARACTERS_TO_WATCH].strip()
    digest = hashlib.sha256(snippet.encode("utf-8")).hexdigest()

    if last is None:
        print("First run - saving baseline snapshot. No message sent.")
        save_state(snippet, digest)
        return

    if digest != last["digest"]:
        print("CHANGE DETECTED - sending Telegram message.")
        message = (
            f"🎟️ Cityline page changed! Check tickets now:\n{URL}\n\n"
            f"New content:\n{snippet[:1500]}"
        )
        send_telegram_message(message)
        save_state(snippet, digest)
    else:
        print("No change.")


if __name__ == "__main__":
    main()
