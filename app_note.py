import json
import os
import tempfile
from datetime import date
from html import escape

import streamlit as st
from google import genai
from google.genai import types

st.set_page_config(page_title="授業ノートAI", page_icon="🎓", layout="centered")

st.markdown("""
<style>
.block-container {max-width: 720px; padding: 1.2rem 1rem 3rem;}
h1 {font-size: 1.8rem !important;}
div[data-testid="stAudioInput"] {margin-top: .5rem;}
.big-button button {font-size: 1.1rem; padding: .7rem 1rem;}
.note-card {padding: 1rem; border-radius: 16px; background: #f7f7f7; margin: .6rem 0;}
</style>
""", unsafe_allow_html=True)

st.title("🎓 授業ノートAI")
st.caption("スマホだけで、授業の録音からノートを作る")
st.caption("無料枠のGoogle Gemini APIを使用します。")

api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
client = genai.Client(api_key=api_key) if api_key else None

if "note" not in st.session_state:
    st.session_state.note = None
if "transcript" not in st.session_state:
    st.session_state.transcript = None

with st.expander("⚙️ 授業情報", expanded=True):
    course = st.text_input("授業名", placeholder="例：特別支援教育論")
    teacher = st.text_input("先生（任意）", placeholder="例：○○先生")
    lesson_date = st.date_input("日付", value=date.today())

st.subheader("🎙️ 授業を録音")
st.caption("ブラウザのマイク許可が必要です。授業の録音ルールも確認してください。")
audio = st.audio_input("録音を開始／終了")

if audio:
    st.audio(audio)

    if not api_key:
        st.error("Gemini APIキーがまだ設定されていません。StreamlitのSecretsに GEMINI_API_KEY を設定してください。")
    elif st.button("✨ この授業をノートにする", type="primary", use_container_width=True):
        try:
            with st.status("授業ノートを作成中…", expanded=True) as status:
                st.write("① 音声をGeminiへ送信中…")

                audio_bytes = audio.getvalue()
                mime_type = audio.type or "audio/wav"

                suffix = ".wav"
                if "webm" in mime_type:
                    suffix = ".webm"
                elif "mp4" in mime_type or "m4a" in mime_type:
                    suffix = ".m4a"
                elif "mpeg" in mime_type or "mp3" in mime_type:
                    suffix = ".mp3"

                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
                    f.write(audio_bytes)
                    temp_path = f.name

                try:
                    uploaded_file = client.files.upload(file=temp_path)

                    st.write("② 音声を文字起こし・整理中…")

                    schema = {
                        "type": "object",
                        "properties": {
                            "transcript": {"type": "string"},
                            "summary": {"type": "string"},
                            "important": {"type": "array", "items": {"type": "string"}},
                            "topics": {"type": "array", "items": {"type": "string"}},
                            "terms": {"type": "array", "items": {"type": "string"}},
                            "assignments": {"type": "array", "items": {"type": "string"}},
                            "review": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": [
                            "transcript", "summary", "important", "topics",
                            "terms", "assignments", "review"
                        ],
                    }

                    prompt = f"""
あなたは正確な大学授業ノート整理アシスタントです。
添付された授業音声を日本語で処理してください。

授業名: {course or '未入力'}
先生: {teacher or '未入力'}
日付: {lesson_date}

以下のルールを厳守してください。
- transcript に音声の発言内容をできるだけ忠実に文字起こしする。
- 聞き取れない部分は推測で補完せず、「[聞き取り不明]」とする。
- 文字起こしにない事実を作らない。
- summary は授業全体を3〜6文で要約する。
- important は先生が強調・繰り返し説明した重要ポイントを優先する。
- topics は授業の流れを整理する。
- terms は専門用語と授業内での説明を短くまとめる。
- assignments は課題・提出物・提出期限が明確に出ている場合だけ記載する。
- review は授業内容から復習価値のある点を整理する。
- 不明瞭な内容は無理に補完しない。
- 出力は指定されたJSON形式だけにする。
"""

                    response = client.models.generate_content(
                        model="gemini-3.8-flash",
                        contents=[prompt, uploaded_file],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=schema,
                        ),
                    )

                    note = json.loads(response.text)
                    st.session_state.transcript = note.pop("transcript", "")
                    st.session_state.note = note
                    status.update(label="完成！", state="complete")

                finally:
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass

        except Exception as e:
            st.error(f"作成中にエラーが起きました：{e}")

