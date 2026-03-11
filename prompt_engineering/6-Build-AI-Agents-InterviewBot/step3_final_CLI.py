from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY') 
client = OpenAI(api_key=OPENAI_API_KEY)

TOTAL_QUESTIONS = 2

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

questions_asked = []  # store previous questions
evaluations_of_questions = [] # store evaluation results

# Ask only 2 questions and evaluate these questions
for i in range(TOTAL_QUESTIONS): 

    question_prompt = f"""Generate one Python interview question.

    Constraints:
    - The question should be suitable for an entry to mid-level Python developer
    - Do NOT repeat any question from this list:
      {questions_asked}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"system","content":system_prompt},
            {"role":"user","content":question_prompt}
        ]
    )

    question = response.choices[0].message.content
    questions_asked.append(question)
    
    print("\nQuestion:", question)

    answer = input("Your Answer: ")

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

    evaluation = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":evaluation_prompt}]
    )

    print("\nFeedback:")
    evaluation_response = evaluation.choices[0].message.content
    evaluations_of_questions.append(evaluation_response)
    print(evaluation_response)

print("THANK YOU :)")
print("Questions:", questions_asked)
print("Evaluations:", evaluations_of_questions)



# Question: What is the difference between deep copy and shallow copy in Python?
# Your Answer: A shallow copy creates a new outer object, but the inner objects (nested objects) are still shared between the original and the copy. A deep copy creates a completely independent copy, including all nested objects.

# Feedback:
# Score: 8 out of 10

# Strengths:
# - The candidate accurately described the key difference between shallow and deep copies, highlighting that shallow copies share nested objects while deep copies create independent copies.

# Weaknesses:
# - The explanation could benefit from mentioning specific methods used to create these copies, such as `copy.copy()` for shallow copies and `copy.deepcopy()` for deep copies. Additionally, an example or clarification regarding the implications of modifying shared objects in shallow copies would enhance completeness.

# Question: What is the difference between a list and a tuple in Python, and when would you use one over the other?
# Your Answer: List are defined using square bracket[], where as tuple are defined using round bracket (). List elements can be modified. Tuple elements cannot be modified. Tuples are immutable. List has lot many methods available for operation, whereas tuples has 2 or 3 methods available

# Feedback:
# Score: 7 out of 10

# Strengths:
# - The candidate correctly identified the syntax for lists and tuples and that lists are mutable while tuples are immutable.
# - They noted the difference in available methods between lists and tuples.

# Weaknesses:
# - The explanation could be clearer with more attention to grammar (e.g., "List" should be "Lists," and "tuple" should be "tuples").
# - The answer lacked specific examples of when to use each data structure, which is important for demonstrating understanding of practical applications.      
# - Mentioning memory efficiency and performance differences could enhance the completeness of the answer.
# THANK YOU :)
# Questions: ['What is the difference between deep copy and shallow copy in Python?', 'What is the difference between a list and a tuple in Python, and when would you use one over the other?']
# Evaluations: ['Score: 8 out of 10\n\nStrengths:\n- The candidate accurately described the key difference between shallow and deep copies, highlighting that shallow copies share nested objects while deep copies create independent copies.\n\nWeaknesses:\n- The explanation could benefit from mentioning specific methods used to create these copies, such as `copy.copy()` for shallow copies and `copy.deepcopy()` for deep copies. Additionally, an example or clarification regarding the implications of modifying shared objects in shallow copies would enhance completeness.', 'Score: 7 out of 10\n\nStrengths:\n- The candidate correctly identified the syntax for lists and tuples and that lists are mutable while tuples are immutable.\n- They noted the difference in available methods between lists and tuples.\n\nWeaknesses:\n- The explanation could be clearer with more attention to grammar (e.g., "List" should be "Lists," and "tuple" should be "tuples").\n- The answer lacked specific examples of when to use each data structure, which is important for demonstrating understanding of practical applications.\n- Mentioning memory efficiency and performance differences could enhance the completeness of the answer.']
