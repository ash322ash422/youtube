import streamlit as st
from step_2_agent_logic import create_agent

# -------------------------
# PAGE CONFIG
# -------------------------
st.set_page_config(page_title="AI Agent App", layout="wide")

st.title("🤖 AI Agent with Tools")

# -------------------------
# SIDEBAR
# -------------------------
st.sidebar.header("Settings")

api_key = st.sidebar.text_input("Enter OpenAI API Key", type="password")

if st.sidebar.button("Quit App"):
    st.warning("App stopped. Refresh to restart.")
    st.stop()

# -------------------------
# SESSION STATE
# -------------------------
if "agent" not in st.session_state and api_key:
    st.session_state.agent = create_agent(api_key)

if "messages" not in st.session_state:
    st.session_state.messages = []

# -------------------------
# DISPLAY CHAT
# -------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# -------------------------
# USER INPUT
# -------------------------
user_input = st.chat_input("Ask something...")

if user_input:
    if not api_key:
        st.error("Please enter your OpenAI API Key in the sidebar.")
    else:
        # Show user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)

        # Get response
        response = st.session_state.agent.invoke({"input": user_input})
        answer = response["output"]

        # Show assistant message
        st.session_state.messages.append({"role": "assistant", "content": answer})
        with st.chat_message("assistant"):
            st.write(answer)
