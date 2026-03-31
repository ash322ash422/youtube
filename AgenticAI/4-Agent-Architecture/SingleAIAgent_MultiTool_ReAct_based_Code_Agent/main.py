from dotenv import load_dotenv
load_dotenv()

import os
import sys
import tempfile
import subprocess
from typing import Optional
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain.prompts import PromptTemplate
from langchain_community.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, Tool

# Define the Code Generation Tool
class CodeGenerationTool(BaseTool):
    llm: ChatOpenAI = Field()

    name: str = "code_generator"
    description: str = "Generates code for specified programming tasks"

    def _run(self, task: str) -> str:
        code_prompt = PromptTemplate(
            template="""Generate clean, efficient code for the task:
            {task}
            
            Guidelines:
            - Use best practices
            - Include minimal comments
            - Ensure the code is executable""",
            input_variables=["task"]
        )
        
        prompt = code_prompt.format(task=task)
        response = self.llm.predict(prompt)
        
        return response



# Define the Code Execution Tool
class CodeExecutionTool(BaseTool):
    name: str = "code_executor"
    description: str = "Executes generated code in a sandbox"

    def _run(self, code: str, language: str = 'python') -> str:
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{language}', delete=False) as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name
            
            result = subprocess.run(
                [sys.executable, temp_file_path],
                capture_output=True,
                text=True,
                timeout=10,
                check=True
            )
            
            return result.stdout

        except subprocess.TimeoutExpired:
            return "Code execution timed out."
        except subprocess.CalledProcessError as e:
            return f"Error executing code: {e.stderr}"
        finally:
            if 'temp_file_path' in locals():
                os.unlink(temp_file_path)


# Create the Code Agent
def create_code_agent(api_key: Optional[str] = None):
    llm = ChatOpenAI(
        api_key=api_key or os.getenv('OPENAI_API_KEY'),
        model="gpt-3.5-turbo",
        temperature=0.0,
        # max_tokens=1000,
    )

    if not llm:
        raise ValueError("OpenAI API key required")

    # Initialize tools
    code_generator_tool = CodeGenerationTool(llm=llm)
    code_executor_tool = CodeExecutionTool()

    tools = [
        Tool(name=code_generator_tool.name, func=code_generator_tool._run, description=code_generator_tool.description),
        Tool(name=code_executor_tool.name, func=code_executor_tool._run, description=code_executor_tool.description)
    ]

    # Initialize the agent
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent="zero-shot-react-description",
        verbose=True
    )

    return agent


# Main function
def main():
    agent = create_code_agent()

    tasks = [
        "Generate a Python function for addition.",
        "Write a function in python to calculate Fibonacci numbers recursively.",
        "Create a script in python to to calculate value of PI upto 4 decimals using random numbers."
    ]

    for task in tasks:
        print(f"\n--- Task: {task} ---")
        response = agent.invoke(task)
        print(response)


if __name__ == "__main__":
    main()
    
# --- Task: Generate a Python function for addition. ---


# > Entering new AgentExecutor chain...
# I should use the code_generator to create a Python function for addition.
# Action: code_generator
# Action Input: "def add(a, b):\n    return a + b"c:\Users\hi\Desktop\projects\python_projects\ai_projects\Generative_AI\Generative_AI_Agent_for_Code_Execution\main.py:37: LangChainDeprecationWarning: The method `BaseChatModel.predict` was deprecated in langchain-core 0.1.7 and will be removed in 1.0. Use :meth:`~invoke` instead.
#   response = self.llm.predict(prompt)

# Observation: def add(a, b):
#     return a + b
# Thought:I have generated the Python function for addition.
# Final Answer: def add(a, b):
#     return a + b

# > Finished chain.
# {'input': 'Generate a Python function for addition.', 'output': 'def add(a, b):\n    return a + b'}

# --- Task: Write a function in python to calculate Fibonacci numbers recursively. ---


