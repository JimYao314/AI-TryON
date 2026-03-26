# 檔案名稱：core.py
import cv2
import numpy as np
import requests
from deep_translator import GoogleTranslator  # 💡 新增：載入最穩定的翻譯套件


class OutfitStyleCore:
    def __init__(self):
        from ultralytics import YOLO
        self.seg_model = YOLO("yolov8n-seg.pt")
        # ⚠️ 請記得隨時將這裡更新為 Colab 當天產生的最新 Ngrok URL
        self.colab_api_url = "https://divisi-nummulitic-margorie.ngrok-free.dev/analyze"

    def run_segmentation(self, img):
        results = self.seg_model.predict(img, classes=[0], conf=0.5, verbose=False)
        report = {"success": False, "ai_analysis": "等待解析..."}

        if not results or results[0].masks is None:
            return None, report

        # --- 1. 生成白底去背圖 ---
        img_h, img_w = img.shape[:2]
        mask = (cv2.resize(results[0].masks.data[0].cpu().numpy(), (img_w, img_h)) > 0.5).astype(np.uint8) * 255
        background = np.ones_like(img) * 255
        fg = cv2.bitwise_and(img, img, mask=mask)
        bg = cv2.bitwise_and(background, background, mask=cv2.bitwise_not(mask))
        final_img = cv2.add(fg, bg)

        # --- 2. 呼叫大腦 ---
        ai_description = "無分析數據"
        try:
            _, img_encoded = cv2.imencode('.jpg', final_img)
            response = requests.post(
                self.colab_api_url,
                files={"file": ("image.jpg", img_encoded.tobytes(), "image/jpeg")},
                timeout=20
            )

            if response.status_code == 200:
                res_json = response.json()
                if res_json.get("success"):
                    ai_description = res_json.get("analysis", "解析結果為空")

                    # 💡 【優化 1：繁體中文翻譯】
                    try:
                        print(f"🔤 [翻譯中] 原始英文: {ai_description}")
                        # 將大腦輸出的英文翻譯成繁體中文 (zh-TW)
                        translated_text = GoogleTranslator(source='en', target='zh-TW').translate(ai_description)
                        ai_description = translated_text
                        print(f"🔤 [翻譯完成] 繁體中文: {ai_description}")
                    except Exception as trans_err:
                        print(f"⚠️ 翻譯模組異常，保留英文輸出: {trans_err}")
                        pass  # 如果翻譯意外失敗，不中斷程式，直接輸出英文

                else:
                    ai_description = f"大腦運算錯誤: {res_json.get('error')}"
            else:
                ai_description = f"連線異常 (代碼: {response.status_code})"

        except Exception as e:
            ai_description = f"通訊失敗: {str(e)}"

        report.update({
            "success": True,
            "body_ratio": round((np.count_nonzero(mask) / (img_w * img_h)) * 100, 1),
            "completeness_text": "全身完整",
            "ai_analysis": ai_description,
            "message": "✅ 偵測成功"
        })

        return final_img, report