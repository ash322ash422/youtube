# app_v1.py

import streamlit as st
import pandas as pd

from langchain_openai import ChatOpenAI
from langchain_experimental.agents import create_pandas_dataframe_agent

# -------------------------
# STREAMLIT UI
# -------------------------
st.set_page_config(page_title="Data Agent App", layout="wide")
st.title("📊 LLM-Powered Data Analysis")

# -------------------------
# SIDEBAR (API KEY)
# -------------------------
st.sidebar.header("Settings")

api_key = st.sidebar.text_input("Enter OpenAI API Key", type="password")

if not api_key:
    st.warning("Please enter your OpenAI API key in the sidebar")
    st.stop()

# -------------------------
# INITIALIZE LLM
# -------------------------
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    openai_api_key=api_key
)

# -------------------------
# FILE UPLOAD
# -------------------------
uploaded_file = st.file_uploader("Upload CSV", type=["csv",])

if uploaded_file:
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        st.write("### Data Preview:")
        st.dataframe(df.head())

        # -------------------------
        # USER QUERY
        # -------------------------
        user_query = st.text_input("Ask a question about your data:")

        if user_query:
            agent = create_pandas_dataframe_agent(
                llm,
                df,
                verbose=True,
                allow_dangerous_code=True
            )

            with st.spinner("Analyzing your data..."):
                result = agent.invoke(user_query)

            st.write("### Result:")
            st.write(result)

    except Exception as e:
        st.error(f"Error: {e}")
