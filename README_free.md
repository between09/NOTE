# 🎓 授業ノートAI — Androidスマホ版 v2

スマホのブラウザだけで、

**録音 → 文字起こし → AI整理 → ノート表示**

まで行う試作版です。

## 使用するAI

OpenAI APIではなく、**Google Gemini API**を使用します。

Gemini APIには無料枠がありますが、無料枠にはモデルごとの利用上限があります。
そのため「完全無制限」ではありません。

## GitHubに置くファイル

- `app.py`
- `requirements.txt`
- `README.md`

## Streamlit Community Cloudで公開

1. GitHubにこの3ファイルをアップロード
2. Streamlit Community Cloudで `app.py` を指定してDeploy
3. Streamlitのアプリ設定から **Secrets** を開く
4. 次を設定

```toml
GEMINI_API_KEY = "あなたのGemini APIキー"
```

5. 保存してアプリを再起動

## Gemini APIキー

Google AI StudioでAPIキーを作成します。

https://aistudio.google.com/apikey

APIキーはGitHubのコードに直接書かないでください。

## 注意

- 授業の録音について、大学・授業担当者のルールを確認してください。
- 他の学生の発言が入る場合は、特に取り扱いに注意してください。
- 音声はGemini APIへ送信されます。
