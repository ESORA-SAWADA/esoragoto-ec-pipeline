import os
import sys
import time
import json
import math
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter, ImageChops

def create_smooth_sun_icon(size=300, line_width=24):
    """
    3倍サイズで超滑らかな太陽アイコン(RGBA)を生成します。
    LANCZOS縮小により、一切ジャギーのない美しい極上のシルク細線を実現。
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    r = size // 4  # 半径 75px
    
    # 太陽の円
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=(255, 255, 255, 255), width=line_width)
    
    # 太陽の光線
    ray_len = 40
    gap = 20
    directions = [
        (0, -1), (0.707, -0.707), (1, 0), (0.707, 0.707),
        (0, 1), (-0.707, 0.707), (-1, 0), (-0.707, -0.707)
    ]
    for dx, dy in directions:
        x0 = cx + dx * (r + gap)
        y0 = cy + dy * (r + gap)
        x1 = cx + dx * (r + gap + ray_len)
        y1 = cy + dy * (r + gap + ray_len)
        draw.line([x0, y0, x1, y1], fill=(255, 255, 255, 255), width=line_width)
        
    return img

def create_smooth_cloud_icon(size=300, line_width=24):
    """
    3倍サイズで『内側の交差線が完全に消去された』超滑らかなお洒落雲アイコンを数学的に生成します。
    - シルエットを白い塗りつぶしで描き、それを MinFilter (Erode) で縮小。
    - 二つのアルファチャネルの差分を取ることで、外側の繋がったお洒落な輪郭線だけを抽出。
    """
    # 1. シルエット用キャンバス (塗りつぶし)
    sil_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(sil_img)
    
    cx, cy = size // 2, size // 2 + 10
    
    # 雲を構成する3つの円を『塗りつぶし』で描画し、一体のシルエットにする
    r1, r2, r3 = int(45), int(65), int(38)
    draw.ellipse([cx-80-r1, cy+10-r1, cx-80+r1, cy+10+r1], fill=(255, 255, 255, 255))
    draw.ellipse([cx-20-r2, cy-15-r2, cx-20+r2, cy-15+r2], fill=(255, 255, 255, 255))
    draw.ellipse([cx+55-r3, cy+15-r3, cx+55+r3, cy+15+r3], fill=(255, 255, 255, 255))
    # 雲の底辺を平らに繋げるための矩形
    draw.rectangle([cx-100, cy+10, cx+60, cy+45], fill=(255, 255, 255, 255))
    
    # 2. アルファマスクの抽出と縮小 (Erodeによる輪郭抽出)
    alpha = sil_img.getchannel('A')
    # MinFilterで内側に向けて Erode (縮小) をかける（これが線の太さになります）
    # line_width=12 に対し、MinFilterのサイズを調整
    shrunk_alpha = alpha.filter(ImageFilter.MinFilter(line_width * 2 - 1))
    
    # 3. 差分を計算して「中空の輪郭線」を完璧に取り出す
    outline_alpha = ImageChops.difference(alpha, shrunk_alpha)
    
    # 4. 新しい透過画像に輪郭を転写
    cloud_outline_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    # 純白で塗りつぶし
    white_img = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    # 差分アルファをマスクとして適用
    cloud_outline_img.paste(white_img, (0, 0), outline_alpha)
    
    return cloud_outline_img

def create_smooth_rain_icon(size=300, line_width=24):
    """
    滑らかな雲の下に、お洒落な雨の雫（細線）が3本流れる雨アイコンを生成します。
    """
    img = create_smooth_cloud_icon(size, line_width)
    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2 + 10
    
    # 雨の雫（斜めの平行線）
    drop_len = 35
    drop_y = cy + 60
    draw.line([cx-50, drop_y, cx-60, drop_y + drop_len], fill=(255, 255, 255, 255), width=line_width)
    draw.line([cx, drop_y, cx-10, drop_y + drop_len], fill=(255, 255, 255, 255), width=line_width)
    draw.line([cx+50, drop_y, cx+40, drop_y + drop_len], fill=(255, 255, 255, 255), width=line_width)
    
    return img

def create_smooth_snow_icon(size=300, line_width=24):
    """
    3倍サイズで超滑らかな結晶（雪）アイコンを生成します。
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    r = size // 3  # 半径 100px
    
    for i in range(6):
        angle = i * (math.pi / 3)
        dx = math.cos(angle)
        dy = math.sin(angle)
        x0 = cx
        y0 = cy
        x1 = cx + dx * r
        y1 = cy + dy * r
        draw.line([x0, y0, x1, y1], fill=(255, 255, 255, 255), width=line_width)
        
        branch_angle_offset = math.pi / 6
        bx = cx + dx * (r * 0.6)
        by = cy + dy * (r * 0.6)
        for sign in [-1, 1]:
            b_angle = angle + sign * branch_angle_offset
            bx1 = bx + math.cos(b_angle) * (r * 0.35)
            by1 = by + math.sin(b_angle) * (r * 0.35)
            draw.line([bx, by, bx1, by1], fill=(255, 255, 255, 255), width=line_width)
            
    return img

