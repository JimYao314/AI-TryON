# 檔案名稱：bot_server.py (全功能最終整合版)
import os
import time
import json
import shutil
import threading
import traceback
import io
from PIL import Image
from flask import Flask, request, abort, send_from_directory
from linebot import LineBotApi, WebhookHandler
from linebot.models import (
    MessageEvent, ImageMessage, TextMessage, TextSendMessage, ImageSendMessage,
    TemplateSendMessage, ButtonsTemplate, MessageAction
)
from comfy_client import ComfyUIClient

app = Flask(__name__)

# ==========================================
# 1. 金鑰與伺服器設定
# ==========================================
LINE_CHANNEL_ACCESS_TOKEN = 'f1JLVSPqO7PwSZpA0lN99MfkAWMM0x4LdGspioSm87n2lo9ZMcWtnR2VySR69JsdusHeuHhQf7S7/HjhlkelUpz7/q5+XYN/XPIx0rKLvOExh7i4oH0rSq70rbeRLrtZoFeJxj21Os/pso/a6E6qrAdB04t89/1O/w1cDnyilFU='
LINE_CHANNEL_SECRET = '8d678eb0a737e41d7ed366efb206da54'
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

COMFY_SERVER_URL = "divisi-nummulitic-xxxxxxxx.xxxxx-xxxx.xxx"

USER_STATES = {}

# 初始化必要資料夾
for folder in ['static', 'temp', 'dataset/garments']:
    if not os.path.exists(folder): os.makedirs(folder)

# 🌟 啟動時自動載入 46 件服裝資料庫
DB_PATH = 'dataset/garment_db.json'
GARMENT_DB = {}
if os.path.exists(DB_PATH):
    with open(DB_PATH, 'r', encoding='utf-8') as f:
        GARMENT_DB = json.load(f)
    print(f"✅ 成功載入 {len(GARMENT_DB)} 件服裝型錄供推薦引擎使用！")


# ==========================================
# 🌟 核心引擎 A：多圖拼接前處理
# ==========================================
def process_garment_images_to_bytes(image_bytes_list, target_edge=1024):
    if not image_bytes_list: return None
    processed_images = []
    total_width, max_height = 0, 0
    for img_bytes in image_bytes_list:
        img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        longest_edge = max(img.width, img.height)
        scale = target_edge / longest_edge
        new_w, new_h = int(img.width * scale), int(img.height * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        processed_images.append(img)
        total_width += new_w
        max_height = max(max_height, new_h)
    tight_canvas = Image.new("RGB", (total_width, max_height), (255, 255, 255))
    current_x = 0
    for img in processed_images:
        paste_y = (max_height - img.height) // 2
        tight_canvas.paste(img, (current_x, paste_y), mask=img)
        current_x += img.width
    output_buffer = io.BytesIO()
    tight_canvas.save(output_buffer, format="PNG")
    return output_buffer.getvalue()


# ==========================================
# 🌟 核心引擎 B：本地中文計分推薦系統
# ==========================================
def find_best_garment_local(user_text):
    if not GARMENT_DB: return None, None
    best_match_path, best_id, highest_score = None, None, 0
    user_text_lower = user_text.lower()
    for garment_id, info in GARMENT_DB.items():
        score = sum(1 for tag in info['tags'] if tag.lower() in user_text_lower)
        if score > highest_score:
            highest_score = score
            best_match_path = info['path']
            best_id = garment_id
    return best_match_path, best_id


# ==========================================
# 2. 系統基礎功能 (靜態、Webhook)
# ==========================================
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)


@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except Exception as e:
        print(f"❌ Webhook Error: {e}");
        abort(400)
    return 'OK'


# ==========================================
# 3. 非同步背景 AI 管線 (對接新模組 + 文字注入)
# ==========================================
def process_vton_in_background(user_id, portrait_path, garment_path, base_url, user_text=""):
    try:
        print(f"⏳ [任務啟動] 開始為 {user_id} 運算...")
        client = ComfyUIClient(COMFY_SERVER_URL)

        # 🌟 這裡會呼叫 comfy_client，將 user_text 注入 FLUX Node 130
        result_bytes = client.run_vton_pipeline("Klein_v1.5_workflow_api.json", portrait_path, garment_path, user_text)

        result_filename = f"result_{user_id}.png"
        result_path = os.path.join('static', result_filename)
        with open(result_path, "wb") as f:
            f.write(result_bytes)

        image_url = f"{base_url}static/{result_filename}?t={int(time.time())}"
        line_bot_api.push_message(user_id, [
            TextSendMessage(text="✨ AI 換裝完成！這是您的專屬穿搭結果："),
            ImageSendMessage(original_content_url=image_url, preview_image_url=image_url)
        ])
        # 清理暫存
        if os.path.exists(portrait_path): os.remove(portrait_path)
        if os.path.exists(garment_path): os.remove(garment_path)
    except Exception as e:
        print(f"❌ 背景任務失敗: {e}")
        line_bot_api.push_message(user_id, TextSendMessage(text=f"⚠️ 合成發生錯誤：{str(e)}"))


