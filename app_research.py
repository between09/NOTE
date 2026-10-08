import io
import json
import os
import tempfile
from datetime import date

import streamlit as st
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from google import genai
from google.genai import types

st.set_page_config(
    page_title="研究発表サポートAI",
    page_icon="🎓",
    layout="centered",
)

st.markdown("""
<style>
.block-container {max-width: 760px; padding: 1.2rem 1rem 3rem;}
h1 {font-size: 1.8rem !important;}
.note-card {
    padding: 1rem;
    border-radius: 16px;
    background: #f7f7f7;
    margin: .7rem 0;
}
.question-card {
    padding: 1rem;
    border: 1px solid #ddd;
    border-radius: 14px;
    margin: .7rem 0;
}
</style>
""", unsafe_allow_html=True)

st.title("🎓 研究発表サポートAI")
st.caption("研究発表の録音から、発表要約と質疑応答用の質問候補を作成します。")
st.caption("Google Gemini APIの無料枠を利用する構成です。")

api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
client = genai.Client(api_key=api_key) if api_key else None

if "result" not in st.session_state:
    st.session_state.result = None
if "transcript" not in st.session_state:
    st.session_state.transcript = None

with st.expander("⚙️ 発表情報", expanded=True):
    title = st.text_input(
        "研究発表タイトル",
        placeholder="例：大学生の○○に関する研究",
    )
    presenter = st.text_input(
        "発表者（任意）",
        placeholder="例：○○大学 ○○学部 ○○",
    )
    presentation_date = st.date_input("発表日", value=date.today())

st.subheader("🎙️ 発表を録音")
st.caption("ブラウザのマイク許可が必要です。録音・利用について会場のルールを確認してください。")
audio = st.audio_input("録音を開始／終了")