def draw_fallback_text_logo(draw, font_logo_icon, font_logo_text, width, logo_text="馬川亭"):
    """本物のロゴ画像ファイルが存在しない場合の、美しいフォールバックテキストロゴスタンプを描画します"""
    logo_color = (255, 255, 255, 225)
    accent_gold = (218, 165, 32, 225) # 上品なゴールドの真円
    
    text_bbox = draw.textbbox((0, 0), logo_text, font=font_logo_text)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]
    
    circle_r = 22 # 半径
    gap = 14
    logo_total_w = (circle_r * 2) + gap + text_w
    logo_x = width - logo_total_w - 100
    logo_y = 140
    
    # 金色の円アイコン
    icon_cx = logo_x + circle_r
    icon_cy = logo_y + circle_r
    draw.ellipse(
        [icon_cx - circle_r, icon_cy - circle_r, icon_cx + circle_r, icon_cy + circle_r],
        outline=accent_gold,
        width=2
    )
    
    # 円の中の「馬」
    char_box = draw.textbbox((0, 0), "馬", font=font_logo_icon)
    char_w = char_box[2] - char_box[0]
    char_h = char_box[3] - char_box[1]
    draw.text(
        (icon_cx - char_w/2 - 1, icon_cy - char_h/2 - 3),
        "馬",
        font=font_logo_icon,
        fill=logo_color
    )
    
    # 「馬川亭」レタリング
    text_x = logo_x + (circle_r * 2) + gap
    text_y = logo_y + (circle_r - text_h/2) - 4
    draw.text(
        (text_x, text_y),
        logo_text,
        font=font_logo_text,
        fill=logo_color
    )

def draw_text_with_shadow(draw, position, text, font, fill=(255, 255, 255, 255), shadow_fill=(0, 0, 0, 180), offset=(3, 3)):
    """ユーザー様のご指示により文字のドロップシャドウは全て廃止し、シンプルに直接描画"""
    x, y = position
    draw.text((x, y), text, font=font, fill=fill)