note = st.session_state.note
if note:
    st.divider()
    st.header("📚 今日の授業ノート")

    st.markdown("### 💡 要約")
    st.write(note["summary"])

    sections = [
        ("⭐ 重要ポイント", "important"),
        ("📚 授業の流れ", "topics"),
        ("🔤 重要語句", "terms"),
        ("📝 課題・提出物", "assignments"),
        ("❓ 復習ポイント", "review"),
    ]

    for title, key in sections:
        st.subheader(title)
        items = note[key]
        if items:
            for item in items:
                st.markdown(f"- {item}")
        else:
            st.caption("該当なし")

    with st.expander("📄 元の文字起こしを見る"):
        st.text_area(
            "transcript",
            st.session_state.transcript or "",
            height=350,
            label_visibility="collapsed",
        )

    # JSON：データ保存用
    json_data = json.dumps({
        "course": course,
        "teacher": teacher,
        "date": str(lesson_date),
        "note": note,
        "transcript": st.session_state.transcript,
    }, ensure_ascii=False, indent=2)

    # HTML：スマホで普通のノートとして読む用
    def html_list(items):
        if not items:
            return "<p class='empty'>該当なし</p>"
        return "<ul>" + "".join(f"<li>{escape(str(x))}</li>" for x in items) + "</ul>"

    html_data = f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(course or "授業ノート")} - {lesson_date}</title>
<style>
body {{font-family:-apple-system,BlinkMacSystemFont,"Noto Sans JP",sans-serif;
      background:#f5f6f8;color:#222;line-height:1.75;margin:0;padding:16px;}}
main {{max-width:720px;margin:auto;background:white;border-radius:18px;padding:22px;
       box-shadow:0 2px 12px rgba(0,0,0,.08);}}
h1 {{font-size:24px;margin:0 0 4px;}}
.meta {{color:#666;font-size:14px;margin-bottom:22px;}}
section {{margin-top:24px;}}
h2 {{font-size:19px;border-bottom:1px solid #ddd;padding-bottom:6px;}}
ul {{padding-left:24px;}}
li {{margin:7px 0;}}
.summary {{background:#f0f4f8;border-radius:12px;padding:14px;}}
.transcript {{white-space:pre-wrap;background:#fafafa;border-radius:12px;padding:14px;
             font-size:14px;}}
.empty {{color:#888;}}
@media print {{
  body {{background:white;padding:0;}}
  main {{box-shadow:none;}}
}}
</style>
</head>
<body>
<main>
<h1>📚 {escape(course or "授業ノート")}</h1>
<div class="meta">
先生：{escape(teacher or "未入力")}<br>
日付：{lesson_date}
</div>

<section>
<h2>💡 要約</h2>
<div class="summary">{escape(note["summary"])}</div>
</section>

<section><h2>⭐ 重要ポイント</h2>{html_list(note["important"])}</section>
<section><h2>📚 授業の流れ</h2>{html_list(note["topics"])}</section>
<section><h2>🔤 重要語句</h2>{html_list(note["terms"])}</section>
<section><h2>📝 課題・提出物</h2>{html_list(note["assignments"])}</section>
<section><h2>❓ 復習ポイント</h2>{html_list(note["review"])}</section>

<section>
<h2>📄 元の文字起こし</h2>
<div class="transcript">{escape(st.session_state.transcript or "")}</div>
</section>
</main>
</body>
</html>"""

    st.divider()
    st.subheader("💾 保存")

    st.download_button(
        "📖 見やすいノートとして保存（HTML）",
        data=html_data,
        file_name=f"{lesson_date}_{course or '授業'}_note.html",
        mime="text/html",
        use_container_width=True,
    )

    st.download_button(
        "📦 データとして保存（JSON）",
        data=json_data,
        file_name=f"{lesson_date}_{course or '授業'}_note.json",
        mime="application/json",
        use_container_width=True,
    )

    st.caption("HTMLはスマホのブラウザで開くと、JSONの記号ではなく普通の授業ノートとして読めます。")
