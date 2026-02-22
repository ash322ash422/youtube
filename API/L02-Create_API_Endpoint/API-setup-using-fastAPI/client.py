# Import requests library
import requests

# Base URL of FastAPI server
BASE_URL = "http://127.0.0.1:8000"

# ---------------------------------
# 1. ADD USER (POST REQUEST)
# ---------------------------------

add_user_url = f"{BASE_URL}/add-user"

# Query parameters (same as Swagger UI)
params = {
    "name": "Ash",
    "email": "ash@gmail.com"
}

response = requests.post(add_user_url, params=params)

print("ADD USER RESPONSE")
print("Status Code:", response.status_code)
print("Response JSON:", response.json())

# ---------------------------------
# 2. GET USER BY ID (GET REQUEST)
# ---------------------------------

get_user_url = f"{BASE_URL}/get-user/1"

response = requests.get(get_user_url)

print("\nGET USER RESPONSE")
print("Status Code:", response.status_code)
print("Response JSON:", response.json())