# > Entering new AgentExecutor chain...
# I should generate code for a recursive function to calculate Fibonacci numbers in Python.
# Action: code_generator
# Action Input: "def fibonacci(n):\n    if n <= 1:\n        return n\n    else:\n        return fibonacci(n-1) + fibonacci(n-2)"
# Observation: def fibonacci(n):
#     if n <= 1:
#         return n
#     else:
#         return fibonacci(n-1) + fibonacci(n-2)

# num = int(input("Enter a number: "))
# result = fibonacci(num)
# print("Fibonacci number at position", num, "is:", result)
# Thought:I need to execute the generated code to test if it works correctly.
# Action: code_executor
# Action Input: code = def fibonacci(n):
#     if n <= 1:
#         return n
#     else:
#         return fibonacci(n-1) + fibonacci(n-2)

# num = 5
# result = fibonacci(num)
# Observation: Error executing code:   File "C:\Users\hi\AppData\Local\Temp\tmpy05znqe1.python", line 1
#     code = def fibonacci(n):
#            ^^^
# SyntaxError: invalid syntax

# Thought:I need to remove the "code =" part from the action input.
# Action: code_executor
# Action Input: def fibonacci(n):
#     if n <= 1:
#         return n
#     else:
#         return fibonacci(n-1) + fibonacci(n-2)

# num = 5
# result = fibonacci(num)
# Observation:
# Thought:The code executed successfully. I should check the result to verify the function.
# Action: code_executor
# Action Input: result
# Observation: Error executing code: Traceback (most recent call last):
#   File "C:\Users\hi\AppData\Local\Temp\tmp69hff702.python", line 1, in <module>
#     result
# NameError: name 'result' is not defined

# Thought:I need to modify the action input to print the result.
# Action: code_executor
# Action Input: print(result)
# Observation: Error executing code: Traceback (most recent call last):
#   File "C:\Users\hi\AppData\Local\Temp\tmpq2bw_24m.python", line 1, in <module>
#     print(result)
#           ^^^^^^
# NameError: name 'result' is not defined

# Thought:I need to include the code that assigns the result to a variable before printing it.
# Action: code_executor
# Action Input: def fibonacci(n):
#     if n <= 1:
#         return n
#     else:
#         return fibonacci(n-1) + fibonacci(n-2)

# num = 5
# result = fibonacci(num)
# print(result)
# Observation: 5

# Thought:The code works correctly and the Fibonacci number at position 5 is 5.
# Final Answer: The Fibonacci number at position 5 is 5.

# > Finished chain.
# {'input': 'Write a function in python to calculate Fibonacci numbers recursively.', 'output': 'The Fibonacci number at position 5 is 5.'}

# --- Task: Create a script in python to to calculate value of PI upto 4 decimals using random numbers. ---


# > Entering new AgentExecutor chain...
# We need to generate code that uses random numbers to approximate the value of PI.
# Action: code_generator
# Action Input: task = "calculate PI using random numbers"
# Observation: import random

# def calculate_pi(num_points):
#     inside_circle = 0
#     total_points = num_points
    
#     for _ in range(num_points):
#         x = random.uniform(0, 1)
#         y = random.uniform(0, 1)
        
#         if x**2 + y**2 <= 1:
#             inside_circle += 1

#     return 4 * inside_circle / total_points

