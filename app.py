import streamlit as st
import requests
import os

API_URL = os.getenv("API_URL", "http://localhost:8000/ask")

st.set_page_config(page_title="GovPulse Client", page_icon="🏛️", layout="wide")
st.markdown("<style>.stChatInput {border-radius: 10px;} h1 {color: #003057;}</style>", unsafe_allow_html=True)

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Flag_of_Scotland.svg/320px-Flag_of_Scotland.svg.png", width=60)
    st.title("🏛️ GovPulse")
    st.caption("v4.0 | Enterprise API Client")
    st.divider()
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

st.title("🏛️ GovPulse: Policy & Data Assistant")
st.markdown("Secure Interface for **GovPulse API**.")

if "messages" not in st.session_state: st.session_state.messages = []

col1, col2, col3 = st.columns(3)
query = None
if col1.button("📊 Glasgow Deprivation"): query = "Most deprived areas in Glasgow"
if col2.button("🔍 Hyndland Rank"): query = "Rank of Hyndland"
if col3.button("📜 Policy Summary"): query = "Summarize industrial strategy"

if chat_input := st.chat_input("Ask a question..."):
    query = chat_input

if query:
    st.session_state.messages.append({"role": "user", "content": query})
    for msg in st.session_state.messages:
        avatar = "🧑‍💻" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Connecting to Secure API..."):
            try:
                payload = {"query": query}
                response = requests.post(API_URL, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    answer = data["response"]
                    if data["redacted_query"] != query:
                        st.caption(f"🛡️ PII Redacted. Processed as: '{data['redacted_query']}'")
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                    
                    st.write("---")
                    c1, c2 = st.columns([1, 5])
                    with c1:
                        if st.button("👍"):
                            requests.post(f"{API_URL.replace('/ask', '')}/feedback", json={"query": query, "response": answer, "rating": "positive"})
                            st.toast("Feedback Saved")
                    with c2:
                        if st.button("👎"):
                            requests.post(f"{API_URL.replace('/ask', '')}/feedback", json={"query": query, "response": answer, "rating": "negative"})
                            st.toast("Issue Logged")
                else:
                    st.error(f"API Error: {response.text}")
            except Exception as e:
                st.error(f"Connection Error: {e}")
