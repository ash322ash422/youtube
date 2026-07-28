import json
import boto3
import requests

import os
from dotenv import load_dotenv
load_dotenv()
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")

# ---------------------------------------------------------------------------
# Step 1: Define your local Python functions
# ---------------------------------------------------------------------------
# These are regular Python functions. The model will never call them directly.
# Instead, the model will ASK us to call them by returning a tool_use block.

def get_weather(location, unit="fahrenheit"):
    """
    Fetches weather data for a location.
    Uses the Open-Meteo API to get current weather information."""
    try:
        # Step 1: Convert city name to Latitude/Longitude using open geocoding
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1&language=en&format=json"
        geo_res = requests.get(geo_url)
        geo_res.raise_for_status()
        geo_data = geo_res.json()
        
        if not geo_data.get("results"):
            return {"error": f"City '{location}' not found."}
            
        city_info = geo_data["results"][0]
        lat, lon = city_info["latitude"], city_info["longitude"]
        
        # Step 2: Fetch current weather data from Open-Meteo using coordinates
        temp_unit = "fahrenheit" if unit.lower() == "fahrenheit" else "celsius"
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&temperature_unit={temp_unit}"
        
        weather_res = requests.get(weather_url)
        weather_res.raise_for_status()
        data = weather_res.json()["current"]
        
        # Map WMO weather codes to simple descriptions (Optional fallback)
        condition = "Clear/Partly cloudy" if data["weather_code"] <= 3 else "Cloudy/Rainy"
        
        return {
            "location": f"{city_info['name']}, {city_info.get('country', '')}",
            "temperature": data["temperature_2m"],
            "unit": unit,
            "condition": condition,
            "humidity": f"{data['relative_humidity_2m']}%",
            "wind": f"{data['wind_speed_10m']} mph" if temp_unit == "fahrenheit" else f"{data['wind_speed_10m']} km/h",
        }
    except requests.exceptions.RequestException as e:
        return {"error": f"Network error: {e}"}

# # Test it out
# print(get_weather("Chicago", "fahrenheit"))

# ---------------------------------------------------------------------------
# Step 2: Describe your functions as "tools" for the model
# ---------------------------------------------------------------------------
# The model needs a description of each tool so it knows:
#   - What the tool does (description)
#   - What inputs it expects (inputSchema)
#
# This is like writing documentation so someone else can use your function.

TOOL_CONFIG = {
    "tools": [
        {
            "toolSpec": {
                "name": "get_weather",
                "description": "Get the current weather for a given location.",
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The city and state, e.g. 'San Francisco, CA'",
                            },
                            "unit": {
                                "type": "string",
                                "enum": ["fahrenheit", "celsius"],
                                "description": "Temperature unit (default: fahrenheit)",
                            },
                        },
                        "required": ["location"],
                    }
                },
            }
        }
    ]
}


# ---------------------------------------------------------------------------
# Step 3: Map tool names to actual Python functions
# ---------------------------------------------------------------------------
# When the model asks to use a tool, we look up the function by name here.

TOOL_FUNCTIONS = {
    "get_weather": get_weather,
}


def run_tool(tool_name, tool_input):
    """
    Look up a tool by name and call it with the provided input.
    Returns the result as a dictionary.
    """
    func = TOOL_FUNCTIONS.get(tool_name)
    if func is None:
        return {"error": f"Unknown tool: {tool_name}"}

    # ** unpacks the dict into keyword arguments:
    #   get_weather(**{"location": "Seattle"})  →  get_weather(location="Seattle")
    return func(**tool_input)


# ---------------------------------------------------------------------------
# Step 4: The main tool use loop
# ---------------------------------------------------------------------------

def tool_use_demo():
    # Create the Bedrock client
    bedrock_client = boto3.client(
        service_name="bedrock-runtime",
        region_name='us-east-1', 
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY
    )

    model_id = "us.amazon.nova-lite-v1:0"

    user_message = "What's the weather like in Seattle right now?"

    print("Bedrock Tool Use Demo")
    print("=" * 60)
    print(f"User: {user_message}\n")

    # Start the conversation with the user's message
    messages = [
        {
            "role": "user",
            "content": [{"text": user_message}],
        }
    ]

    # --- First API call ---
    # Send the message AND the tool definitions to the model.
    # The model will look at the question, look at the available tools,
    # and decide if it needs to call one.
    print("[Step 1] Sending message to model with tool definitions...")

    response = bedrock_client.converse(
        modelId=model_id,
        messages=messages,
        toolConfig=TOOL_CONFIG,
        inferenceConfig={"temperature": 0.0, "maxTokens": 300},
    )

    stop_reason = response["stopReason"]
    assistant_message = response["output"]["message"]

    print(f"  Model responded with stop reason: {stop_reason}")

    # --- Check: did the model ask to use a tool? ---
    if stop_reason == "tool_use":
        # The model wants to call a tool. Let's find the toolUse block.
        tool_use_block = None
        for block in assistant_message["content"]:
            if "toolUse" in block:
                tool_use_block = block["toolUse"]
                break

        tool_name = tool_use_block["name"]
        tool_input = tool_use_block["input"]
        tool_use_id = tool_use_block["toolUseId"]

        print(f"\n[Step 2] Model wants to call: {tool_name}")
        print(f"  With arguments: {json.dumps(tool_input, indent=2)}")

        # --- Run the actual function ---
        result = run_tool(tool_name, tool_input)
        print(f"\n[Step 3] Function returned: {json.dumps(result, indent=2)}")

        # --- Send the result back to the model ---
        # We add the assistant's message (with the tool request) to the history,
        # then add a user message containing the tool result.
        messages.append(assistant_message)
        messages.append({
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "toolUseId": tool_use_id,
                        "content": [{"json": result}],
                    }
                }
            ],
        })

        print("\n[Step 4] Sending tool result back to model...")

        final_response = bedrock_client.converse(
            modelId=model_id,
            messages=messages,
            toolConfig=TOOL_CONFIG,
            inferenceConfig={"temperature": 0.0, "maxTokens": 300},
        )

        final_text = final_response["output"]["message"]["content"][0]["text"]
        print(f"\nAssistant: {final_text}")

    elif stop_reason == "end_turn":
        # The model answered directly without needing a tool
        print(f"\nAssistant: {assistant_message['content'][0]['text']}")


if __name__ == "__main__":
    tool_use_demo()
