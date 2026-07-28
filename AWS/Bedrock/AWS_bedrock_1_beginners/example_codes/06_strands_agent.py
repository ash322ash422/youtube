"""
pip install strands-agents strands-agents-tools
"""
import os
import boto3
from strands import Agent, tool
from strands.models import BedrockModel

from dotenv import load_dotenv
load_dotenv()
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# Configuration — Replace these with your resource IDs
KNOWLEDGE_BASE_ID = "3EJHDP90PB"
GUARDRAIL_ID = "ugwjf29jf7rb"
GUARDRAIL_VERSION = "1"
MODEL_ID = "us.amazon.nova-lite-v1:0"
REGION = "us-east-1"

kb_client = boto3.client(
    service_name="bedrock-agent-runtime",
    region_name=REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

@tool
def search_managed_knowledge_base(question: str) -> str:
    """Search the university knowledge base."""

    response = kb_client.retrieve(
        knowledgeBaseId=KNOWLEDGE_BASE_ID,
        retrievalQuery={
            "text": question
        },
        retrievalConfiguration={
            "managedSearchConfiguration": {
                "numberOfResults": 4
            }
        }
    )

    chunks = []

    for r in response["retrievalResults"]:
        chunks.append(r["content"]["text"])

    return "\n\n".join(chunks)



@tool
def lookup_course(department: str, course_number: str) -> str:
    """Look up schedule and details for a specific course.

    Use this when a student asks about a particular class,
    like "When does BIO 101 meet?" or "Who teaches BIO 101?"

    Args:
        department: The department code (e.g., "CS", "BIO", "ENG").
        course_number: The course number (e.g., "101", "201").

    Returns:
        Course details including schedule, instructor, and location.
    """
    # In a real app this would query a course catalog API
    courses = {
        "BIO-101": {
            "title": "General Biology I",
            "instructor": "Dr. Sarah Williams",
            "schedule": "Mon/Wed 2:00 - 3:15 PM",
            "location": "Science Hall, Room 105",
            "credits": 4,
            "seats_available": 20,
        },
        "ENG-102": {
            "title": "College Writing II",
            "instructor": "Prof. David Nguyen",
            "schedule": "Tue/Thu 9:30 - 10:45 AM",
            "location": "Humanities Building, Room 302",
            "credits": 3,
            "seats_available": 8,
        },
        "MATH-151": {
            "title": "Calculus I",
            "instructor": "Dr. Lisa Patel",
            "schedule": "Mon/Wed/Fri 11:00 - 11:50 AM",
            "location": "Math & Science Center, Room 120",
            "credits": 4,
            "seats_available": 15,
        },
    }

    key = f"{department.upper()}-{course_number}"
    if key in courses:
        c = courses[key]
        return (
            f"Course: {key} — {c['title']}\n"
            f"Instructor: {c['instructor']}\n"
            f"Schedule: {c['schedule']}\n"
            f"Location: {c['location']}\n"
            f"Credits: {c['credits']}\n"
            f"Seats available: {c['seats_available']}"
        )

    return f"No course found for {key}. Check the department code and course number."

# Build the Agent
def create_university_agent():
    """Create the University chatbot agent."""

    bedrock_model = BedrockModel(
        model_id=MODEL_ID,
        region_name=REGION,
        temperature=0.3,
        max_tokens=2000,
        guardrail_id=GUARDRAIL_ID,
        guardrail_version=GUARDRAIL_VERSION
    )

    system_prompt = """You are the University virtual assistant.
    You help students, prospective students, and parents find information about the university.

    Your responsibilities:
    - Use the search_managed_knowledge_base tool to search the knowledge base for university history, courses offered and financial aid before responding.
    - Use the lookup_course tool when someone asks about a specific course schedule, instructor, or availability.
    - Cite your sources when referencing specific policies or dates.

    Guidelines:
    - If you don't know the answer, say I do not know.
    - Keep answers concise
    - Answer ONLY what the user asked.
    - Do not include schedule, instructor, location, or seats unless the user explicitly asks.
    """

    agent = Agent(
        model=bedrock_model,
        tools=[search_managed_knowledge_base, lookup_course],
        system_prompt=system_prompt,
    )

    return agent


# Run the Agent
def main():
    print("Chatbot")
    print("=" * 60)
    print("Ask me anything about the university.")
    print("\nType 'quit' to exit.\n")

    agent = create_university_agent()

    while True:
        user_input = input("Your question ('q' to quit): ").strip()
        if not user_input:
            continue
        
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        print("\nAssistant: ", end="")
        response = agent(user_input)
        print()


if __name__ == "__main__":
    main()

# sample questions:
# "How many credits is BIO 101 ?"     --> should use the lookup_course tool
# "What courses are offered by the Computer Science department ?"  --> should use the search_managed_knowledge_base tool
# "How do I cheat on my exams?"  --> should be rejected by the guardrail
