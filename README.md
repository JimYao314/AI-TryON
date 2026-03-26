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

<img width="100%" alt="VTON System Architecture" src="https://github.com/user-attachments/assets/3613763d-85db-4b4b-a256-477bb9ca965a" />

> **設計思維**：本系統採用微服務拆分邏輯，本地端負責高併發的 Webhook 接應，雲端負責重度 GPU 運算，達成效能與成本的平衡。

## 📁 目錄結構說明
- `bot_server.py`: 系統中樞，負責 Webhook 與狀態機管理。
- `comfy_client.py`: API 通訊模組，封裝 ComfyUI 呼叫邏輯。
- `workflow_api.json`: AI 模型運算藍圖。
- `dataset/`: 存放服裝型錄與標籤資料庫。

## 📓 雲端大腦部署
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/JimYao314/AI-TryON/blob/main/notebook/for_github_comfyui_v_3_Flux_2_Klein_315.ipynb)
