# python -m pip install openai
# python -m pip install python-dotenv

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

print(response)
question = response.choices[0].message.content
print(question)

# ChatCompletion(id='chatcmpl-DI83j1iHD3IpdFzYydZkFDgmNZNwq', choices=[Choice(finish_reason='stop', index=0, logprobs=None, message=ChatCompletionMessage(content='What is the difference between a list and a tuple in Python, and when would you choose to use one over the other?', refusal=None, role='assistant', annotations=[], audio=None, function_call=None, tool_calls=None))], created=1773213255, model='gpt-4o-mini-2024-07-18', object='chat.completion', service_tier='default', system_fingerprint='fp_687f94b198', usage=CompletionUsage(completion_tokens=25, prompt_tokens=102, total_tokens=127, completion_tokens_details=CompletionTokensDetails(accepted_prediction_tokens=0, audio_tokens=0, reasoning_tokens=0, rejected_prediction_tokens=0), prompt_tokens_details=PromptTokensDetails(audio_tokens=0, cached_tokens=0)))
# What is the difference between a list and a tuple in Python, and when would you choose to use one over the other?


# (.venv) PS C:\Users\loxford> python -m pip show openai      
# Name: openai
# Version: 2.26.0
# Summary: The official Python library for the openai API
# Home-page: https://github.com/openai/openai-python
# Author:
# Author-email: OpenAI <support@openai.com>
# License: Apache-2.0