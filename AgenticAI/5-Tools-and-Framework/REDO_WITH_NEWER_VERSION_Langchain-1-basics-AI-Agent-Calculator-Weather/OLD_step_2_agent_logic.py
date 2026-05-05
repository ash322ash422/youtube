import requests
import math
import os
import warnings

from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, AgentType
from langchain.tools import Tool
from langchain.memory import ConversationBufferMemory

# Suppress warnings
warnings.filterwarnings("ignore", message=".*deprecated.*")


# -------------------------
# TOOL 1: Calculator
# -------------------------
def calculator(expression: str) -> str:
    try:
        return str(eval(expression, {"__builtins__": None}, vars(math)))
    except:
        return "Error in calculation"


# -------------------------
# TOOL 2: Weather
# -------------------------
def get_weather(city: str) -> str:
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}"
        geo_res = requests.get(geo_url).json()

        if "results" not in geo_res:
            return "City not found"

        lat = geo_res["results"][0]["latitude"]
        lon = geo_res["results"][0]["longitude"]

        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        weather_res = requests.get(weather_url).json()

        temp = weather_res["current_weather"]["temperature"]
        wind = weather_res["current_weather"]["windspeed"]

        return f"Temperature: {temp}°C, Wind Speed: {wind} km/h"

    except:
        return "Error fetching weather"


# -------------------------
# CREATE AGENT FUNCTION
# -------------------------
def create_agent(api_key):

    os.environ["OPENAI_API_KEY"] = api_key

    tools = [
        Tool(
            name="Calculator",
            func=calculator,
            description="Useful for solving math expressions like 25*4 or 100/5"
        ),
        Tool(
            name="Weather",
            func=get_weather,
            description="Useful for getting weather of a city like Delhi, London, Moscow"
        )
    ]

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0
    )

    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )

    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        memory=memory,
        verbose=True
    )

    return agent
