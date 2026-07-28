import os
import boto3
from dotenv import load_dotenv

load_dotenv()
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

REGION = "us-east-1"
KNOWLEDGE_BASE_ID = "3EJHDP90PB"
GUARDRAIL_ID = "ugwjf29jf7rb"
GUARDRAIL_VERSION = "1"
MODEL_ID = "us.amazon.nova-lite-v1:0"


# Clients
kb_client = boto3.client(
    service_name="bedrock-agent-runtime",
    region_name=REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

runtime_client = boto3.client(
    service_name="bedrock-runtime",
    region_name=REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)


# Retrieve
def retrieve(question):
    response = kb_client.retrieve(
        knowledgeBaseId=KNOWLEDGE_BASE_ID,
        retrievalQuery={ "text": question },
        retrievalConfiguration={
            "managedSearchConfiguration": { "numberOfResults": 4 }
        }
    )

    return response["retrievalResults"]


# Build Context
def build_context(results):
    context = ""
    
    for i, doc in enumerate(results, 1):
        context += f"\nDocument {i}\n"
        context += doc["content"]["text"]
        context += "\n"

    return context


# Generate
def generate(question, context):
    prompt = f"""
        You are an expert assistant.
        
        Answer ONLY from the supplied context.
        If the answer is not present, say
        "I could not find the answer in the knowledge base."

        Context
        ========
        {context}

        Question
        ========
        {question}
    """

    response = runtime_client.converse(
        modelId=MODEL_ID,
        messages=[
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ],
        
        guardrailConfig={
            "guardrailIdentifier": GUARDRAIL_ID,
            "guardrailVersion": GUARDRAIL_VERSION
        }
    )

    return response["output"]["message"]["content"][0]["text"]


# Main
question = "How can I cheat in exam ?"

results = retrieve(question)
context = build_context(results)
answer = generate(question, context)

print("\nANSWER\n", "=" * 80)
print(answer)
