import os
import numpy as np
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
from pypdf import PdfReader

load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")  # Ensure this is in your .env

# Initialize clients
client = OpenAI(api_key=API_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)

# Define Index Configurations
INDEX_NAME = "pdf-rag-index"
DIMENSION = 1536  # Dimension for 'text-embedding-3-small'


# -------- READ PDF --------
def read_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


# -------- CHUNK TEXT --------
def chunk_text(text, size=300):
    return [text[i : i + size] for i in range(0, len(text), size)]


# -------- EMBEDDINGS --------
def embed(texts):
    response = client.embeddings.create(model="text-embedding-3-small", input=texts)
    return np.array([d.embedding for d in response.data]).astype("float32")


# -------- BUILD VECTOR DB (PINECONE) --------
def build_index(chunks):
    # 1. Create index if it doesn't exist
    if INDEX_NAME not in pc.list_indexes().names():
        pc.create_index(
            name=INDEX_NAME,
            dimension=DIMENSION,
            metric="cosine",  # Cosine is recommended for OpenAI embeddings
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )

    index = pc.Index(INDEX_NAME)

    # 2. Generate embeddings
    embeddings = embed(chunks)

    # 3. Format data for Pinecone upsert: (id, vector, metadata)
    vectors_to_upsert = []
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        vectors_to_upsert.append(
            {"id": f"chunk-{i}", "values": embedding.tolist(), "metadata": {"text": chunk}}
        )

    # 4. Upload to cloud
    index.upsert(vectors = vectors_to_upsert)
    return index


# -------- RETRIEVE --------
def retrieve(query, index, k=3):
    q_emb = embed([query])[0].tolist()

    # Query Pinecone and request metadata to get the original text back
    results = index.query(vector=q_emb, top_k=k, include_metadata=True)

    return [match["metadata"]["text"] for match in results["matches"]]


# -------- ASK LLM --------
def ask_llm(question, context):
    prompt = f"""
    Answer using the context below. Keep it short.

    Context:
    {context}

    Question: {question}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content