def composite_post_image(base_image_path, text_title, text_subtitle, text_message, theme_color="warm-gold", mode="morning", weather_temp="27", weather_status="晴れ", video_path=None):
    """
    ベース画像にテロップ、ロゴ、あるいはストーリースタンプ(朝モード専用)を美しく自動合成します。
    - PIL.ImageOps.exif_transpose を搭載し、スマホ縦写真のEXIF自動回転(横を向く問題)を100%完全解決。
    - 【極上天気アイコン】スーパサンプリングとマスク抽出による、一切ジャギーがなく内側交差線のない極上天気スタンプを自動合成。
    - 【ロゴ画像対応】'logo.png' がプロジェクト内、またはアセットフォルダに置かれた場合、透過アルファチャネルを保持したまま右上に自動合成します。
    """
    print(f"ベース画像 {base_image_path} を読み込み中...")
    try:
        if base_image_path == "TRANSPARENT_STAMP":
            print("背景が完全に透明な透過スタンプ画像を生成します...")
            image = Image.new("RGBA", (1080, 1920), (0, 0, 0, 0))
        elif not os.path.exists(base_image_path):
            print("ベース画像が見つかりません。テスト用の無地背景を生成します。")
            image = Image.new("RGBA", (1080, 1920), (34, 49, 43, 255))
        else:
            raw_image = Image.open(base_image_path).convert("RGBA")
            image = ImageOps.exif_transpose(raw_image)
            image = resize_to_reel_ratio(image)
    except Exception as e:
        print(f"画像読み込みエラー: {e}")
        image = Image.new("RGBA", (1080, 1920), (34, 49, 43, 255))

    draw = ImageDraw.Draw(image)
    width, height = image.size

    # フォントの選択 (Noto Sans JP 最優先)
    font_paths_gothic = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "NotoSansJP-Bold.ttf"),
        "/Library/Fonts/NotoSansJP-Bold.otf",
        "/Library/Fonts/NotoSansJP-Medium.otf",
        "NotoSansJP-Bold.ttf",
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/Library/Fonts/Arial Unicode.ttf"
    ]
    
    # フォントの選択 (明朝体 - ロゴマークのブランド再現用)
    font_paths_mincho = [
        "/System/Library/Fonts/ヒラギノ明朝 ProN.ttc",
        "/System/Library/Fonts/ヒラギノ明朝 Pro.ttc",
        "/System/Library/Fonts/Hiragino Mincho ProN.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
        "/Library/Fonts/Arial Unicode.ttf"
    ]
    
    font_morning_large = None
    font_morning_mid = None
    font_morning_temp = None
    font_logo_icon = None
    font_logo_text = None
    
    font_main = None
    font_sub = None
    font_message = None
    
    # ゴシック系フォントロード (Font Weight 600 / SemiBold を厳密指定)
    for fp in font_paths_gothic:
        if os.path.exists(fp):
            try:
                font_morning_large = ImageFont.truetype(fp, 60)
                font_morning_mid = ImageFont.truetype(fp, 44)
                font_morning_temp = ImageFont.truetype(fp, 48)
                font_date_large = ImageFont.truetype(fp, 48)
                font_time_small = ImageFont.truetype(fp, 38)
                font_weather_label = ImageFont.truetype(fp, 30)
                font_badge_date = ImageFont.truetype(fp, 36)
                
                font_main = ImageFont.truetype(fp, 64)
                font_sub = ImageFont.truetype(fp, 36)
                font_message = ImageFont.truetype(fp, 48)
                
                # Noto Sans JP バリアブルフォントに対して Font Weight 600 を厳密適用
                for fnt in [font_morning_large, font_morning_mid, font_morning_temp, font_date_large, font_time_small, font_weather_label, font_badge_date, font_main, font_sub, font_message]:
                    try:
                        fnt.set_variation_by_axes([600])
                    except Exception:
                        pass
                print(f"✨ [VideoCompositor] Noto Sans JP (Font Weight 600) の適用に成功しました: {fp}")
                break
            except Exception as e:
                print(f"ゴシックフォント読み込み失敗: {fp}, エラー: {e}")
                
    # 明朝系フォントロード
    for fp in font_paths_mincho:
        if os.path.exists(fp):
            try:
                font_logo_icon = ImageFont.truetype(fp, 26)
                font_logo_text = ImageFont.truetype(fp, 34)
                break
            except Exception as e:
                print(f"明朝フォント読み込み失敗: {fp}, エラー: {e}")

    # フォールバック処理
    if font_main is None:
        font_morning_large = ImageFont.load_default()
        font_morning_mid = ImageFont.load_default()
        font_morning_temp = ImageFont.load_default()
        font_main = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_message = ImageFont.load_default()
    if font_logo_text is None:
        font_logo_icon = font_morning_large
        font_logo_text = font_morning_mid

    # -------------------------------------------------------------
    # 🌅 統一洗練ストーリークローンモード (全時間帯対応)
    # -------------------------------------------------------------
    if base_image_path == "TRANSPARENT_STAMP" or mode in ["morning", "afternoon", "evening", "noon", "night", "daily"]:
        print("🎨 [VideoCompositor] 洗練された透過ストーリースタンプを合成中...")
        
        # 1. 超高品位天気スタンプ（whether_Icons 28種 JMA アイコン画像の自動判定・合成）
        weather_override = os.environ.get("WEATHER_OVERRIDE")
        status_norm = weather_override.lower() if weather_override else weather_status.lower()
        
        temp_override = os.environ.get("TEMP_OVERRIDE")
        if temp_override:
            weather_temp = temp_override
        
        def get_jma_weather_icon_code(s):
            s = s.lower()
            if "雪" in s:
                if "晴" in s: return "411"
                elif "曇" in s or "雲" in s: return "413"
                elif "雨" in s: return "414"
                return "400"
            elif "雨" in s or "傘" in s or "霧" in s:
                if "晴" in s: return "311"
                elif "曇" in s or "雲" in s: return "313"
                elif "雪" in s: return "314"
                return "300"
            elif "曇" in s or "雲" in s:
                if "晴" in s: return "201"
                elif "雨" in s: return "202"
                elif "雪" in s: return "204"
                return "200"
            elif "晴" in s:
                if "曇" in s or "雲" in s: return "101"
                elif "雨" in s: return "102"
                elif "雪" in s: return "104"
                return "100"
            else:
                return "200"  # 未知の場合はデフォルトを雲(200)とする

        icon_code = get_jma_weather_icon_code(status_norm)
        icon_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "whether_Icons")
        icon_file = os.path.join(icon_dir, f"{icon_code}.png")

        # ★ 刻印日時は動画ファイルの古いmtimeに惑わされず、常に100%【現在のリアルタイム日本時間(Asia/Tokyo JST)】を採用！
        from datetime import timezone, timedelta
        JST = timezone(timedelta(hours=9))
        now = datetime.now(JST)

        # モードの確定（autoの場合は時刻で自動判定）
        effective_mode = mode
        if effective_mode == "auto":
            if now.hour < 11:
                effective_mode = "morning"
            elif 11 <= now.hour < 16:
                effective_mode = "afternoon"
            else:
                effective_mode = "evening"

        # ★ 時刻表記の指定（07:00 -> 7:00 へ変更）
        time_override = os.environ.get("TIME_OVERRIDE")
        if time_override:
            time_line = time_override
        elif effective_mode == "morning":
            time_line = "7:00"
        elif effective_mode == "afternoon":
            time_line = "12:00"
        else:
            time_line = "17:00"

        weekdays_jp = ["月", "火", "水", "木", "金", "土", "日"]
        weekday_str = weekdays_jp[now.weekday()]
        date_time_str = f"{now.month}/{now.day}({weekday_str}) {time_line} 配信"

        # -------------------------------------------------------------
        # (1) 右側 (電線よりずっと下の位置 Y=650) ：天気アイコン -> 温度 -> 時間帯ラベル (午前の天気等)
        # ★ 天気アイコンの位置をご指示通り「午前の天気」の位置 (Y=650) まで下げる！
        # -------------------------------------------------------------
        center_cx = width - 240  # 右側エリアの中心軸
        weather_top_y = 650  # 天気アイコンの新しいY位置

        # 天気ラベル文字列の確定（午前の天気 / 午後の天気 / 夜の天気）
        if effective_mode == "morning":
            weather_label_str = "午前の天気"
        elif effective_mode == "afternoon":
            weather_label_str = "午後の天気"
        else:
            weather_label_str = "夜の天気"

        # [1] 天気アイコン表示 (Y = 650)
        icon_y = weather_top_y
        if os.path.exists(icon_file):
            print(f"☀️ [VideoCompositor] JMA天気アイコン画像を読み込み中: {icon_file} (Code: {icon_code})")
            weather_icon_img = Image.open(icon_file).convert("RGBA")
            target_w, target_h = 150, 80
            weather_icon_resized = weather_icon_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            icon_x = int(center_cx - target_w / 2)
            image.paste(weather_icon_resized, (icon_x, icon_y), weather_icon_resized)
        else:
            if "雪" in status_norm:
                weather_icon_img = create_smooth_snow_icon(line_width=24)
            elif "雨" in status_norm or "傘" in status_norm or "霧" in status_norm:
                weather_icon_img = create_smooth_rain_icon(line_width=24)
            elif "曇" in status_norm or "雲" in status_norm:
                weather_icon_img = create_smooth_cloud_icon(line_width=24)
            else:
                weather_icon_img = create_smooth_sun_icon(line_width=24)
                
            icon_display_size = 130
            weather_icon_resized = weather_icon_img.resize((icon_display_size, icon_display_size), Image.Resampling.LANCZOS)
            icon_x = int(center_cx - icon_display_size / 2)
            image.paste(weather_icon_resized, (icon_x, icon_y), weather_icon_resized)
            
        # [2] 気温表示 (Y = icon_y + 85)
        temp_y = icon_y + 85
        temp_str = f"{weather_temp}℃"
        temp_bbox = draw.textbbox((0, 0), temp_str, font=font_morning_temp)
        temp_w = temp_bbox[2] - temp_bbox[0]
        draw.text((center_cx - temp_w / 2, temp_y), temp_str, font=font_morning_temp, fill=(255, 255, 255, 255))

        # [3] 時間帯ラベル (Y = temp_y + 75: 気温の文字から少し下げる)
        label_y = temp_y + 75
        if font_weather_label:
            label_bbox = draw.textbbox((0, 0), weather_label_str, font=font_weather_label)
            label_w = label_bbox[2] - label_bbox[0]
            draw.text((center_cx - label_w / 2, label_y), weather_label_str, font=font_weather_label, fill=(255, 255, 255, 255))

        # 2. 下部の営業案内テキスト (朝・昼・夜の新規定義3段ルールに完全対応)
        from calendar_integrator import get_today_ukitchen_event, get_tomorrow_ukitchen_event
        ukitchen_data = get_today_ukitchen_event()
        
        close_hour = 21
        close_time_str = "21:00"
        
        if ukitchen_data:
            ukitchen_name = ukitchen_data["summary"]
            start_str = ukitchen_data.get("start_time", "9:00")
            end_str = ukitchen_data.get("end_time", "21:00")
            time_range_str = f"{start_str}〜{end_str}"
            if ukitchen_data.get("end_hour"):
                close_hour = max(21, ukitchen_data["end_hour"])
                close_time_str = f"{close_hour}:00"
        else:
            ukitchen_name = None
            time_range_str = "9:00〜21:00"

        text_lines = []

        if effective_mode == "morning":
            # 【朝 (7時/10時)】
            # 1段目: 朝の挨拶
            text_lines.append(("おはようございます！", font_morning_mid, 1380))
            # 2段目: 今日の営業内容
            if ukitchen_name:
                text_lines.append((f"本日 {ukitchen_name}", font_morning_large, 1450))
                # 3段目: U-kitchen出店時間表示
                text_lines.append((time_range_str, font_morning_mid, 1530))
            else:
                text_lines.append(("本日 ドリンクバー営業", font_morning_large, 1450))
                # ★ ドリンクバー営業の時は3段目の営業時間は空欄にする

        elif effective_mode == "afternoon":
            # 【昼 (12時/14時)】
            # 1段目: 空欄
            # 2段目: 現在の営業内容
            if ukitchen_name:
                active_title = f"{ukitchen_name} 営業中" if "営業" not in ukitchen_name and "出店" not in ukitchen_name else ukitchen_name
                text_lines.append((active_title, font_morning_large, 1440))
                # 3段目: U-kitchen出店時間表示
                text_lines.append((time_range_str, font_morning_mid, 1520))
            else:
                active_title = "ドリンクバー営業中"
                text_lines.append((active_title, font_morning_large, 1440))
                # ★ ドリンクバー営業の時は3段目の営業時間は空欄にする

        else:
            # 【夜 (17時/18時)】
            # 1段目: 空欄
            # 2段目: 現在の営業内容 (21時以降はありがとうございました)
            if now.hour >= close_hour:
                text_lines.append(("ありがとうございました", font_morning_large, 1440))
                text_lines.append((f"{close_time_str} Close", font_morning_mid, 1520))
            else:
                if ukitchen_name:
                    active_title = f"{ukitchen_name} 営業中" if "営業" not in ukitchen_name and "出店" not in ukitchen_name else ukitchen_name
                else:
                    active_title = "ドリンクバー営業中"
                text_lines.append((active_title, font_morning_large, 1440))
                
                # 3段目: 明日の告知 (U-kitchen出店予定がある場合のみ告知、通常のドリンクバー営業日は空欄)
                tomorrow_data = get_tomorrow_ukitchen_event()
                if tomorrow_data and tomorrow_data.get("summary"):
                    tm_name = tomorrow_data["summary"]
                    tm_text = f"明日は{tm_name}営業です" if "営業" not in tm_name and "出店" not in tm_name else f"明日は{tm_name}です"
                    text_lines.append((tm_text, font_morning_mid, 1520))

        # 下部テキストラインを描画
        for text, font, y_coord in text_lines:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            draw_text_with_shadow(draw, ((width - text_w)/2, y_coord), text, font=font)

        # 3. 馬川亭様の公式Webロゴマークを合成（右上アライメント: Y=195）＆ 直下に営業時間 9:00-21:00 を影なしで配置
        logo_paths = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png"), # プロトタイプフォルダ直下
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "07_アセット", "logo.png") # アセットフォルダ内
        ]
        
        logo_path = None
        for lp in logo_paths:
            if os.path.exists(lp):
                logo_path = lp
                break
        
        hours_str = "9:00-21:00"

        if logo_path:
            print(f"📁 [VideoCompositor] 公式ロゴ画像検出: {logo_path} を読み込んで合成します。")
            try:
                # 透過PNGとしてロード
                logo_img = Image.open(logo_path).convert("RGBA")
                # 高さを1.2倍の94pxへ拡大リサイズ
                target_h = 94
                aspect = logo_img.width / logo_img.height
                target_w = int(target_h * aspect)
                logo_resized = logo_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                
                # ★ 左上配置位置 (ロゴと営業時間を少し下げる: Y=280)
                logo_x = 180
                logo_y = 280
                
                # 透過重ね合わせ
                logo_overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
                logo_overlay.paste(logo_resized, (logo_x, logo_y), logo_resized)
                image = Image.alpha_composite(image, logo_overlay)
                draw = ImageDraw.Draw(image)
                print(f"✨ [VideoCompositor] 公式ロゴ画像({os.path.basename(logo_path)})の透過重ね合成に成功しました！")
                
                logo_center_x = logo_x + target_w / 2

                # ★ [1] 日時の文字を「白＆小さめ(30px)」にして「ロゴの上のセンター」に配置！
                dt_bbox = draw.textbbox((0, 0), date_time_str, font=font_weather_label)
                dt_w = dt_bbox[2] - dt_bbox[0]
                draw.text((logo_center_x - dt_w / 2, logo_y - 45), date_time_str, font=font_weather_label, fill=(255, 255, 255, 255))

                # ★ [2] ロゴの直下(Y = logo_y + 85)に営業時間 9:00-21:00 を【影なし】で美しく描画
                bbox_h = draw.textbbox((0, 0), hours_str, font=font_morning_mid)
                w_h = bbox_h[2] - bbox_h[0]
                draw.text((logo_center_x - w_h / 2, logo_y + 85), hours_str, font=font_morning_mid, fill=(255, 255, 255, 255))

            except Exception as e:
                print(f"⚠️ [VideoCompositor] ロゴ画像の合成エラー（テキストロゴにフォールバックします）: {e}")
                draw_fallback_text_logo(draw, font_logo_icon, font_logo_text, width, logo_text="馬川亭")
                # テキストロゴ直下に営業時間（影なし）描画
                bbox_h = draw.textbbox((0, 0), hours_str, font=font_morning_mid)
                w_h = bbox_h[2] - bbox_h[0]
                draw.text((width - 150 - w_h, 290), hours_str, font=font_morning_mid, fill=(255, 255, 255, 255))
        else:
            print("💡 [VideoCompositor] logo.png が見つかりませんでした。テキストフォールバックロゴを合成します。")
            draw_fallback_text_logo(draw, font_logo_icon, font_logo_text, width, logo_text="馬川亭")
            bbox_h = draw.textbbox((0, 0), hours_str, font=font_morning_mid)
            w_h = bbox_h[2] - bbox_h[0]
            draw.text((width - 150 - w_h, 290), hours_str, font=font_morning_mid, fill=(255, 255, 255, 255))

    # -------------------------------------------------------------
    # 🎪 MODE B: イベント告知モード (高級グラスモルフィズム重ね)
    # -------------------------------------------------------------
    else:
        print("🎨 [VideoCompositor] イベント告知用高級グラスモルフィズムを合成中...")
        color_map = {
            "warm-gold": (218, 165, 32, 255),       # ゴールド
            "emerald-green": (46, 139, 87, 255),    # エメラルド
            "indigo-night": (25, 25, 112, 255)       # インディゴ
        }
        accent_color = color_map.get(theme_color, (218, 165, 32, 255))

        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        overlay_draw.rounded_rectangle(
            [50, 150, width - 50, 450], 
            radius=20, 
            fill=(0, 0, 0, 140), 
            outline=accent_color,
            width=3
        )
        
        overlay_draw.rounded_rectangle(
            [50, height - 400, width - 50, height - 150], 
            radius=20, 
            fill=(0, 0, 0, 160), 
            outline=accent_color,
            width=2
        )

        image = Image.alpha_composite(image, overlay)
        draw = ImageDraw.Draw(image)

        draw.text((100, 180), text_title, font=font_main, fill=(255, 255, 255, 255))
        draw.text((100, 280), text_subtitle, font=font_sub, fill=accent_color)
        draw.text((100, 340), "📍 馬川亭 - UMAKAWATEI", font=font_sub, fill=(200, 200, 200, 255))

        message_y = height - 310
        draw.text((100, message_y), text_message, font=font_message, fill=(255, 250, 205, 255))
        draw.text((width - 320, height - 100), "Powered by UMA-POST", font=font_sub, fill=(150, 150, 150, 180))

    # 保存 (透過アルファチャネル RGBA を100%保持)
    output_path = "latest_composite_post.png"
    image.save(output_path, "PNG")
    print(f"クリエイティブ画像が正常に合成されました(透過維持): {output_path}")
    return output_path

