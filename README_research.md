# 🎓 研究発表サポートAI

研究発表会での利用を想定したStreamlitアプリです。

## 機能

- 発表タイトル・発表者・発表日を入力
- スマートフォンのマイクで研究発表を録音
- Geminiで音声を文字起こし
- 発表内容を以下に整理
  - 発表要約
  - 研究目的・問題意識
  - 研究方法
  - 結果・考察
  - 研究の意義
  - 限界
  - 重要な要点
- 質疑応答用の質問候補を6〜10個程度自動生成
  - 質問
  - 質問する意図
  - 回答後の深掘り質問
- 発表要約をWord（.docx）で保存

## GitHub / Streamlit Community Cloud

必要ファイル：
- app.py
- requirements.txt

Secrets：
GEMINI_API_KEY = "あなたのGemini APIキー"

JSON・HTMLの保存機能は廃止しています。
