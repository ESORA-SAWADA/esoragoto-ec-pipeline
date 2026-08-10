#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UMA-POST Mac ユーザー常駐高信頼スケジューラ (mac_daemon_scheduler.py)
--------------------------------------------------------------
- 定時投稿: 毎日の朝 07:00 / 昼 12:00 / 夕方 17:00 (予備5分前トリガー)
- 夕方ライブ配信: 毎日変動する佐渡の「リアルタイム日没時刻」からちょうど1時間 (3600秒間) 配信
"""

import os
import sys
import time
import subprocess
import urllib.request
import ssl
import json
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def log(msg):
    now_str = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")
    line = f"[{now_str}] {msg}\n"
    print(line, end="", flush=True)
    with open(os.path.join(SCRIPT_DIR, "mac_daemon.log"), "a", encoding="utf-8") as f:
        f.write(line)

def get_sado_sunset_time():
    """
    佐渡島（緯度:38.016, 経度:138.368）の本日の正確な日没時刻(JST)をオープンAPIから取得
    """
    try:
        ctx = ssl._create_unverified_context()
        url = "https://api.open-meteo.com/v1/forecast?latitude=38.016&longitude=138.368&daily=sunset&timezone=Asia%2FTokyo"
        res = urllib.request.urlopen(url, context=ctx, timeout=5).read()
        data = json.loads(res)
        sunset_iso = data["daily"]["sunset"][0] # 例: '2026-08-10T18:46'
        sunset_dt = datetime.fromisoformat(sunset_iso).replace(tzinfo=JST)
        return sunset_dt
    except Exception as e:
        log(f"⚠️ [Daemon] 日没API取得エラー。18:45にフォールバックします: {e}")
        now_jst = datetime.now(JST)
        return now_jst.replace(hour=18, minute=45, second=0, microsecond=0)

def execute_post_job(mode):
    log(f"🚀 [Daemon] 定時投稿 (モード: '{mode}') を実行中...")
    cmd = [sys.executable, os.path.join(SCRIPT_DIR, "main.py"), "--mode", mode]
    try:
        res = subprocess.run(cmd, cwd=SCRIPT_DIR, capture_output=True, text=True, timeout=1800)
        log(f"✅ [Daemon] 投稿実行完了 (Exit Code: {res.returncode})")
    except Exception as e:
        log(f"❌ [Daemon] 投稿実行例外エラー: {e}")

def execute_sunset_live_job(duration_seconds=3600):
    log(f"🌇 [Daemon] 変動日没時刻のマジックアワーライブ配信 (時間: {duration_seconds//60}分間) を実行中...")
    cmd = [sys.executable, os.path.join(SCRIPT_DIR, "sunset_live_streamer.py"), str(duration_seconds)]
    try:
        res = subprocess.run(cmd, cwd=SCRIPT_DIR, capture_output=True, text=True, timeout=duration_seconds + 300)
        log(f"✅ [Daemon] マジックアワーライブ配信完了 (Exit Code: {res.returncode})")
    except Exception as e:
        log(f"❌ [Daemon] ライブ配信実行例外エラー: {e}")

def main():
    log("🌟 UMA-POST 定時投稿(07:00/12:00/17:00) ＆ 変動日没1時間ライブ常駐スケジューラーが起動いたしました。")
    executed_today = {}

    while True:
        now_jst = datetime.now(JST)
        today_key = now_jst.strftime("%Y-%m-%d")
        curr_h = now_jst.hour
        curr_m = now_jst.minute

        # 1. 毎朝 06:55 に本日分の日没時間を動的に取得更新
        sunset_dt = get_sado_sunset_time()
        sunset_h = sunset_dt.hour
        sunset_m = sunset_dt.minute

        # 2. 定時投稿スケジュールのチェック (07:00 / 12:00 / 17:00 予備5分前トリガー)
        fixed_jobs = [
            {"hour": 6, "minute": 55, "mode": "morning"},
            {"hour": 11, "minute": 55, "mode": "afternoon"},
            {"hour": 16, "minute": 55, "mode": "evening"}
        ]

        for fj in fixed_jobs:
            if curr_h == fj["hour"] and curr_m == fj["minute"]:
                key = f"{today_key}_{fj['mode']}"
                if key not in executed_today:
                    executed_today[key] = True
                    execute_post_job(fj["mode"])

        # 3. 毎日変動する「日没時刻（Sunset Time）」でのライブ配信チェック (1時間 = 3600秒間配信)
        # 日没の5分前に自動ストリーミング準備開始
        pre_sunset_m = (sunset_m - 5) % 60
        pre_sunset_h = sunset_h if sunset_m >= 5 else sunset_h - 1

        if curr_h == pre_sunset_h and curr_m == pre_sunset_m:
            live_key = f"{today_key}_sunset_live"
            if live_key not in executed_today:
                executed_today[live_key] = True
                log(f"🌅 本日の佐渡の日没時刻 ({sunset_h}:{sunset_m:02d}) を検出！ 日没から1時間(3600秒)のライブ配信を全自動で開始します...")
                execute_sunset_live_job(duration_seconds=3600)

        # 4. ハイブリッド遠隔トリガーの二重監視
        # ルートA: Google Drive クラウド共有ファイル (remote_trigger.json)
        try:
            from remote_trigger_watcher import check_and_execute_remote_trigger
            check_and_execute_remote_trigger()
        except Exception:
            pass

        # ルートB: GitHub クラウド指示キュー (GitHub API / Issue Queue)
        try:
            from github_queue_watcher import check_github_queue
            check_github_queue()
        except Exception:
            pass

        time.sleep(15)

if __name__ == "__main__":
    main()