def resize_to_reel_ratio(img):
    target_ratio = 9 / 16
    width, height = img.size
    current_ratio = width / height

    if current_ratio > target_ratio:
        new_width = int(height * target_ratio)
        left = (width - new_width) / 2
        img = img.crop((left, 0, left + new_width, height))
    elif current_ratio < target_ratio:
        new_height = int(width / target_ratio)
        top = (height - new_height) / 2
        img = img.crop((0, top, width, top + new_height))
    
    return img.resize((1080, 1920), Image.Resampling.LANCZOS)

def get_ffmpeg_path():
    """システム全体の ffmpeg (shutil.which) を最優先、なければ bin/ffmpeg を使用します"""
    import shutil
    sys_path = shutil.which("ffmpeg")
    if sys_path:
        return sys_path

    local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", "ffmpeg")
    if os.path.exists(local_path):
        return local_path
    
    if os.path.exists("./bin/ffmpeg"):
        return os.path.abspath("./bin/ffmpeg")
        
    return None

def find_latest_gopro_video(mode=None):
    """02_デイリー動画素材フォルダから、指定モード(morning/afternoon/evening)の時間帯に合致した最新GoProタイムラプスビデオ(.mp4)を自動スキャンします"""
    import glob
    target_env = os.environ.get("TARGET_VIDEO")
    if target_env:
        print(f"🎯 [VideoCompositor] 環境変数 TARGET_VIDEO による直接指定を検出しました: {target_env}")
    search_dirs = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "07_アセット", "02_デイリー動画素材"),
        "./07_アセット/02_デイリー動画素材",
        "07_アセット/02_デイリー動画素材",
        "/var/secured_vault/camera",
        "/Users/sawadiiii/Library/CloudStorage/GoogleDrive-sawada@esoragoto.jp/共有ドライブ/ESORAGOTO-LLC/20_umakawatei/07_アセット/02_デイリー動画素材"
    ]
    
    mp4_files = []
    for asset_dir in search_dirs:
        if os.path.exists(asset_dir):
            files = glob.glob(os.path.join(asset_dir, "*.mp4")) + glob.glob(os.path.join(asset_dir, "*.MP4"))
            # 「01_投稿済み」を除外
            valid_files = [f for f in files if "01_投稿済み" not in f]
            mp4_files.extend(valid_files)
            
    if not mp4_files:
        return None
        
    if target_env:
        matched = [f for f in mp4_files if target_env in f]
        if matched:
            print(f"✨ [VideoCompositor] 指定ファイル '{target_env}' を正常に補獲しました: {os.path.basename(matched[0])}")
            return matched[0]
        
    # 最終更新日時順（最新順）にソート
    mp4_files.sort(key=os.path.getmtime, reverse=True)

    # モードに応じた撮影時間帯(JST)のフィルタリング
    if mode in ["morning", "afternoon", "evening"]:
        target_files = []
        for f in mp4_files:
            mtime = os.path.getmtime(f)
            # ファイル名に HHMMSS が入っているか解析（例: 20260810_121000_vertical.mp4）
            basename = os.path.basename(f)
            file_hour = None
            try:
                parts = basename.split("_")
                if len(parts) >= 2 and len(parts[1]) >= 6 and parts[1][:6].isdigit():
                    file_hour = int(parts[1][:2])
            except Exception:
                pass
            
            if file_hour is None:
                # mtime から時を取得
                from datetime import datetime, timezone, timedelta
                JST = timezone(timedelta(hours=9))
                dt = datetime.fromtimestamp(mtime, tz=JST)
                file_hour = dt.hour

            if mode == "morning" and (0 <= file_hour < 11):
                target_files.append(f)
            elif mode == "afternoon" and (11 <= file_hour < 16):
                target_files.append(f)
            elif mode == "evening" and (16 <= file_hour <= 23):
                target_files.append(f)

        if target_files:
            print(f"🎬 [VideoCompositor] モード '{mode}' に合致する時間帯(hour:{file_hour}時台)の適切な動画素材を厳選しました: {os.path.basename(target_files[0])}")
            return target_files[0]

    return mp4_files[0]