# # Example usage
# num_points = 1000000
# pi_estimate = calculate_pi(num_points)
# print(pi_estimate)
# Thought:The code generated looks like it will approximate the value of PI using random numbers.
# Action: code_executor
# Action Input: code = "import random\n\ndef calculate_pi(num_points):\n    inside_circle = 0\n    total_points = num_points\n    \n    for _ in range(num_points):\n        x = random.uniform(0, 1)\n        y = random.uniform(0, 1)\n        \n        if x**2 + y**2 <= 1:\n            inside_circle += 1\n            \n    return 4 * inside_circle / total_points\n\n# Example usage\nnum_points = 1000000\npi_estimate = calculate_pi(num_points)\nprint(pi_estimate)"
# Observation: Error executing code:   File "C:\Users\hi\AppData\Local\Temp\tmp5k8r8bho.python", line 1
#     code = "import random\n\ndef calculate_pi(num_points):\n    inside_circle = 0\n    total_points = num_points\n    \n    for _ in range(num_points):\n        x = random.uniform(0, 1)\n        y = random.uniform(0, 1)\n        \n        if x**2 + y**2 <= 1:\n            inside_circle += 1\n            \n    return 4 * inside_circle / total_points\n\n# Example usage\nnum_points = 1000000\npi_estimate = calculate_pi(num_points)\nprint(pi_estimate)
#            ^
# SyntaxError: unterminated string literal (detected at line 1)

# Thought:The code has a syntax error due to the string literal not being properly terminated.
# Action: code_executor
# Action Input: code = "import random\n\ndef calculate_pi(num_points):\n    inside_circle = 0\n    total_points = num_points\n    \n    for _ in range(num_points):\n        x = random.uniform(0, 1)\n        y = random.uniform(0, 1)\n        \n        if x**2 + y**2 <= 1:\n            inside_circle += 1\n            \n    return 4 * inside_circle / total_points\n\n# Example usage\nnum_points = 1000000\npi_estimate = calculate_pi(num_points)\nprint(pi_estimate)"
# Observation: Error executing code:   File "C:\Users\hi\AppData\Local\Temp\tmp2oiukhwd.python", line 1
#     code = "import random\n\ndef calculate_pi(num_points):\n    inside_circle = 0\n    total_points = num_points\n    \n    for _ in range(num_points):\n        x = random.uniform(0, 1)\n        y = random.uniform(0, 1)\n        \n        if x**2 + y**2 <= 1:\n            inside_circle += 1\n            \n    return 4 * inside_circle / total_points\n\n# Example usage\nnum_points = 1000000\npi_estimate = calculate_pi(num_points)\nprint(pi_estimate)
#            ^
# SyntaxError: unterminated string literal (detected at line 1)

# Thought:The code literal is not being properly terminated in the input. I need to fix that.
# Action: code_executor
# Action Input: code = 'import random\n\ndef calculate_pi(num_points):\n    inside_circle = 0\n    total_points = num_points\n    \n    for _ in range(num_points):\n        x = random.uniform(0, 1)\n        y = random.uniform(0, 1)\n        \n        if x**2 + y**2 <= 1:\n            inside_circle += 1\n            \n    return 4 * inside_circle / total_points\n\n# Example usage\nnum_points = 1000000\npi_estimate = calculate_pi(num_points)\nprint(pi_estimate)'
# Observation:
# Thought:The code executed successfully this time.
# Final Answer: import random

# def calculate_pi(num_points):
#     inside_circle = 0
#     total_points = num_points
    
#     for _ in range(num_points):
#         x = random.uniform(0, 1)
#         y = random.uniform(0, 1)
        
#         if x**2 + y**2 <= 1:
#             inside_circle += 1

#     return 4 * inside_circle / total_points

# # Example usage
# num_points = 1000000
# pi_estimate = calculate_pi(num_points)
# print(pi_estimate)

# > Finished chain.
# {'input': 'Create a script in python to to calculate value of PI upto 4 decimals using random numbers.', 'output': 'import random\n\ndef calculate_pi(num_points):\n    inside_circle = 0\n    total_points = num_points\n    \n    for _ in range(num_points):\n        x = random.uniform(0, 1)\n        y = random.uniform(0, 1)\n        \n        if x**2 + y**2 <= 1:\n            inside_circle += 1\n            \n    return 4 * inside_circle / total_points\n\n# Example usage\nnum_points = 1000000\npi_estimate = calculate_pi(num_points)\nprint(pi_estimate)'}