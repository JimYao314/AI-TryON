# 檔案名稱：comfy_client.py
import json
import urllib.request
import urllib.parse
import time
import requests


class ComfyUIClient:
    def __init__(self, server_address):
        # 移除網址前綴與末尾斜線，確保格式為：xxxx.pinggy.link 或 xxxx.ngrok-free.app
        self.server_address = server_address.replace("https://", "").replace("http://", "").strip("/")

    def upload_image(self, file_path, filename):
        """將圖片上傳至 ComfyUI 伺服器"""
        print(f"🔼 正在上傳圖片至 ComfyUI: {filename}")
        try:
            with open(file_path, "rb") as f:
                files = {"image": (filename, f)}
                # 呼叫 ComfyUI API 上傳接口
                res = requests.post(f"https://{self.server_address}/api/upload/image", files=files, timeout=30)
                if res.status_code == 200:
                    return res.json()["name"]
                else:
                    print(f"❌ 上傳失敗: {res.text}")
                    return None
        except Exception as e:
            print(f"❌ 上傳過程發生錯誤: {e}")
            return None

    def run_vton_pipeline(self, workflow_json_path, portrait_path, garment_path, user_text=""):
        """
        執行 Klein_v1.5 換衣管線
        Node 76: 人像 (Portrait)
        Node 157: 衣服 (Garment)
        Node 130: 文字提示詞 (Positive Prompt)
        Node 160: 最終成品輸出 (Preview/Save Image)
        """

        # 1. 上傳圖片並取得伺服器端檔名
        p_name = self.upload_image(portrait_path, f"user_p_{int(time.time())}.png")
        g_name = self.upload_image(garment_path, f"garment_g_{int(time.time())}.png")

        if not p_name or not g_name:
            raise Exception("圖片上傳失敗，無法啟動 AI 運算。")

        # 2. 載入工作流 JSON 藍圖
        with open(workflow_json_path, "r", encoding="utf-8") as f:
            prompt = json.load(f)

        # 3. 🌟 動態注入參數 🌟
        # 對齊 Node 76 (人像)
        prompt["76"]["inputs"]["image"] = p_name
        # 對齊 Node 157 (衣服/拼接圖)
        prompt["157"]["inputs"]["image"] = g_name

        # 處理文字 Prompt (Node 130)
        # 設定基礎系統 Prompt，並合併使用者的需求
        system_base = "TRYON person in the first picture. Replace the outfit completely with the garments shown in the reference images. "
        combined_prompt = system_base + (user_text if user_text else "Professional fashion editorial photography.")
        prompt["130"]["inputs"]["text"] = combined_prompt
        print(f"📝 已注入最終 Prompt: {combined_prompt}")

        # 4. 發送任務至佇列
        print("🚀 正在提交任務至雲端大腦 (FLUX Model)...")
        p_payload = json.dumps({"prompt": prompt}).encode('utf-8')
        req = urllib.request.Request(f"https://{self.server_address}/api/prompt", data=p_payload)
        with urllib.request.urlopen(req) as response:
            result_json = json.loads(response.read())
            prompt_id = result_json['prompt_id']

        # 5. 輪詢 (Polling) 等待運算完成
        print(f"⏳ 任務 ID: {prompt_id}，等待運算中 (FLUX 較耗時，請耐心等候)...")
        while True:
            h_req = urllib.request.Request(f"https://{self.server_address}/api/history/{prompt_id}")
            with urllib.request.urlopen(h_req) as h_res:
                history = json.loads(h_res.read())

            if prompt_id in history:
                print("✅ ComfyUI 運算完成！")

                # 🌟 鎖定輸出節點 160 🌟
                if "160" in history[prompt_id]['outputs']:
                    image_info = history[prompt_id]['outputs']["160"]['images'][0]
                    print(f"🎯 成功鎖定輸出節點: 160，檔名: {image_info['filename']}")

                    # 6. 下載成品圖
                    v_url = f"https://{self.server_address}/api/view?{urllib.parse.urlencode(image_info)}"
                    v_req = urllib.request.Request(v_url)
                    with urllib.request.urlopen(v_req) as v_res:
                        return v_res.read()
                else:
                    # 報錯診斷
                    actual_nodes = list(history[prompt_id]['outputs'].keys())
                    raise Exception(f"找不到 Node 160。目前輸出的節點有: {actual_nodes}")

            # 每 3 秒檢查一次進度
            time.sleep(3)