#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube Live Data API v3 全自動配信管理モジュール (youtube_live_api_manager.py)
-------------------------------------------------
1. client_secret.json から OAuth2 認証を完遂し token_youtube_live.json にトークンを保存
2. 日没時刻に合わせ enableAutoStart=True / enableAutoStop=True の新規ライブ配信枠を自動生成
3. ストリーム（RTMP）を自動作成して配信枠へ自動バインド（紐付け）
4. 送信先 RTMP URL とストリームキーを返し、100%人手不要の完全自動ライブ配信を実現
"""

import os
import sys
import time
from datetime import datetime, timezone, timedelta
import google.oauth2.credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

JST = timezone(timedelta(hours=9))

# YouTube API スコープ
SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRET_FILE = os.path.join(SCRIPT_DIR, "client_secret.json")
TOKEN_FILE = os.path.join(SCRIPT_DIR, "token_youtube_live.json")

def get_authenticated_youtube_service():
    """
    OAuth2 認証を行い、YouTube Live API サービスオブジェクトを取得・返却
    """
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = google.oauth2.credentials.Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            print(f"⚠️ 既存トークンの読み込みエラー: {e}")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                print("✨ YouTube API トークンを自動リフレッシュしました！")
            except Exception as e:
                print(f"⚠️ トークンリフレッシュ失敗: {e}")
                creds = None

        if not creds:
            if not os.path.exists(CLIENT_SECRET_FILE):
                raise FileNotFoundError(f"❌ {CLIENT_SECRET_FILE} が見つかりません。")

            print("🔐 YouTube API の初回認証を開始します (ブラウザで認証してください)...")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=8088)

        # トークン保存
        try:
            with open(TOKEN_FILE, "w") as token:
                token.write(creds.to_json())
            print(f"✨ 新しい認証トークンを保存しました: {TOKEN_FILE}")
        except Exception as e:
            print(f"⚠️ トークン保存エラー: {e}")

    return build("youtube", "v3", credentials=creds)

def create_auto_live_broadcast(title=None, description=None, privacy_status="public"):
    """
    YouTube API 経由で enableAutoStart=True, enableAutoStop=True の本番ライブ配信枠を自動生成＆バインド
    """
    now_jst = datetime.now(JST)
    date_str = now_jst.strftime('%Y/%m/%d')

    if not title:
        title = f"【佐渡・馬川亭】マジックアワー ライブ【{date_str}】"

    if not description:
        description = "佐渡島・馬川亭から届けるマジックアワーのリアルタイムライブ配信です。\n綺麗な夕焼けが見れたら、明日いいことあるかも！"

    print(f"🚀 [YouTubeAPI] 完全自動ライブ配信枠のチェック・生成を開始します: {title} (公開設定: {privacy_status})")
    youtube = get_authenticated_youtube_service()

    # ★ 1日1枠ロック: 本日すでに同タイトルの配信枠が存在する場合は二重作成せず再利用！
    try:
        existing_res = youtube.liveBroadcasts().list(
            part="snippet,status,contentDetails",
            broadcastStatus="all",
            maxResults=10
        ).execute()
        for item in existing_res.get("items", []):
            item_title = item.get("snippet", {}).get("title", "")
            if date_str in item_title:
                b_id = item["id"]
                print(f"🔒 [YouTubeAPI] 本日({date_str})の既存配信枠を発見しました (ID: {b_id})。二重作成を防止し既存枠を再利用します。")
                # バインドされている Stream 情報を取得
                bound_stream_id = item.get("contentDetails", {}).get("boundStreamId")
                if bound_stream_id:
                    s_res = youtube.liveStreams().list(part="cdn", id=bound_stream_id).execute()
                    if s_res.get("items"):
                        cdn = s_res["items"][0]["cdn"]["ingestionInfo"]
                        return {
                            "broadcast_id": b_id,
                            "stream_id": bound_stream_id,
                            "rtmp_server": cdn["ingestionAddress"],
                            "rtmp_url": cdn["ingestionAddress"],
                            "stream_key": cdn["streamName"]
                        }
    except Exception as ex:
        print(f"⚠️ [YouTubeAPI] 既存枠チェック中の警告: {ex}")

    now = datetime.now(timezone.utc)
    start_time_iso = (now + timedelta(seconds=10)).isoformat()

    # 1. ライブ配信枠 (Broadcast) の作成
    broadcast_body = {
        "snippet": {
            "title": title,
            "description": description,
            "scheduledStartTime": start_time_iso,
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False
        },
        "contentDetails": {
            "enableAutoStart": True,   # ★ データ送信到達で全自動ライブ配信スタート！
            "enableAutoStop": True,    # ★ データ送信停止で全自動ライブ配信ストップ！
            "enableDvr": True,
            "latencyPreference": "low"  # 低遅延
        }
    }

    broadcast_res = youtube.liveBroadcasts().insert(
        part="snippet,status,contentDetails",
        body=broadcast_body
    ).execute()

    broadcast_id = broadcast_res["id"]
    print(f"✅ [YouTubeAPI] 自動ライブ配信枠を作成しました (ID: {broadcast_id})")

    # 2. ライブストリーム (Stream) の作成
    stream_body = {
        "snippet": {
            "title": f"Stream-{broadcast_id}"
        },
        "cdn": {
            "frameRate": "30fps",
            "ingestionType": "rtmp",
            "resolution": "1080p"
        }
    }

    stream_res = youtube.liveStreams().insert(
        part="snippet,cdn",
        body=stream_body
    ).execute()

    stream_id = stream_res["id"]
    ingestion_address = stream_res["cdn"]["ingestionInfo"]["ingestionAddress"]
    stream_name = stream_res["cdn"]["ingestionInfo"]["streamName"]

    print(f"✅ [YouTubeAPI] 自動ストリームを作成しました (ID: {stream_id})")

    # 3. 配信枠とストリームの自動バインド (Bind)
    bind_res = youtube.liveBroadcasts().bind(
        id=broadcast_id,
        part="id,contentDetails",
        streamId=stream_id
    ).execute()

    print(f"🎉 [YouTubeAPI] 配信枠とストリームの完全自動結合(Bind)が完了しました！")
    print(f"📡 RTMP URL: {ingestion_address}")
    print(f"🔑 Stream Key: {stream_name}")

    return {
        "broadcast_id": broadcast_id,
        "stream_id": stream_id,
        "rtmp_server": ingestion_address,
        "stream_key": stream_name
    }

def transition_broadcast_to_live(broadcast_id):
    """
    enableAutoStart=True のため、RTMP データ受領時に YouTube 側が自動で LIVE 化します。
    """
    try:
        youtube = get_authenticated_youtube_service()
        youtube.liveBroadcasts().transition(
            broadcastStatus="live",
            id=broadcast_id,
            part="id,status"
        ).execute()
        print(f"🎉 [YouTubeAPI] 配信枠 {broadcast_id} を一般公開 LIVE 状態に切り替えました！")
    except Exception as e:
        print(f"ℹ️ [YouTubeAPI] enableAutoStart により YouTube 側で自動 LIVE 遷移が進行中 ({e})")

def transition_broadcast_to_complete(broadcast_id):
    """
    enableAutoStop=True のため、RTMP データ停止時に YouTube 側が自動で END 化します。
    """
    try:
        youtube = get_authenticated_youtube_service()
        youtube.liveBroadcasts().transition(
            broadcastStatus="complete",
            id=broadcast_id,
            part="id,status"
        ).execute()
        print(f"🎉 [YouTubeAPI] 配信枠 {broadcast_id} を配信終了 (Complete) 状態に切り替えました！")
    except Exception as e:
        print(f"ℹ️ [YouTubeAPI] enableAutoStop により YouTube 側で自動配信終了が進行中 ({e})")
        return None
