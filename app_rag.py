from agentic_chatbot_rag_backend import (
    chatbot,
    get_all_threads,
    ingest_rag_document,
    delete_thread_from_db
)
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from streamlit_mic_recorder import mic_recorder
import streamlit as st
import uuid
import tempfile
import whisper
from gtts import gTTS
import os

st.set_page_config(
    page_title="AgentFlow AI",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def load_whisper():
    return whisper.load_model("tiny")

whisper_model = load_whisper()

if "chat_threads" not in st.session_state:
    st.session_state["chat_threads"] = get_all_threads() or []

if "uploaded_docs" not in st.session_state:
    st.session_state["uploaded_docs"] = set()

# ========================= Document Upload =========================

st.sidebar.markdown("---")
st.sidebar.subheader("📄 Upload Document")

uploaded_file = st.sidebar.file_uploader(
    "Choose a PDF",
    type=["pdf"]
)

if uploaded_file is not None:

    if uploaded_file.name not in st.session_state["uploaded_docs"]:

        try:

            with st.sidebar:
                with st.spinner("Processing PDF..."):

                    with tempfile.NamedTemporaryFile(
                        delete=False,
                        suffix=".pdf"
                    ) as tmp_file:

                        tmp_file.write(
                            uploaded_file.getbuffer()
                        )

                        temp_path = tmp_file.name

                    ingest_rag_document(temp_path)

                    st.session_state[
                        "uploaded_docs"
                    ].add(uploaded_file.name)

                    os.remove(temp_path)

                    st.success(
                        f"✅ {uploaded_file.name} uploaded successfully"
                    )

        except Exception as e:

            st.error(
                f"Upload failed: {str(e)}"
            )

if st.session_state["uploaded_docs"]:

    st.sidebar.markdown("### 📚 Knowledge Base")

    for doc in st.session_state["uploaded_docs"]:

        st.sidebar.write(f"📄 {doc}")

st.sidebar.markdown("---")

st.markdown("""
<style>

/* Hide Streamlit branding only */
#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

/* DO NOT hide header */
/* header {visibility:hidden;} */

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: #161A23;
    min-width: 320px !important;
    max-width: 320px !important;
}

/* Chat messages */
[data-testid="stChatMessage"] {
    border-radius: 16px;
    padding: 12px;
    margin-bottom: 10px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    backdrop-filter: blur(10px);
}

/* Buttons */
.stButton > button {
    width: 100%;
    border-radius: 12px;
}

/* Sidebar buttons */
section[data-testid="stSidebar"] .stButton > button {
    text-align: left;
}

/* Main title */
.main-title {
    text-align: center;
    font-size: 2.5rem;
    font-weight: 700;
    margin-bottom: 0.2rem;
}

/* Sidebar scrollbar */
section[data-testid="stSidebar"]::-webkit-scrollbar {
    width: 6px;
}

section[data-testid="stSidebar"]::-webkit-scrollbar-thumb {
    background: #444;
    border-radius: 10px;
}

</style>
""", unsafe_allow_html=True)

voice_enabled = st.sidebar.checkbox(
    "🔊 Voice Mode",
    value=False
)

# ========================= Utility Functions =========================

def generate_thread_id():
    return str(uuid.uuid4())


def add_thread(thread_id):
    if thread_id not in st.session_state["chat_threads"]:
        st.session_state["chat_threads"].append(thread_id)
        
def delete_thread(thread_id):

    delete_thread_from_db(thread_id)

    if thread_id in st.session_state["chat_threads"]:
        st.session_state["chat_threads"].remove(thread_id)

    if st.session_state["thread_id"] == thread_id:

        st.session_state["thread_id"] = generate_thread_id()
        st.session_state["message_history"] = []

        add_thread(st.session_state["thread_id"])


def reset_chat():
    st.session_state["thread_id"] = generate_thread_id()
    st.session_state["message_history"] = []
    add_thread(st.session_state["thread_id"])


def load_conversation(thread_id):

    state = chatbot.get_state(
        config={
            "configurable": {
                "thread_id": thread_id
            }
        }
    )

    return state.values.get("messages", [])


def get_thread_title(thread_id):

    messages = load_conversation(thread_id)

    for message in messages:

        if isinstance(message, HumanMessage):

            title = message.content.strip()

            if len(title) > 30:
                title = title[:30] + "..."

            return f" {title}"

    return "🆕 New Chat"


# ========================= Header =========================

st.markdown("""
<div class='main-title'>
🤖 AgentFlow AI
</div>
""", unsafe_allow_html=True)

st.caption("Powered by LangGraph • Groq • Streamlit")

# ========================= Session State =========================

if "message_history" not in st.session_state:
    st.session_state["message_history"] = []

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generate_thread_id()

if "chat_threads" not in st.session_state:
    st.session_state["chat_threads"] = get_all_threads() or []

if "uploaded_docs" not in st.session_state:
    st.session_state["uploaded_docs"] = set()
    
if "last_audio_id" not in st.session_state:
    st.session_state["last_audio_id"] = None
    
if "voice_input" not in st.session_state:
    st.session_state["voice_input"] = None

add_thread(st.session_state["thread_id"])

# ========================= Sidebar =========================

st.sidebar.markdown("## Chats")
st.sidebar.caption("Conversation History")

if st.sidebar.button("➕ New Chat", use_container_width=True):
    reset_chat()
    st.rerun()

for thread_id in st.session_state["chat_threads"][::-1]:

    title = get_thread_title(thread_id)

    col1, col2 = st.sidebar.columns([5, 1])

    with col1:
        if st.button(
            title,
            key=f"chat_{thread_id}",
            use_container_width=True
        ):

            st.session_state["thread_id"] = thread_id

            messages = load_conversation(thread_id)

            temp_messages = []

            for message in messages:

                if isinstance(message, HumanMessage):
                    role = "user"

                elif isinstance(message, AIMessage):
                    role = "assistant"

                else:
                    continue

                temp_messages.append({
                    "role": role,
                    "content": message.content
                })

            st.session_state["message_history"] = temp_messages

            st.rerun()

    with col2:
        if st.button(
            "🗑",
            key=f"delete_{thread_id}"
        ):

            delete_thread(thread_id)
            st.rerun()

# ========================= Welcome Screen =========================

if len(st.session_state["message_history"]) == 0:

    st.markdown("""
    ## 👋 Welcome

    Ask me anything about:

    - 💻 Programming
    - 🤖 Artificial Intelligence
    - 🔗 LangGraph
    - 🗄️ Databases
    - ☁️ Cloud Computing
    - 📚 General Knowledge

    Start by typing a message below.
    """)

# ========================= Chat Window =========================

for message in st.session_state["message_history"]:

    avatar = "👨‍💻" if message["role"] == "user" else "🤖"

    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

st.markdown("""
<style>

.voice-float {
    position: fixed;
    bottom: 18px;
    right: 85px;
    z-index: 9999;
}

</style>
""", unsafe_allow_html=True)

col1, col2 = st.columns([20, 1])

with col1:
    user_input = st.chat_input(
        "Ask me anything..."
    )

with col2:
    audio = mic_recorder(
        start_prompt="၊၊||၊",
        stop_prompt="◼",
        key="voice_recorder"
    )

voice_text = None

audio_id = audio.get("id") if audio else None

if (
    audio
    and audio_id != st.session_state["last_audio_id"]
):

    st.session_state["last_audio_id"] = audio_id

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".wav"
    ) as f:

        f.write(audio["bytes"])
        audio_path = f.name

    try:

        result = whisper_model.transcribe(
            audio_path
        )

        voice_text = result["text"]

        st.session_state["voice_input"] = voice_text
        
        st.session_state["last_was_voice"] = True

        st.success(
            f"🎤 You said: {voice_text}"
        )

    except Exception as e:

        st.error(
            f"Speech recognition failed: {str(e)}"
        )

    finally:

        if os.path.exists(audio_path):
            os.remove(audio_path)

