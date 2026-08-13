import os
import time
import requests

def upload_to_gcs(local_file_path):
    """
    ローカルの動画/画像ファイルを Google Cloud Storage (GCS) バケットへ自動アップロードし、
    Meta (Instagram) API が直接ダウンロードできる公開URLを取得します。
    """
    bucket_name = os.environ.get("GCS_BUCKET_NAME")
    if not bucket_name:
        return None
        
    try:
        from google.cloud import storage
        cred_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if cred_file and not os.path.isabs(cred_file):
            cred_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), cred_file)
            
        if cred_file and os.path.exists(cred_file):
            client = storage.Client.from_service_account_json(cred_file)
        else:
            client = storage.Client()
            
        bucket = client.bucket(bucket_name)
        blob_name = f"reels/{os.path.basename(local_file_path)}"
        blob = bucket.blob(blob_name)
        
        print(f"📦 [GCSUploader] GCSバケット ({bucket_name}) へ転送中: {blob_name} ...")
        blob.upload_from_filename(local_file_path)
        
        public_url = f"https://storage.googleapis.com/{bucket_name}/{blob_name}"
        print(f"✨ [GCSUploader] アップロード完了！公開URL: {public_url}")
        return public_url
    except Exception as e:
        print(f"⚠️ [GCSUploader] GCSへの転送でエラーが発生しました: {e}")
        return None

