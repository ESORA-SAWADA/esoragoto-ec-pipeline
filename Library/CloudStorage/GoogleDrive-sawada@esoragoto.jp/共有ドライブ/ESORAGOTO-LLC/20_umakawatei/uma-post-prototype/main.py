#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==================================================
🌄 UMA-POST: 馬川亭 デイリーSNS自動投稿メインエンジン (main.py)
==================================================
機能:
 1. リアルタイム天気 (Open-Meteo API) & カレンダー連携 (Google Calendar API) からコンテンツを自動取得
 2. 02_デイリー動画素材 から現場の最新 GoPro タイムラプス動画を第一優先で補獲
 3. 直立/縦型動画の上に透明なテロップスタンプ(お天気+ロゴ+コピー)を合成
 4. Instagram Stories (ストーリーズ) へ自動配信 & GCSに保存
 5. 動画がない場合のみ、馬川亭の店舗外観ストック写真(live_sample_base.jpg)で安全フォールバック
==================================================
"""

import os
import sys
import argparse
import time
from datetime import datetime, timezone, timedelta

# ローカルモジュールのインポート
from video_compositor import (
    find_latest_gopro_video,
    composite_post_image,
    overlay_stamp_on_video,
    convert_image_to_reel_video,
    is_image_or_video_black
)
from calendar_integrator import get_google_calendar_events
from morning_post_generator import generate_morning_post
from instagram_publisher import publish_reel_to_instagram
import sunset_detector
import youtube_live_api_manager
import sunset_live_streamer

JST = timezone(timedelta(hours=9))

def get_fallback_stock_photo():
    """動画未検出時の安全フォールバック用：馬川亭の店舗外観ベース画像"""
    base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "live_sample_base.jpg")
    if os.path.exists(base_path):
        return base_path
    daily_photo_dir = os.path.abspath("../07_アセット/01_デイリー写真")
    if os.path.exists(daily_photo_dir):
        import glob
        photos = glob.glob(os.path.join(daily_photo_dir, "*.jpg")) + glob.glob(os.path.join(daily_photo_dir, "*.png"))
        if photos:
            return max(photos, key=os.path.getmtime)
    return base_path

def main():
    parser = argparse.ArgumentParser(description="UMA-POST デイリーリール投稿エンジン")
    parser.add_argument("--mode", choices=["morning", "afternoon", "evening"], default="morning", help="投稿モード (morning/afternoon/evening)")
    args = parser.parse_args()
    mode = args.mode

    print(f"==========================================")
    print(f"🌄 UMA-POST: デイリーリール投稿フローを開始 (モード: {mode})")
    print(f"==========================================")

    # STEP 1: 天気 & カレンダー情報の自動解析
    print("\n[STEP 1/4] 天気・イベントの自動解析とGeminiによるコンテンツ生成...")
    weather_fetched = sunset_detector.get_sunset_info()
    weather_status = weather_fetched.get("weather", "晴れ")
    weather_temp = str(weather_fetched.get("current_temp", weather_fetched.get("max_temp", "27")))

    # Google カレンダーイベントの取得
    events_summary = get_google_calendar_events()
    
    # Gemini による投稿文章・見出しの自動生成
    title, subtitle, message = generate_morning_post()

    # STEP 2: 02_デイリー動画素材 から GoPro タイムラプス動画を第一優先で探索
    print("\n[STEP 2/4] 02_デイリー動画素材 (GoProタイムラプス動画) を第一優先スキャン中...")
    gopro_video = find_latest_gopro_video(mode=mode)
    reel_video_path = None

    if gopro_video and os.path.exists(gopro_video):
        print(f"🎥 [VideoCompositor] 最新のGoProタイムラプス動画を補獲しました！: {os.path.basename(gopro_video)}")
        
        # 透過スタンプ(お天気+ロゴ+テロップ)画像を生成
        temp_stamp_path = composite_post_image(
            base_image_path="TRANSPARENT_STAMP",
            text_title=title,
            text_subtitle=subtitle,
            text_message=f"「{message}」",
            theme_color="warm-gold",
            mode=mode,
            weather_temp=weather_temp,
            weather_status=weather_status
        )
        
        # GoPro動画の上に透過スタンプをFFmpegで15秒間重ね合わせて最新リール動画を自動合成
        print("\n[STEP 3/4] GoPro動画にテロップスタンプを動画合成中...")
        reel_video_path = overlay_stamp_on_video(gopro_video, temp_stamp_path, "latest_reel_video.mp4")
        
        if temp_stamp_path and os.path.exists(temp_stamp_path):
            try:
                os.remove(temp_stamp_path)
            except Exception:
                pass

    # STEP 3: GoPro動画が無い、または動画合成で黒画面障害が発生した場合の安全自動フォールバック
    if not reel_video_path or is_image_or_video_black(reel_video_path):
        print("💡 [VideoCompositor] GoPro動画未検出または黒画面障害を検知。馬川亭外観写真ベース動画へ安全自動フォールバックします。")
        stock_photo = get_fallback_stock_photo()
        composite_image_path = composite_post_image(
            base_image_path=stock_photo,
            text_title=title,
            text_subtitle=subtitle,
            text_message=f"「{message}」",
            theme_color="warm-gold",
            mode=mode,
            weather_temp=weather_temp,
            weather_status=weather_status
        )
        reel_video_path = convert_image_to_reel_video(composite_image_path, "latest_reel_video.mp4")

    # STEP 4: Instagram Stories への自動配信
    print("\n[STEP 4/4] Instagram Storiesへの自動配信と後処理を実行...")
    if reel_video_path and os.path.exists(reel_video_path):
        success = publish_reel_to_instagram(reel_video_path)
        if success:
            print("🎉 Instagram Stories 投稿成功！")
        else:
            print("⚠️ Instagram Stories 投稿処理で警告が発生しました。")
    else:
        print("❌ 投稿対象のリール動画の生成に失敗しました。")

    # STEP 5: 夕方モード時の YouTube Live トリガー
    if mode == "evening":
        print("\n[STEP 5/5] 🌇 YouTube Live マジックアワー全自動配信をトリガー中...")
        try:
            sunset_live_streamer.start_sunset_live_stream(duration_seconds=3600, test_mode=False)
        except Exception as ex:
            print(f"⚠️ [YouTubeLive] マジックアワー配信トリガー例外: {ex}")

    print(f"\n==========================================")
    print(f"🎉 デイリーストーリーズ投稿フロー({mode})が正常に完了しました！")
    print(f"==========================================")

if __name__ == "__main__":
    main()
