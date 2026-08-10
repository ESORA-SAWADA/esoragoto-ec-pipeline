#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UMA-POST GitHub クラウド指示キュー監視モジュール (github_queue_watcher.py)
---------------------------------------------------------------------
- Google Drive 共有ファイル（ルートA）に加え、GitHub プライベートリポジトリの Issue / Release / Workflow / API 指示キュー（ルートB）を二重化監視
- iMac ↔ MacBook Air 間で 100% 途切れない『ハイブリッド遠隔トリガー』を実現
"""

import os
import sys
import json
import urllib.request
import ssl
import subprocess
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GITHUB_REPO = "ESORA-SAWADA/esoragoto-ec-pipeline"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

def check_github_queue():
    """
    GitHub API 経由で 'remote-command' ラベルの付いた Issue 指示キューを監視＆実行
    """
    if not GITHUB_TOKEN:
        return

    try:
        ctx = ssl._create_unverified_context()
        url = f"https://api.github.com/repos/{GITHUB_REPO}/issues?labels=remote-command&state=open"
        req = urllib.request.Request(url, headers={
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "UMA-POST-MacBookAir"
        })
        res = urllib.request.urlopen(req, context=ctx, timeout=5).read()
        issues = json.loads(res)

        for issue in issues:
            body = issue.get("body", "").strip()
            issue_number = issue.get("number")
            print(f"🐙 [GitHubQueue] GitHub クラウド指示キューを検知しました (Issue #{issue_number}): {body}")

            # コマンド解析
            cmd_type = None
            if "morning" in body.lower():
                cmd_type = "morning"
            elif "afternoon" in body.lower():
                cmd_type = "afternoon"
            elif "evening" in body.lower():
                cmd_type = "evening"
            elif "sunset_live" in body.lower() or "live" in body.lower():
                cmd_type = "sunset_live"

            if cmd_type:
                if cmd_type in ["morning", "afternoon", "evening"]:
                    cmd = [sys.executable, os.path.join(SCRIPT_DIR, "main.py"), "--mode", cmd_type]
                    subprocess.run(cmd, cwd=SCRIPT_DIR)
                elif cmd_type == "sunset_live":
                    cmd = [sys.executable, os.path.join(SCRIPT_DIR, "sunset_live_streamer.py"), "3600"]
                    subprocess.run(cmd, cwd=SCRIPT_DIR)

            # Issue を Close 処理して二重実行を防止
            close_url = f"https://api.github.com/repos/{GITHUB_REPO}/issues/{issue_number}"
            close_req = urllib.request.Request(close_url, data=json.dumps({"state": "closed"}).encode("utf-8"), headers={
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json",
                "User-Agent": "UMA-POST-MacBookAir"
            }, method="PATCH")
            urllib.request.urlopen(close_req, context=ctx, timeout=5)
            print(f"✅ [GitHubQueue] Issue #{issue_number} をクローズし、処理完了しました！")

    except Exception as e:
        pass

if __name__ == "__main__":
    check_github_queue()
