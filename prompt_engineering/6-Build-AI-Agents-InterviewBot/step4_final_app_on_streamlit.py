# python -m pip install streamlit

from openai import OpenAI
import os
from dotenv import load_dotenv
import streamlit as st
import re

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY') 
client = OpenAI(api_key=OPENAI_API_KEY)
TOTAL_QUESTIONS = 2

st.title("AI Job Interview Bot")

# Session state variables
if "question_number" not in st.session_state:
    st.session_state.question_number = 1 # counter

if "questions_asked" not in st.session_state:
    st.session_state.questions_asked = [] # keep track of questions

if "scores" not in st.session_state:
    st.session_state.scores = [] # store scores for each questions

if "current_question" not in st.session_state:
    st.session_state.current_question = ""

if "submitted" not in st.session_state:
    st.session_state.submitted = False

if "last_feedback" not in st.session_state:
    st.session_state.last_feedback = "" # previous feed back

if "interview_started" not in st.session_state:
    st.session_state.interview_started = False

if "last_answer" not in st.session_state:
    st.session_state.last_answer = "" # previous answer

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


# Function to generate question
def generate_question():

    question_prompt = f"""Generate one Python interview question.

    Constraints:
    - The question should be suitable for an entry to mid-level Python developer
    - Do NOT repeat any question from this list:
      {st.session_state.questions_asked}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"system","content":system_prompt},
            {"role":"user","content":question_prompt}
        ]
    )

    question = response.choices[0].message.content
    st.session_state.current_question = question
    st.session_state.questions_asked.append(question)

def main():
        
    # Start Interview button
    if not st.session_state.interview_started:
        if st.button("Start Interview"):
            st.session_state.interview_started = True
            generate_question()
            st.rerun()
            

    # Show question and handle answer flow
    if st.session_state.current_question != "":

        st.subheader(f"Question {st.session_state.question_number} of {TOTAL_QUESTIONS}")
        st.write(st.session_state.current_question)

        # --- Answer submission phase ---
        if not st.session_state.submitted:
            answer = st.text_area("Your Answer")

            if st.button("Submit Answer"):
                evaluation_prompt = f"""
                You are a Python technical interviewer.

                Evaluate the candidate's answer to the interview question.

                Question:
                {st.session_state.current_question}

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
                    messages=[{"role": "user", "content": evaluation_prompt}]
                )

                evaluation_response = evaluation.choices[0].message.content
                st.session_state.last_feedback = evaluation_response

                # Extract score
                match = re.search(r"Score:\s*(\d+)", evaluation_response)
                if match:
                    score = int(match.group(1))
                    st.session_state.scores.append(score)

                st.session_state.last_answer = answer
                st.session_state.submitted = True
                st.rerun()

        # --- Feedback & navigation phase ---
        else:
            st.subheader("Feedback")
            st.info(f"**Question asked:** {st.session_state.current_question}")
            st.write(f"**Your Answer:** {st.session_state.last_answer}")
            st.write(st.session_state.last_feedback)

            # More questions remaining
            if st.session_state.question_number < TOTAL_QUESTIONS:
                if st.button("Next Question"):
                    st.session_state.question_number += 1
                    st.session_state.submitted = False
                    st.session_state.last_feedback = ""
                    generate_question()
                    st.rerun()

            # All questions done
            else:
                st.subheader("Interview Completed!")

                if len(st.session_state.scores) > 0:
                    final_score = sum(st.session_state.scores) / len(st.session_state.scores)
                    st.success(f"Final Score: {final_score:.2f} / 10")

                st.write("Thank you for completing the AI interview.")

                if st.button("Restart Interview"):
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    st.rerun()

if __name__ == '__main__':
    main()

# python -m streamlit run step4_final_app_on_streamlit.py

