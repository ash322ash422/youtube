import streamlit as st
from rag_core import load_and_split_pdfs, build_vector_store, get_retriever, ask_llm

st.set_page_config(page_title="LangChain RAG App", layout="wide")

st.title(" LangChain Native RAG Chatbot")

# -------- SIDEBAR --------
st.sidebar.title("Settings")
api_key = st.sidebar.text_input("Enter OpenAI API Key", type="password")

if not api_key:
    st.warning("Please enter API key")
    st.stop()

# -------- FILE UPLOAD --------
uploaded_files = st.file_uploader(
    "Upload PDF(s)",
    type="pdf",
    accept_multiple_files=True
)

# -------- BUILD INDEX --------
if uploaded_files:
    if "retriever" not in st.session_state:
        with st.spinner("Processing PDFs..."):

            docs = load_and_split_pdfs(uploaded_files)
            vectorstore = build_vector_store(docs, api_key)
            retriever = get_retriever(vectorstore)

            st.session_state.retriever = retriever

        st.success("PDF(s) processed successfully!")

# -------- CHAT --------
question = st.chat_input("Ask a question")

if question:
    if "retriever" not in st.session_state:
        st.warning("Upload PDF first!")
        st.stop()

    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):

            answer, docs = ask_llm(
                question,
                st.session_state.retriever,
                api_key
            )
    
            # (OPTIONAL) If you want to see the chunks
            # st.write("### Retrieved Sources:")
            # for d in docs:
            #     st.write(f" Page {d.metadata.get('page', 'N/A')}")
            #     st.write(d.page_content[:300] + "...")

            st.write("### Final Answer:")
            st.write(answer)
