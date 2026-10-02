import os, json
from datetime import date
import streamlit as st
from openai import OpenAI

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

api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
client = OpenAI(api_key=api_key) if api_key else None

if "note" not in st.session_state:
    st.session_state.note = None
if "transcript" not in st.session_state:
    st.session_state.transcript = None

with st.expander("⚙️ 授業情報", expanded=True):
    course = st.text_input("授業名", placeholder="例：特別支援教育論")
    teacher = st.text_input("先生（任意）", placeholder="例：○○先生")
    lesson_date = st.date_input("日付", value=date.today())

st.subheader("🎙️ 授業を録音")
st.caption("ブラウザのマイク許可が必要です。授業の録音ルールも確認してね。")
audio = st.audio_input("録音を開始／終了")

if audio:
    st.audio(audio)
    if not api_key:
        st.error("OpenAI APIキーがまだ設定されていません。READMEのセットアップ手順を確認してください。")
    elif st.button("✨ この授業をノートにする", type="primary", use_container_width=True):
        try:
            with st.status("授業ノートを作成中…", expanded=True) as status:
                st.write("① 音声を文字起こし中…")
                audio_bytes = audio.getvalue()
                transcription = client.audio.transcriptions.create(
                    model="gpt-4o-transcribe",
                    file=("lesson.wav", audio_bytes, audio.type or "audio/wav"),
                    response_format="text",
                )
                transcript = transcription.text
                st.session_state.transcript = transcript

                st.write("② 授業内容を整理中…")
                schema = {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "important": {"type": "array", "items": {"type": "string"}},
                        "topics": {"type": "array", "items": {"type": "string"}},
                        "terms": {"type": "array", "items": {"type": "string"}},
                        "assignments": {"type": "array", "items": {"type": "string"}},
                        "review": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["summary","important","topics","terms","assignments","review"],
                    "additionalProperties": False
                }
                prompt = f"""大学の授業ノートを作成してください。
授業名: {course or '未入力'}
先生: {teacher or '未入力'}
日付: {lesson_date}

文字起こし:
--- 
{transcript}
---

ルール:
- 文字起こしにない事実を作らない。
- 「先生が言ったこと」と「AIの推測」を混ぜない。
- 課題や提出期限は、明確に出ているものだけ書く。
- 不明瞭な箇所は無理に補完しない。
- important は先生が強調・繰り返し説明した内容を優先。
- review は授業内容から復習価値のある点を整理する。
- terms は専門用語と授業内での説明を短くまとめる。
"""
                response = client.responses.create(
                    model=os.getenv("OPENAI_TEXT_MODEL", "gpt-5-mini"),
                    instructions="あなたは正確な大学授業ノート整理アシスタントです。出力は指定JSONだけにしてください。",
                    input=prompt,
                    text={"format": {"type": "json_schema", "name": "class_note", "schema": schema, "strict": True}},
                )
                note = json.loads(response.output_text)
                st.session_state.note = note
                status.update(label="完成！", state="complete")
        except Exception as e:
            st.error(f"作成中にエラーが起きました：{e}")

note = st.session_state.note
if note:
    st.divider()
    st.header("📚 今日の授業ノート")
    st.subheader("💡 3〜6文まとめ")
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
        st.text_area("transcript", st.session_state.transcript or "", height=350, label_visibility="collapsed")

    if st.download_button(
        "📥 ノートを保存（JSON）",
        data=json.dumps({
            "course": course, "teacher": teacher, "date": str(lesson_date),
            "note": note, "transcript": st.session_state.transcript
        }, ensure_ascii=False, indent=2),
        file_name=f"{lesson_date}_{course or '授業'}_note.json",
        mime="application/json",
        use_container_width=True
    ):
        st.toast("保存したよ！")