if (
    not user_input
    and st.session_state["voice_input"]
):

    user_input = st.session_state["voice_input"]

    st.session_state["voice_input"] = None

if user_input:

    st.session_state["message_history"].append(
        {
            "role": "user",
            "content": user_input
        }
    )

    with st.chat_message("user", avatar="👨‍💻"):
        st.markdown(user_input)

    CONFIG = {
        "configurable": {
            "thread_id": st.session_state["thread_id"]
        },
        "metadata": {
            "thread_id": st.session_state["thread_id"]
        },
        "run_name": "chat_trace"
    }

    with st.chat_message("assistant", avatar="🤖"):

        status_box = st.status(
            "🤖 Processing your request...",
            expanded=True
        )

        for event in chatbot.stream(
            {
                "messages": [
                    HumanMessage(content=user_input)
                ]
            },
            config=CONFIG,
            stream_mode="updates"
        ):

            # LLM node updates
            if "chat_node" in event:

                messages = event["chat_node"].get(
                    "messages",
                    []
                )

                if messages:

                    last_msg = messages[-1]

                    if isinstance(last_msg, AIMessage):

                        if getattr(last_msg, "tool_calls", None):

                            status_box.write(
                                "🤔 Deciding which tool to use..."
                            )

                        else:

                            status_box.write(
                                "✍️ Generating final answer..."
                            )

            # Tool node updates
            if "tools" in event:

                status_box.write(
                    "🌐 Calling tool..."
                )

                tool_messages = event["tools"].get(
                    "messages",
                    []
                )

                for msg in tool_messages:

                    if isinstance(msg, ToolMessage):

                        status_box.write(
                            f"✅ Tool: {msg.name}"
                        )

                        with st.expander(
                            f"View {msg.name} output"
                        ):
                            st.code(
                                str(msg.content)[:1000]
                            )

        # Fetch final answer from memory
        state = chatbot.get_state(CONFIG)

        messages = state.values.get(
            "messages",
            []
        )

        if messages:
            ai_message = messages[-1].content
        else:
            ai_message = "No response generated."

        status_box.update(
            label="✅ Tool execution completed",
            state="complete",
            expanded=False
        )

        st.markdown(ai_message)
        
    if voice_enabled and st.session_state.get("last_was_voice", False):

        tts = gTTS(ai_message)

        tts.save("response.mp3")

        with open("response.mp3", "rb") as f:
            audio_bytes = f.read()

        import base64

        audio_base64 = base64.b64encode(audio_bytes).decode()

        st.markdown(
            f"""
            <audio autoplay>
                <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
            </audio>
            """,
            unsafe_allow_html=True
        )

        os.remove("response.mp3")

    st.session_state["message_history"].append(
        {
            "role": "assistant",
            "content": ai_message
        }
)