# ==========================================
# 4. 文字訊息邏輯：指令、推薦、防呆
# ==========================================
@handler.add(MessageEvent, message=TextMessage)
def handle_text(event):
    user_id = event.source.user_id
    user_text = event.message.text.strip()
    base_url = request.host_url.replace('http://', 'https://')

    # 選單指令：功能表
    if user_text == "@功能表":
        buttons = ButtonsTemplate(title='👗 AI 智慧衣櫥', text='請開啟功能表進入換裝流程',
                                  actions=[MessageAction(label='✨ 開始試衣', text='@開始試衣')])
        line_bot_api.reply_message(event.reply_token, TemplateSendMessage(alt_text='功能表', template=buttons))
        return

    # 選單指令：開始試衣
    if user_text == "@開始試衣" or user_text == "重置":
        if user_id in USER_STATES: del USER_STATES[user_id]
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="👋 歡迎使用！請先傳送一張您的「全身照」📸"))
        return

    # 推薦引擎 & OK 指令 (當已傳送人像後)
    if user_id in USER_STATES and USER_STATES[user_id]["step"] == "collecting":
        # A. 觸發合成指令
        if user_text.upper() in ["OK", "完成"]:
            if USER_STATES[user_id]["garment_list"]:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="🔍 合併衣物中，啟動 AI 合成..."))
                merged_bytes = process_garment_images_to_bytes(USER_STATES[user_id]["garment_list"])
                merged_path = f"temp/{user_id}_merged.png"
                with open(merged_path, "wb") as f:
                    f.write(merged_bytes)
                portrait_path = USER_STATES[user_id]["portrait_path"]
                del USER_STATES[user_id]
                threading.Thread(target=process_vton_in_background,
                                 args=(user_id, portrait_path, merged_path, base_url, "custom mix style")).start()
            else:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 尚未收到衣服照片喔！"))
            return

        # B. 文字推薦引擎 (打字許願)
        best_path, chosen_id = find_best_garment_local(user_text)
        if best_path and os.path.exists(best_path):
            line_bot_api.reply_message(event.reply_token,
                                       TextSendMessage(text=f"🎯 已為您配對 [{chosen_id}]，正在啟動換裝..."))
            target_path = f"temp/{user_id}_garment.jpg"
            shutil.copy(best_path, target_path)
            portrait_path = USER_STATES[user_id]["portrait_path"]
            del USER_STATES[user_id]
            threading.Thread(target=process_vton_in_background,
                             args=(user_id, portrait_path, target_path, base_url, user_text)).start()
        else:
            line_bot_api.reply_message(event.reply_token,
                                       TextSendMessage(text="😢 資料庫找不到符合的衣服，建議傳送照片或更換關鍵字！"))
        return

    # 若非以上狀況
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="👋 歡迎！請傳送「全身照」或點擊功能表開始試衣。"))


# ==========================================
# 5. 圖片訊息邏輯：人像與多圖收集
# ==========================================
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    user_id = event.source.user_id
    img_data = line_bot_api.get_message_content(event.message.id).content
    if user_id not in USER_STATES:
        path = f"temp/{user_id}_portrait.jpg"
        with open(path, "wb") as f:
            f.write(img_data)
        USER_STATES[user_id] = {"step": "collecting", "portrait_path": path, "garment_list": []}
        line_bot_api.reply_message(event.reply_token, TextSendMessage(
            text="📸 收到人像！請繼續：\n👉 傳送 1~5 張衣服圖 (傳完打 OK)\n👉 或輸入需求文字 (如:女生 短T)"))
    elif USER_STATES[user_id]["step"] == "collecting":
        USER_STATES[user_id]["garment_list"].append(img_data)
        count = len(USER_STATES[user_id]["garment_list"])
        line_bot_api.reply_message(event.reply_token,
                                   TextSendMessage(text=f"✅ 已接收第 {count} 件。繼續傳圖，或回覆「OK」開始。"))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)