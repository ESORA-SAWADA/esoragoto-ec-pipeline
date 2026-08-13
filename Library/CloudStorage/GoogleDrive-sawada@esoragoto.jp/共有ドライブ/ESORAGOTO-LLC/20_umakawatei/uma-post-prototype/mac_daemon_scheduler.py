#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================
UMA-POST Mac ユーザー常駐高信頼スケジューラ (mac_daemon_scheduler.py)
--------------------------------------------------------------
- 定時投稿: 毎日の朝 07:00 / 昼 12:00 / 夕方 17:00 (予備5分前〜35分間 時間窓ガード)
- 夕方ライブ配信: 毎日変動する佐渡の「リアルタイム日没時刻」からちょうど1時間 (3600秒間) 配信
- 時間すり抜け完全防止ロジック: ネットワーク遅延等で分単位が飛んでも時間窓内で確実に自動発動
==============================================================
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

_cached_sunset_date = None
_cached_sunset_dt = None

def get_sado_sunset_time():
    """
    佐渡島（緯度:38.016, 経度:138.368）の本日の正確な日没時刻(JST)をオープンAPIから取得（1日1回キャッシュ）
    """
    global _cached_sunset_date, _cached_sunset_dt
    now_jst = datetime.now(JST)
    today_str = now_jst.strftime("%Y-%m-%d")

    if _cached_sunset_date == today_str and _cached_sunset_dt is not None:
        return _cached_sunset_dt

    try:
        ctx = ssl._create_unverified_context()
        url = "https://api.open-meteo.com/v1/forecast?latitude=38.016&longitude=138.368&daily=sunset&timezone=Asia%2FTokyo"
        res = urllib.request.urlopen(url, context=ctx, timeout=5).read()
        data = json.loads(res)
        sunset_iso = data["daily"]["sunset"][0] # 例: '2026-08-10T18:46'
        sunset_dt = datetime.fromisoformat(sunset_iso).replace(tzinfo=JST)
        _cached_sunset_date = today_str
        _cached_sunset_dt = sunset_dt
        log(f"🌅 [Daemon] 本日の佐渡の日没時刻を取得更新しました: {sunset_dt.strftime('%H:%M JST')}")
        return sunset_dt
    except Exception as e:
        log(f"⚠️ [Daemon] 日没API取得エラー。18:45にフォールバックします: {e}")
        default_dt = now_jst.replace(hour=18, minute=45, second=0, microsecond=0)
        _cached_sunset_date = today_str
        _cached_sunset_dt = default_dt
        return default_dt

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
    log("🌟 UMA-POST 高信頼時間窓ガード付き定時投稿＆変動日没ライブ常駐スケジューラーが起動いたしました。")
    executed_today = {}

    while True:
        now_jst = datetime.now(JST)
        today_key = now_jst.strftime("%Y-%m-%d")
        curr_h = now_jst.hour
        curr_m = now_jst.minute

        # 1. 本日の日没時刻のキャッシュ取得
        sunset_dt = get_sado_sunset_time()
        sunset_h = sunset_dt.hour
        sunset_m = sunset_dt.minute

        # 2. 定時投稿スケジュールのチェック (時間窓ガード: 開始分〜＋30分間 確実に捕捉)
        # 朝: 06:55 〜 07:30
        # 昼: 11:55 〜 12:30
        # 夕: 16:55 〜 17:30
        fixed_jobs = [
            {"start_h": 6, "start_m": 55, "end_h": 7, "end_m": 30, "mode": "morning"},
            {"start_h": 11, "start_m": 55, "end_h": 12, "end_m": 30, "mode": "afternoon"},
            {"start_h": 16, "start_m": 55, "end_h": 17, "end_m": 30, "mode": "evening"}
        ]

        curr_minutes_today = curr_h * 60 + curr_m

        for fj in fixed_jobs:
            start_mins = fj["start_h"] * 60 + fj["start_m"]
            end_mins = fj["end_h"] * 60 + fj["end_m"]

            if start_mins <= curr_minutes_today <= end_mins:
                key = f"{today_key}_{fj['mode']}"
                if key not in executed_today:
                    executed_today[key] = True
                    log(f"⏰ [Daemon] 時間窓枠 ({fj['start_h']}:{fj['start_m']:02d}〜) に到達。モード '{fj['mode']}' を実行します。")
                    execute_post_job(fj["mode"])

        # 3. 毎日変動する「日没時刻（Sunset Time）」でのライブ配信チェック (1時間 = 3600秒間配信)
        # 日没の5分前〜＋30分間の時間窓ガード
        sunset_start_mins = (sunset_h * 60 + sunset_m) - 5
        sunset_end_mins = sunset_start_mins + 35

        if sunset_start_mins <= curr_minutes_today <= sunset_end_mins:
            live_key = f"{today_key}_sunset_live"
            if live_key not in executed_today:
                executed_today[live_key] = True
                log(f"🌅 [Daemon] 日没時間窓到達 (日没: {sunset_h}:{sunset_m:02d})。マジックアワーライブ配信を開始します...")
                execute_sunset_live_job(duration_seconds=3600)

        # 4. ハイブリッド遠隔トリガーの二重監視
        try:
            from remote_trigger_watcher import check_and_execute_remote_trigger
            check_and_execute_remote_trigger()
        except Exception:
            pass

        try:
            from github_queue_watcher import check_github_queue
            check_github_queue()
        except Exception:
            pass

        time.sleep(15)

if __name__ == "__main__":
    main()
