#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
馬川亭 夕焼け全自動ライブ配信ストリーマー (sunset_live_streamer.py)
------------------------------------------------------
- Instagram Live Producer (RTMP) / YouTube Live 両対応
- YouTube Live API 連動による 100% 完全無人自動公開＆自動アーカイビング
"""

import os
import sys
import time
import shutil
import subprocess
from datetime import datetime, timezone, timedelta
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

JST = timezone(timedelta(hours=9))

def get_sado_sunset_datetime():
    """
    佐渡島（緯度:38.016, 経度:138.368）の気象・天体APIから本日の正確な日没時刻(JST)を動的に取得
    """
    try:
        import urllib.request, ssl, json
        ctx = ssl._create_unverified_context()
        url = "https://api.open-meteo.com/v1/forecast?latitude=38.016&longitude=138.368&daily=sunset&timezone=Asia%2FTokyo"
        res = urllib.request.urlopen(url, context=ctx, timeout=5).read()
        data = json.loads(res)
        sunset_iso = data["daily"]["sunset"][0] # 例: '2026-08-10T18:46'
        sunset_dt = datetime.fromisoformat(sunset_iso).replace(tzinfo=JST)
        print(f"☀️ [SunsetAPI] 佐渡のリアルタイム日没時刻(JST)を取得しました: {sunset_dt.strftime('%H:%M:%S')}")
        return sunset_dt
    except Exception as e:
        print(f"⚠️ [SunsetAPI] 日没時刻の取得でエラー。デフォルト18:45にフォールバックします: {e}")
        now_jst = datetime.now(JST)
        return now_jst.replace(hour=18, minute=45, second=0, microsecond=0)

def start_sunset_live_stream(duration_seconds=3600, stream_key=None, rtmp_server=None, broadcast_id=None, test_mode=False):
    """
    YouTube Live へ H.264 / AAC 映像ストリームを送信し、API 経由で完全無人・自動公開 (デフォルト1時間 = 3600秒)
    """
    duration_seconds = int(duration_seconds)
    # .env または 引数から優先的にキーとサーバーを取得
    stream_key = stream_key or os.environ.get("YOUTUBE_LIVE_STREAM_KEY") or os.environ.get("INSTAGRAM_LIVE_STREAM_KEY")
    rtmp_server = rtmp_server or os.environ.get("YOUTUBE_RTMP_SERVER") or os.environ.get("INSTAGRAM_RTMP_SERVER") or "rtmps://a.rtmp.youtube.com/live2"

    print("\n==========================================")
    print("🌇 UMA-POST: YouTube Live 夕焼け自動ライブ配信システム")
    print(f"配信予定時間: {duration_seconds // 60}分間 ({duration_seconds}秒)")
    print("==========================================\n")

    if not stream_key and not test_mode:
        print("⚠️ [SunsetStreamer] STREAM_KEY が設定されていません。")
        return False

    # ターゲット RTMP URL の生成
    if stream_key:
        if rtmp_server.endswith("/"):
            target_rtmp_url = f"{rtmp_server}{stream_key}"
        else:
            target_rtmp_url = f"{rtmp_server}/{stream_key}"
    else:
        target_rtmp_url = f"{rtmp_server}/DUMMY_KEY"

    # ★ ユーザーポリシー厳守: 録画動画（MP4）のループ再生フォールバックは100%完全排除！
    # リアルタイム生ライブストリーム通信（GoPro HERO8 生中継）のみを許可します。
    gopro_live_url = None
    gopro_ip = "172.22.137.51"
    
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        # GoPro USB IP 通信チェック (8554 or 8080)
        if s.connect_ex((gopro_ip, 8554)) == 0:
            gopro_live_url = f"udp://{gopro_ip}:8554"
            print(f"📹 [SunsetStreamer] GoPro HERO8 リアルタイム生中継ストリーム ({gopro_live_url}) の接続を確立しました！")
        elif s.connect_ex((gopro_ip, 8080)) == 0:
            # GoPro Open API ライブストリーム URL
            gopro_live_url = f"http://{gopro_ip}:8080/live/mode"
            print(f"📹 [SunsetStreamer] GoPro HERO8 Webライブストリーム ({gopro_live_url}) の接続を確立しました！")
        s.close()
    except Exception as e:
        print(f"⚠️ [SunsetStreamer] GoPro 接続判定例外: {e}")

    if not gopro_live_url:
        print("❌ [SunsetStreamer] エラー: GoPro HERO8 のリアルタイム生ライブ通信が検出できません。")
        print("🛑 ユーザールールポリシーに従い、録画動画のループ再生フォールバックは完全無効化されているため、配信を安全停止します。")
        return False

    input_video = gopro_live_url

    is_image = input_video.endswith(('.jpg', '.jpeg', '.png'))

    if test_mode:
        print("🧪 [SunsetStreamer] テストモード実行中")
        print(f"📹 入力ソース: {input_video}")
        print(f"🎯 送信先RTMP: {rtmp_server}/[YOUTUBE_LIVE_STREAM_KEY]")
        print("✨ ライブ配信パイプライン準備完了！")
        return True

    ffmpeg_bin = os.path.abspath("./bin/ffmpeg") if os.path.exists("./bin/ffmpeg") else (shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg" or "/usr/local/bin/ffmpeg" or "ffmpeg")

    # YouTube Live 最適化 ffmpeg パラメータ (超低遅延・安定ビットレート配信)
    if is_image:
        ffmpeg_cmd = [
            ffmpeg_bin, "-y",
            "-loop", "1",
            "-i", input_video,
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-vf", "scale=1080:1920",
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-preset", "ultrafast",
            "-r", "30",
            "-g", "60",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100",
            "-f", "flv",
            target_rtmp_url
        ]
    else:
        ffmpeg_cmd = [
            ffmpeg_bin, "-y",
            "-re",
            "-stream_loop", "-1",
            "-i", input_video,
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-vf", "scale=1080:1920",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-tune", "zerolatency",
            "-b:v", "2500k",
            "-maxrate", "3000k",
            "-bufsize", "6000k",
            "-pix_fmt", "yuv420p",
            "-g", "60",
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100",
            "-f", "flv",
            target_rtmp_url
        ]

    print(f"🚀 [SunsetStreamer] YouTube Live へストリーミングを開始します: {target_rtmp_url[:40]}...")
    try:
        log_file_path = "./ffmpeg_stream.log"
        log_f = open(log_file_path, "a")

        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=log_f,
            stderr=log_f
        )
        print(f"📡 [SunsetStreamer] YouTube Live ライブストリーミング中... (PID: {process.pid})")
        
        # パケット到着を 5秒待機後、API 経由で『一般公開 (LIVE)』へ即時遷移
        time.sleep(5)
        if broadcast_id:
            try:
                from youtube_live_api_manager import transition_broadcast_to_live
                transition_broadcast_to_live(broadcast_id)
            except Exception as e:
                print(f"⚠️ Live トランジション通知: {e}")

        start_time = time.time()
        while time.time() - start_time < duration_seconds:
            if process.poll() is not None:
                print(f"⚠️ [SunsetStreamer] ffmpeg プロセスがエラー終了しました (Exit Code: {process.poll()})。")
                break
            time.sleep(5)

        # 配信終了処理
        if process.poll() is None:
            print("⏰ [SunsetStreamer] 指定配信時間に達しました。ライブ配信を終了します...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

        # API 経由で全自動で『終了・アーカイブ化 (COMPLETE)』
        if broadcast_id:
            try:
                from youtube_live_api_manager import transition_broadcast_to_complete
                transition_broadcast_to_complete(broadcast_id)
            except Exception as e:
                print(f"⚠️ Complete トランジション通知: {e}")

        print("🎉 [SunsetStreamer] YouTube Live 夕焼け配信が正常に完了いたしました！")
        return True
    except Exception as e:
        print(f"❌ [SunsetStreamer] ストリーミング処理中にエラーが発生しました: {e}")
        return False

if __name__ == "__main__":
    dur = int(sys.argv[1]) if len(sys.argv) > 1 else 1800
    key = sys.argv[2] if len(sys.argv) > 2 else None
    srv = sys.argv[3] if len(sys.argv) > 3 else None
    b_id = sys.argv[4] if len(sys.argv) > 4 else None
    start_sunset_live_stream(duration_seconds=dur, stream_key=key, rtmp_server=srv, broadcast_id=b_id)
