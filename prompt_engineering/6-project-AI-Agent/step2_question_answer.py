from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY') 


client = OpenAI(api_key=OPENAI_API_KEY)

# system prompt defines the behavior, personality, and rules of the AI.
system_prompt = """
You are an experienced technical HR interviewer.

You are interviewing a candidate for a Python Developer role.

Your behavior:
- Ask only ONE question at a time
- The question must be conceptual (not coding)
- The question should test understanding of Python fundamentals
- Keep the question clear and concise
- Do not provide explanations or answers
"""

question_prompt = """Generate one Python interview question.

Constraints:
- The question should be suitable for an entry to mid-level Python developer
"""


response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question_prompt}
    ]
)

question = response.choices[0].message.content
print(question)


# Step 2: User answer
answer = input("Your Answer: ")

# Step 3: Evaluate answer
evaluation_prompt = f"""
You are a Python technical interviewer.

Evaluate the candidate's answer to the interview question.

Question:
{question}

Candidate Answer:
{answer}

Evaluation Criteria:
1. Technical correctness
2. Clarity of explanation
3. Completeness of the answer
4. Understanding of Python concepts

Return ONLY the following fields in this exact format:

Score: <score out of 10>

Strengths:
- Mention what the candidate answered correctly.

Weaknesses:
- Mention what was missing or incorrect.
"""

response2 = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role":"user","content":evaluation_prompt}]
)

print(response2.choices[0].message.content)


# What is the difference between a list and a tuple in Python?
# Your Answer: List are defined using square bracket[], where as tuple are defined using round bracket (). List elements can be modified. Tuple elements cannot be modified. Tuples are immutable. List has lot many methods available for operation, whereas tuples has 2 or 3 methods available
# Score: 8 out of 10

# Strengths:
# - The candidate correctly identified the syntax differences between lists and tuples and noted that lists are mutable while tuples are immutable.

# Weaknesses:
# - The candidate could have elaborated on the implications of mutability and immutability, such as performance benefits of tuples in certain contexts. Additionally, stating that tuples have only "2 or 3 methods" is somewhat vague; they could have specified common tuple methods like `count()` and `index()`.        
