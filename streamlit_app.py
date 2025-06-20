import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(page_title="QueryNest AI", layout="wide")
st.title("🦊 QueryNest – Smart AI Assistant")

# Session message storage
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar Actions
st.sidebar.title("⚙️ Actions")
action = st.sidebar.radio("Choose Action", ["Chat", "Ask from PDF", "Web Search", "Weather Info"])

# Upload PDF
uploaded_file = st.sidebar.file_uploader("📄 Upload PDF", type=["pdf"])
if uploaded_file:
    with st.spinner("📤 Uploading PDF..."):
        response = requests.post(f"{API_URL}/upload_pdf", files={"file": uploaded_file})
        if response.status_code == 200:
            st.sidebar.success(response.json().get("message", "✅ PDF Uploaded"))
        else:
            st.sidebar.error("❌ Failed to upload PDF")

# Main input
user_input = st.text_input("Ask me anything...")

# Handle Send
if st.button("Send") and user_input.strip():
    st.session_state.messages.append({"sender": "user", "text": user_input})

    try:
        if action == "Chat":
            payload = {"question": user_input}
            res = requests.post(f"{API_URL}/chat", json=payload)
            reply = res.json().get("answer", "🤖 No response from backend.")
        
        elif action == "Ask from PDF":
            payload = {"question": user_input}
            res = requests.post(f"{API_URL}/ask_pdf", json=payload)
            reply = res.json().get("answer", "📄 No relevant PDF answer found.")
        
        elif action == "Web Search":
            res = requests.get(f"{API_URL}/web_search", params={"query": user_input})
            reply = res.json().get("result", "🌐 No web result.")
        
        elif action == "Weather Info":
            res = requests.get(f"{API_URL}/weather", params={"city": user_input})
            reply = res.json().get("weather", "🌦️ No weather info found.")
        
    except Exception as e:
        reply = f"❌ Error: {e}"

    st.session_state.messages.append({"sender": "bot", "text": reply})

# Display Chat History
st.markdown("### 💬 Chat History")
for msg in st.session_state.messages:
    if msg["sender"] == "user":
        st.markdown(f"🧑‍💻 **You:** {msg['text']}")
    else:
        st.markdown(f"🤖 **QueryNest:** {msg['text']}")
