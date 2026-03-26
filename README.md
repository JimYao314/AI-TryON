# 👗 AI 智慧虛擬試衣助理 (VTON LINE AI Assistant)

本專案是一個基於 **微服務架構** 的 AI 虛擬試衣系統。使用者透過 **LINE App** 即可進行高品質的 AI 服裝合成與智能推薦。

## 🚀 核心技術亮點
- **三層式架構設計**: 分離前端(LINE)、邏輯中樞(Flask)與運算工廠(ComfyUI/Colab)，達成 Edge-Cloud 協同運算。
- **非同步任務系統**: 實作 Python Multi-threading 與主動推播，完美解決 AI 運算耗時導致的 Webhook 逾時痛點。
- **自研推薦引擎**: 建構 46 件服飾之 Metadata Database，設計基於模糊計分的推薦演算法。
- **影像前處理管線**: 支援多圖無縫拼接與正規化處理，優化 AI 合成特徵。

## 🛠️ 技術棧 (Tech Stack)
- **Backend**: Python 3.10, Flask (RESTful API)
- **AI Brain**: ComfyUI (FLUX Model, CatVTON)
- **Bot Platform**: LINE Messaging API v3
- **Tools**: Ngrok, Pinggy, Pillow, OpenCV

## 📊 系統架構

```mermaid
graph TD
    UserA(👤 輸入 A：上傳「全身照片」)
    UserB1(📸 輸入 B1：自訂衣服照片)
    UserB2(💬 輸入 B2：輸入文字需求)
    Result(✨ 輸出：接收高擬真換裝照片)
    
    UserA --> State{狀態機}
    UserB1 --> Pack[API 打包]
    UserB2 --> Rec[推薦引擎]
    Pack --> AI[☁️ Colab AI 運算]
    AI --> Result

<img width="1590" height="3320" alt="mermaid-diagram-2026-03-11-163822" src="https://github.com/user-attachments/assets/3613763d-85db-4b4b-a256-477bb9ca965a" />

> **設計思維**：本系統採用微服務拆分邏輯，本地端負責高併發的 Webhook 接應，雲端負責重度 GPU 運算，達成效能與成本的平衡。

## 📁 目錄結構說明
- `bot_server.py`: 系統中樞，負責 Webhook 與狀態機管理。
- `comfy_client.py`: API 通訊模組，封裝 ComfyUI 呼叫邏輯。
- `workflow_api.json`: AI 模型運算藍圖。
- `dataset/`: 存放服裝型錄與標籤資料庫。
