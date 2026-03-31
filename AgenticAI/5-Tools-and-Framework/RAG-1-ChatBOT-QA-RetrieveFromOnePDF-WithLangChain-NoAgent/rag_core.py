# rag_core.py

from langchain_community.document_loaders import PyPDFLoader # install pypdf
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS # install faiss-gpu

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
import tempfile

# -------- LOAD + SPLIT --------
def load_and_split_pdfs(files):
    all_docs = []

    for file in files:
        # Handle both Streamlit file and local file
        if hasattr(file, "read"):
            # Streamlit file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file.read())
                file_path = tmp.name
        else:
            # Local file path
            file_path = file

        loader = PyPDFLoader(file_path)
        docs = loader.load()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )

        split_docs = splitter.split_documents(docs)
        all_docs.extend(split_docs)

    return all_docs

# -------- BUILD VECTOR STORE --------
def build_vector_store(docs, api_key):
    embeddings = OpenAIEmbeddings(openai_api_key=api_key)

    vectorstore = FAISS.from_documents(docs, embeddings)

    return vectorstore


# -------- RETRIEVER --------
def get_retriever(vectorstore):
    return vectorstore.as_retriever(search_kwargs={"k": 3})


# -------- ASK LLM --------
def ask_llm(question, retriever, api_key):
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=api_key
    )

    docs = retriever.invoke(question)

    context = "\n\n".join([doc.page_content for doc in docs])

    prompt = f"""
    Answer using the context below. Keep it short.

    Context:
    {context}

    Question: {question}
    """

    response = llm.invoke(prompt)

    return response.content, docs

############################################
if __name__ == "__main__":

    import os

    #  Set your API key here (temporary for testing)
    api_key = "key_here"

    #  Provide path to a local PDF
    test_pdf = "document-loxford-company.pdf"

    if not os.path.exists(test_pdf):
        print(" PDF file not found. ")
        exit()

    print(" Loading and splitting PDF...")
    docs = load_and_split_pdfs([open(test_pdf, "rb")])

    print(f" Total chunks created: {len(docs)}")

    print(" Building vector store...")
    vectorstore = build_vector_store(docs, api_key)

    retriever = get_retriever(vectorstore)

    # Test question
    question = "What is this document about?"

    print(f"\n Question: {question}")

    answer, retrieved_docs = ask_llm(question, retriever, api_key)

    print("\n Retrieved Chunks:")
    for i, d in enumerate(retrieved_docs):
        print(f"\n--- Chunk {i+1} ---")
        print(d.page_content[:200])

    print("\n Final Answer:")
    print(answer)
