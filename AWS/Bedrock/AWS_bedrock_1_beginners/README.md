# Amazon Bedrock for Beginners – From First Prompt to AI Agent for RAG

This repo contains code samples that take you from your first Bedrock API call to a fully working AI agent. By the end, you'll build a university FAQ chatbot that uses a Knowledge Base for RAG, Guardrails for content safety, a custom tool for course lookups, and the Strands Agents SDK to tie it all together.

## Prerequisites

-  **Note:** You will need to create an IAM Role or user in your account to follow along, you cannot complete the tutorial using the root user.

## Step 1: Install Dependencies

Create a virtual environment and install the required packages:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Project Structure

```
├── example_codes/                  
│   ├── 01_converse_api.py                      # Converse API basics + system prompts
│   ├── 02_multi_turn.py                        # Multi-turn conversation history
│   ├── 03_tool_using_assistant.py              # Tool use (function calling)
│   ├── 04_RAG_managed_knowledge_base_query.py  # RAG with Knowledge Bases
│   ├── 05_guardrails.py                        # Guardrails + Knowledge Base
│   └── 06_strands_agent.py                     # Capstone: university chatbot agent
│
├── knowledge_base_docs/       
│   ├── 01_history.txt
│   ├── 02_courses.txt
│   ├── 03_fiancial_aid.txt
│
├── requirements.txt
└── README.md
```


## Cleanup

To avoid ongoing charges, delete the resources you created. Follow this order since some resources depend on others.

### 1. Delete the Knowledge Base

1. Go to the [Bedrock console](https://console.aws.amazon.com/bedrock/) → **Knowledge bases**
2. Select your knowledge base 
3. Click **Delete**
4. Confirm the deletion

### 2. Delete the S3 Vectors Bucket

Bedrock created an S3 Vectors bucket when you set up the Knowledge Base. You need to empty it before you can delete it.

1. Go to the [S3 console](https://console.aws.amazon.com/s3/)
2. Find the S3 Vectors bucket (it will have a name like `bedrock-kb-...` or similar)
3. Select the bucket and click **Empty**
4. Type "permanently delete" to confirm, then click **Empty**
5. Once empty, go back to the bucket list, select the bucket again, and click **Delete**
6. Type the bucket name to confirm and click **Delete bucket**

### 3. Delete the FAQ Documents Bucket

1. In the S3 console, find the bucket you created for the FAQ files (e.g., `bedrock-university-faq-jd`)
2. Select the bucket and click **Empty**
3. Type "permanently delete" to confirm, then click **Empty**
4. Go back to the bucket list, select the bucket, and click **Delete**
5. Type the bucket name to confirm and click **Delete bucket**

### 4. Delete the Guardrail

1. Go to the [Bedrock console](https://console.aws.amazon.com/bedrock/) → **Guardrails**
2. Select your guardrail (`university-chatbot-guardrail`)
3. Click **Delete**
4. Confirm the deletion



### Reranking Options

Managed KBs use a service-managed reranker by default. You can customize this in the `managedSearchConfiguration`:
- `"rerankingModelType": "MANAGED"` (default) — automatic reranking, no config needed
- `"rerankingModelType": "NONE"` — disable reranking
- `"rerankingModelType": "CUSTOM"` — use your own Bedrock reranking model (e.g., Cohere Rerank v3.5)

## Resources

- [Amazon Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Bedrock Supported Models & IDs](https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids.html)
- [Bedrock Knowledge Bases Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)
- [Build a Managed Knowledge Base](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-build-managed.html)
- [Create a Managed Knowledge Base](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-managed-create.html)
- [Query a Knowledge Base (Retrieve API)](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-test-retrieve.html)
- [Agentic Retrieval](https://docs.aws.amazon.com/bedrock/latest/userguide/kb-test-agentic.html)
- [Bedrock Guardrails Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html)
- [Strands Agents SDK](https://strandsagents.com/)
- [Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)