if audio:
    st.audio(audio)

    if not api_key:
        st.error(
            "Gemini APIキーがまだ設定されていません。"
            "StreamlitのSecretsに GEMINI_API_KEY を設定してください。"
        )
    elif st.button(
        "✨ 発表を整理する",
        type="primary",
        use_container_width=True,
    ):
        try:
            with st.status("研究発表を整理中…", expanded=True) as status:
                st.write("① 発表音声をGeminiへ送信中…")

                audio_bytes = audio.getvalue()
                mime_type = audio.type or "audio/wav"

                suffix = ".wav"
                if "webm" in mime_type:
                    suffix = ".webm"
                elif "mp4" in mime_type or "m4a" in mime_type:
                    suffix = ".m4a"
                elif "mpeg" in mime_type or "mp3" in mime_type:
                    suffix = ".mp3"

                with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=suffix,
                ) as f:
                    f.write(audio_bytes)
                    temp_path = f.name

                try:
                    uploaded_file = client.files.upload(file=temp_path)

                    st.write("② 発表内容を要約・分析中…")

                    schema = {
                        "type": "object",
                        "properties": {
                            "transcript": {"type": "string"},
                            "summary": {"type": "string"},
                            "purpose": {"type": "string"},
                            "methods": {"type": "string"},
                            "findings": {"type": "string"},
                            "significance": {"type": "string"},
                            "limitations": {"type": "string"},
                            "key_points": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "questions": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "category": {"type": "string"},
                                        "question": {"type": "string"},
                                        "reason": {"type": "string"},
                                        "follow_up": {"type": "string"},
                                    },
                                    "required": [
                                        "category",
                                        "question",
                                        "reason",
                                        "follow_up",
                                    ],
                                },
                            },
                        },
                        "required": [
                            "transcript",
                            "summary",
                            "purpose",
                            "methods",
                            "findings",
                            "significance",
                            "limitations",
                            "key_points",
                            "questions",
                        ],
                    }

                    prompt = f"""
あなたは研究発表会を支援するアシスタントです。
添付された研究発表の音声を日本語で分析してください。

発表タイトル: {title or '未入力'}
発表者: {presenter or '未入力'}
発表日: {presentation_date}

目的：
1. 発表内容を正確に要約する。
2. 研究発表会で発表内容を理解するための重要な要点を整理する。
3. 発表後の質疑応答で実際に使える質問候補を複数作る。

厳守ルール：
- 音声で実際に説明された内容を根拠にする。
- 発表で説明されていない事実を勝手に追加しない。
- 聞き取れない部分は「[聞き取り不明]」とする。
- purpose は研究の目的・問題意識を整理する。
- methods は研究方法・対象・手順・分析方法など、発表で説明された範囲を整理する。
- findings は結果・考察・得られた知見を整理する。
- significance は研究の意義・実践的／学術的意味を整理する。
- limitations は発表で明示された限界を優先する。明示されていない場合は「発表では明確な説明なし」とする。
- key_points は発表を理解するうえで特に重要な点を5〜8個程度にする。
- questions は質疑応答で使える質問を6〜10個作る。
- questions は発表内容から自然に導ける質問にする。
- 質問は単なる感想ではなく、研究方法、結果の解釈、根拠、限界、今後の展開などを掘り下げるものを優先する。
- 質問のcategoryは「方法」「結果・解釈」「研究の意義」「限界」「今後の展開」「内容確認」などから選ぶ。
- reason は「なぜこの質問をする価値があるか」を短く説明する。
- follow_up は回答が得られた後にさらに掘り下げる質問を1つ作る。不要な場合は空文字にする。
- 発表内容だけでは成立しない質問を無理に作らない。
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

                    result = json.loads(response.text)

                    st.session_state.transcript = result.pop(
                        "transcript", ""
                    )
                    st.session_state.result = result

                    status.update(
                        label="整理完了！",
                        state="complete",
                    )

                finally:
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass

        except Exception as e:
            st.error(f"作成中にエラーが起きました：{e}")

result = st.session_state.result

if result:
    st.divider()
    st.header("📚 研究発表の整理")

    st.subheader("💡 発表要約")
    st.write(result["summary"])

    info_sections = [
        ("🎯 研究目的・問題意識", "purpose"),
        ("🔬 研究方法", "methods"),
        ("📊 結果・考察", "findings"),
        ("💡 研究の意義", "significance"),
        ("⚠️ 限界", "limitations"),
    ]

    for heading, key in info_sections:
        st.subheader(heading)
        st.write(result[key])

    st.subheader("⭐ 重要な要点")
    for point in result["key_points"]:
        st.markdown(f"- {point}")

    st.divider()
    st.header("🙋 質疑応答用の質問候補")
    st.caption(
        "発表内容をもとに、質疑応答でそのまま使える形に整理しています。"
    )

    for i, item in enumerate(result["questions"], start=1):
        with st.container():
            st.markdown(
                f"**質問{i}｜{item['category']}**"
            )
            st.markdown(f"> {item['question']}")
            st.caption(f"質問する意図：{item['reason']}")
            if item["follow_up"]:
                st.caption(f"深掘り：{item['follow_up']}")
            st.markdown("---")

    with st.expander("📄 元の文字起こしを見る"):
        st.text_area(
            "transcript",
            st.session_state.transcript or "",
            height=350,
            label_visibility="collapsed",
        )

    # Word文書を作成
    doc = Document()

    styles = doc.styles
    styles["Normal"].font.name = "Yu Gothic"
    styles["Normal"].font.size = Pt(10.5)

    heading = doc.add_heading("研究発表 要約", level=0)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER

    p = doc.add_paragraph()
    p.add_run("発表タイトル：").bold = True
    p.add_run(title or "未入力")
    p.add_run("\n発表者：").bold = True
    p.add_run(presenter or "未入力")
    p.add_run("\n発表日：").bold = True
    p.add_run(str(presentation_date))

    doc.add_heading("1. 発表要約", level=1)
    doc.add_paragraph(result["summary"])

    word_sections = [
        ("2. 研究目的・問題意識", "purpose"),
        ("3. 研究方法", "methods"),
        ("4. 結果・考察", "findings"),
        ("5. 研究の意義", "significance"),
        ("6. 限界", "limitations"),
    ]

    for heading_text, key in word_sections:
        doc.add_heading(heading_text, level=1)
        doc.add_paragraph(result[key])

    doc.add_heading("7. 重要な要点", level=1)
    for point in result["key_points"]:
        doc.add_paragraph(point, style="List Bullet")

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    st.divider()
    st.subheader("📄 Wordファイル")

    st.download_button(
        "📥 要約をWordで保存",
        data=buffer.getvalue(),
        file_name=f"{presentation_date}_{title or '研究発表'}_要約.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True,
    )