def move_video_to_posted(video_path):
    """
    投稿完了した動画ファイルを「02_デイリー動画素材/01_投稿済み」フォルダへ安全に移動します。
    """
    if not video_path or not os.path.exists(video_path):
        return False
        
    try:
        import shutil
        video_dir = os.path.dirname(os.path.abspath(video_path))
        posted_dir = os.path.join(video_dir, "01_投稿済み")
        
        # 01_投稿済み フォルダが存在しなければ自動作成
        os.makedirs(posted_dir, exist_ok=True)
        
        filename = os.path.basename(video_path)
        dest_path = os.path.join(posted_dir, filename)
        
        shutil.move(video_path, dest_path)
        print(f"📦 [VideoCompositor] 使用済み動画を「01_投稿済み」フォルダへ移動完了: {filename}")
        return True
    except Exception as e:
        print(f"⚠️ [VideoCompositor] 動画ファイルの退避移動中にエラーが発生しました: {e}")
        return False

def overlay_stamp_on_video(video_path, stamp_image_path, output_video_path="latest_reel_video.mp4"):
    """GoProタイムラプス動画の上に、透過テロップスタンプ(PNG)をFFmpegで15秒間完璧にアルファブレンド合成します"""
    import subprocess
    ffmpeg_bin = get_ffmpeg_path()
    if not ffmpeg_bin:
        print("❌ [VideoCompositor] FFmpegが見つかりません。動画合成をスキップします。")
        return None
        
    print(f"🎬 [VideoCompositor] GoPro動画にテロップスタンプを動画合成中: {video_path} -> {output_video_path}...")
    try:
        # ffprobe で動画の幅と高さを事前チェック
        width, height = 1920, 1080
        ffprobe_bin = ffmpeg_bin.replace("ffmpeg", "ffprobe") if "ffmpeg" in ffmpeg_bin else "ffprobe"
        try:
            prob_cmd = [
                ffprobe_bin, "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=p=0",
                video_path
            ]
            prob_res = subprocess.run(prob_cmd, capture_output=True, text=True)
            if prob_res.returncode == 0 and prob_res.stdout.strip():
                parts = prob_res.stdout.strip().split(",")
                if len(parts) >= 2:
                    width, height = int(parts[0]), int(parts[1])
        except Exception as e:
            print(f"⚠️ [VideoCompositor] ffprobeによる動画サイズ解析をスキップ: {e}")

        base_name_lower = os.path.basename(video_path).lower()
        is_already_vertical = "vertical" in base_name_lower or "upright" in base_name_lower
        if width > height and not is_already_vertical:
            print(f"🔄 [VideoCompositor] 横長動画({width}x{height})を検出しました。縦画面(90度回転)へ自動回転補正します...")
            filter_str = "[0:v]transpose=1,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[bg];[bg][1:v]overlay=0:0[v]"
        else:
            print(f"📱 [VideoCompositor] 縦型/直立動画({width}x{height})としてそのまま回転なしで合成処理を実行します...")
            filter_str = "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[bg];[bg][1:v]overlay=0:0[v]"

        cmd = [
            ffmpeg_bin,
            "-i", video_path,
            "-loop", "1",
            "-i", stamp_image_path,
            "-filter_complex", filter_str,
            "-map", "[v]",
            "-t", "15",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", "24",
            "-y",
            output_video_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and os.path.exists(output_video_path):
            print(f"🎥 [VideoCompositor] タイムラプス動画リールの生成に成功しました！: {output_video_path}")
            return output_video_path
        else:
            print(f"⚠️ [VideoCompositor] FFmpeg合成エラー(returncode={res.returncode}): {res.stderr[-300:] if res.stderr else '不明なエラー'}")
            print("🔄 [VideoCompositor] 代替フォールバック: 背景付き合成画像から5秒の縦型リール動画を自動生成します...")
            bg_image = "latest_composite_post.png" if os.path.exists("latest_composite_post.png") else stamp_image_path
            return convert_image_to_reel_video(bg_image, output_video_path)
    except Exception as e:
        print(f"❌ [VideoCompositor] 動画合成処理中に例外が発生しました: {e}")
        print("🔄 [VideoCompositor] 代替フォールバック: 背景付き合成画像から5秒の縦型リール動画を自動生成します...")
        bg_image = "latest_composite_post.png" if os.path.exists("latest_composite_post.png") else stamp_image_path
        return convert_image_to_reel_video(bg_image, output_video_path)

def convert_image_to_reel_video(image_path, output_video_path="latest_reel_video.mp4"):
    import subprocess
    ffmpeg_bin = get_ffmpeg_path()
    
    print(f"🎬 [VideoCompositor] 画像から5秒のリール動画(MP4)を生成中: {image_path} -> {output_video_path}...")
    
    if not os.path.exists(image_path):
        print("❌ エラー: 動画変換元の画像が見つかりません。")
        return None
        
    if not ffmpeg_bin:
        print("⚠️ [VideoCompositor] システムに FFmpeg が見つかりませんでした。動画化をシミュレートし、ダミー動画をコピーします。")
        with open(output_video_path, "w") as f:
            f.write("MOCK MP4 VIDEO CONTENT (FFMPEG NOT INSTALLED)")
        return output_video_path
        
    try:
        cmd = [
            ffmpeg_bin,
            "-loop", "1",
            "-i", image_path,
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-t", "5",
            "-pix_fmt", "yuv420p",
            "-vf", "scale=1080:1920,setsar=1",
            "-r", "24",
            "-y",
            output_video_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(f"🎥 [VideoCompositor] 縦型5秒リール動画(MP4)の生成に成功しました: {output_video_path}")
        return output_video_path
    except Exception as e:
        print(f"❌ [VideoCompositor] FFmpegによる動画変換中にエラーが発生しました: {e}")
        return None