class InstagramPublisher:
    def __init__(self):
        self.access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
        self.account_id = os.environ.get("INSTAGRAM_ACCOUNT_ID")
        self.api_version = "v19.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        
        if not self.access_token or not self.account_id:
            print("💡 [InstagramPublisher] APIキーまたはアカウントIDが未設定です。モックモードで動作します。")
            self.is_mock = True
        else:
            print("🚀 [InstagramPublisher] APIキーが検出されました。本番モードで動作します。")
            self.is_mock = False

    def publish_image(self, image_url, caption):
        """
        Instagramに画像を投稿する (Meta Graph API)
        """
        if self.is_mock:
            print(f"\n--- [Instagram API Mock] 画像の自動投稿シミュレーション ---")
            print(f"■ 投稿画像URL: {image_url}")
            print(f"■ キャプション:\n{caption}")
            print(f"---------------------------------------------------\n")
            return {"status": "success", "media_id": "mock_media_123456789"}

        # 1. コンテナの作成 (POST /ig_user_id/media)
        container_url = f"{self.base_url}/{self.account_id}/media"
        payload = {
            "image_url": image_url,
            "caption": caption,
            "access_token": self.access_token
        }
        
        try:
            print("1/2: メディアコンテナを作成中...")
            response = requests.post(container_url, data=payload, timeout=20)
            res_data = response.json()
            
            if response.status_code != 200:
                print(f"エラーが発生しました: {res_data}")
                return {"status": "failed", "error": res_data}
                
            creation_id = res_data.get("id")
            print(f"メディアコンテナ作成成功。Creation ID: {creation_id}")
            
            # 2. コンテナの公開 (POST /ig_user_id/media_publish)
            publish_url = f"{self.base_url}/{self.account_id}/media_publish"
            publish_payload = {
                "creation_id": creation_id,
                "access_token": self.access_token
            }
            
            print("2/2: Instagramにメディアを公開中...")
            pub_response = requests.post(publish_url, data=publish_payload, timeout=20)
            pub_data = pub_response.json()
            
            if pub_response.status_code == 200:
                media_id = pub_data.get("id")
                print(f"🎉 投稿に成功しました！ Media ID: {media_id}")
                return {"status": "success", "media_id": media_id}
            else:
                print(f"公開に失敗しました: {pub_data}")
                return {"status": "failed", "error": pub_data}
                
        except Exception as e:
            print(f"APIリクエスト中に例外が発生しました: {e}")
            return {"status": "error", "message": str(e)}

    def publish_reel(self, video_url, caption):
        """
        InstagramにReels(リール動画)を投稿する
        """
        if self.is_mock:
            print(f"\n--- [Instagram API Mock] リール動画の自動投稿シミュレーション ---")
            print(f"■ 投稿動画URL: {video_url}")
            print(f"■ キャプション:\n{caption}")
            print(f"----------------------------------------------------------\n")
            return {"status": "success", "media_id": "mock_reels_987654321"}

        # 1. リール動画コンテナの作成 (POST /ig_user_id/media with media_type=REELS)
        container_url = f"{self.base_url}/{self.account_id}/media"
        payload = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": self.access_token
        }
        
        try:
            print("1/3: リール動画コンテナを作成中...")
            response = requests.post(container_url, data=payload, timeout=20)
            res_data = response.json()
            
            if response.status_code != 200:
                print(f"コンテナ作成エラー: {res_data}")
                return {"status": "failed", "error": res_data}
                
            creation_id = res_data.get("id")
            print(f"リール動画コンテナ作成成功。Creation ID: {creation_id}")
            
            # 2. 動画処理が完了するまでポーリング
            # Instagramサーバーが動画を処理し終わるのを待つ必要があります
            status_url = f"{self.base_url}/{creation_id}"
            status_payload = {
                "fields": "status_code",
                "access_token": self.access_token
            }
            
            print("2/3: Instagram側での動画処理完了を待機中...")
            for attempt in range(10): # 最大10回(50秒)ポーリング
                time.sleep(5)
                status_res = requests.get(status_url, params=status_payload, timeout=10)
                status_data = status_res.json()
                status_code = status_data.get("status_code")
                
                print(f"待機中... 処理ステータス: {status_code}")
                if status_code == "FINISHED":
                    print("動画処理が完了しました！")
                    break
                elif status_code == "ERROR":
                    print("動画の処理中にエラーが発生しました。")
                    return {"status": "failed", "error": "Processing error on Instagram server"}
            else:
                print("タイムアウトしました。処理はバックグラウンドで継続している可能性があります。")
            
            # 3. リールの公開 (POST /ig_user_id/media_publish)
            publish_url = f"{self.base_url}/{self.account_id}/media_publish"
            publish_payload = {
                "creation_id": creation_id,
                "access_token": self.access_token
            }
            
            print("3/3: リール動画を公開中...")
            pub_response = requests.post(publish_url, data=publish_payload, timeout=20)
            pub_data = pub_response.json()
            
            if pub_response.status_code == 200:
                media_id = pub_data.get("id")
                print(f"🎉 リール動画の投稿に成功しました！ Media ID: {media_id}")
                return {"status": "success", "media_id": media_id}
            else:
                print(f"リールの公開に失敗しました: {pub_data}")
                return {"status": "failed", "error": pub_data}
                
        except Exception as e:
            print(f"リール投稿APIリクエスト中に例外が発生しました: {e}")
            return {"status": "error", "message": str(e)}

    def publish_story_video(self, video_url):
        """
        Instagram Stories (ストーリーズ) に動画を投稿する (Meta Graph API)
        """
        if self.is_mock:
            print(f"\n--- [Instagram API Mock] ストーリーズ動画の自動投稿シミュレーション ---")
            print(f"■ 投稿動画URL: {video_url}")
            print(f"----------------------------------------------------------\n")
            return {"status": "success", "media_id": "mock_story_video_987654321"}

        # 1. ストーリーズ動画コンテナの作成 (POST /ig_user_id/media with media_type=STORIES)
        container_url = f"{self.base_url}/{self.account_id}/media"
        payload = {
            "media_type": "STORIES",
            "video_url": video_url,
            "access_token": self.access_token
        }
        
        try:
            print("1/3: ストーリーズ動画コンテナを作成中...")
            response = requests.post(container_url, data=payload, timeout=20)
            res_data = response.json()
            
            if response.status_code != 200:
                print(f"コンテナ作成エラー: {res_data}")
                return {"status": "failed", "error": res_data}
                
            creation_id = res_data.get("id")
            print(f"ストーリーズ動画コンテナ作成成功。Creation ID: {creation_id}")
            
            # 2. 動画処理が完了するまでポーリング
            status_url = f"{self.base_url}/{creation_id}"
            status_payload = {
                "fields": "status_code",
                "access_token": self.access_token
            }
            
            print("2/3: Instagram側での動画処理完了を待機中...")
            for attempt in range(30):
                time.sleep(5)
                status_res = requests.get(status_url, params=status_payload, timeout=10)
                status_data = status_res.json()
                status_code = status_data.get("status_code")
                
                print(f"待機中... 処理ステータス: {status_code}")
                if status_code == "FINISHED":
                    print("動画処理が完了しました！")
                    break
                elif status_code == "ERROR":
                    print("動画の処理中にエラーが発生しました。")
                    return {"status": "failed", "error": "Processing error on Instagram server"}
            else:
                print("タイムアウトしました。処理はバックグラウンドで継続している可能性があります。")
            
            # 3. ストーリーズの公開 (POST /ig_user_id/media_publish)
            publish_url = f"{self.base_url}/{self.account_id}/media_publish"
            publish_payload = {
                "creation_id": creation_id,
                "access_token": self.access_token
            }
            
            print("3/3: ストーリーズ動画を公開中...")
            pub_response = requests.post(publish_url, data=publish_payload, timeout=20)
            pub_data = pub_response.json()
            
            if pub_response.status_code == 200:
                media_id = pub_data.get("id")
                print(f"🎉 ストーリーズ動画の投稿に成功しました！ Media ID: {media_id}")
                return {"status": "success", "media_id": media_id}
            else:
                print(f"ストーリーズの公開に失敗しました: {pub_data}")
                return {"status": "failed", "error": pub_data}
                
        except Exception as e:
            print(f"APIリクエスト中に例外が発生しました: {e}")
            return {"status": "error", "message": str(e)}

    def publish_story_image(self, image_url):
        """
        Instagram Stories (ストーリーズ) に静止画像を投稿する (Meta Graph API)
        """
        if self.is_mock:
            print(f"\n--- [Instagram API Mock] ストーリーズ画像の自動投稿シミュレーション ---")
            print(f"■ 投稿画像URL: {image_url}")
            print(f"----------------------------------------------------------\n")
            return {"status": "success", "media_id": "mock_story_image_123456789"}

        container_url = f"{self.base_url}/{self.account_id}/media"
        payload = {
            "media_type": "STORIES",
            "image_url": image_url,
            "access_token": self.access_token
        }
        
        try:
            print("1/2: ストーリーズ画像コンテナを作成中...")
            response = requests.post(container_url, data=payload, timeout=20)
            res_data = response.json()
            
            if response.status_code != 200:
                print(f"コンテナ作成エラー: {res_data}")
                return {"status": "failed", "error": res_data}
                
            creation_id = res_data.get("id")
            print(f"ストーリーズ画像コンテナ作成成功。Creation ID: {creation_id}")
            
            publish_url = f"{self.base_url}/{self.account_id}/media_publish"
            publish_payload = {
                "creation_id": creation_id,
                "access_token": self.access_token
            }
            
            print("2/2: ストーリーズ画像を公開中...")
            pub_response = requests.post(publish_url, data=publish_payload, timeout=20)
            pub_data = pub_response.json()
            
            if pub_response.status_code == 200:
                media_id = pub_data.get("id")
                print(f"🎉 ストーリーズ画像の投稿に成功しました！ Media ID: {media_id}")
                return {"status": "success", "media_id": media_id}
            else:
                print(f"ストーリーズの公開に失敗しました: {pub_data}")
                return {"status": "failed", "error": pub_data}
                
        except Exception as e:
            print(f"APIリクエスト中に例外が発生しました: {e}")
            return {"status": "error", "message": str(e)}

def publish_reel_to_instagram(video_path):
    """ローカル動画ファイルを GCS にアップロードし Instagram Stories へ公開する便利関数"""
    video_url = upload_to_gcs(video_path)
    if not video_url:
        print("❌ GCS へのアップロードに失敗しました。")
        return False
    publisher = InstagramPublisher()
    res = publisher.publish_story_video(video_url)
    return res.get("status") == "success"

if __name__ == "__main__":
    publisher = InstagramPublisher()
    sample_image = "https://images.unsplash.com/photo-1501854140801-50d01698950b?auto=format&fit=crop&w=1080&q=80"
    publisher.publish_image(sample_image, "これは自動投稿のテストです。 #馬川亭 #テスト")
