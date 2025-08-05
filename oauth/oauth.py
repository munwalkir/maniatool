import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

app = FastAPI()

origins = [
    "http://localhost:9931",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@app.get("/callback")
async def auth_callback(code: str):
    token_url = "https://osu.ppy.sh/oauth/token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": REDIRECT_URI
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(token_url, data=payload, headers=headers)

    print(f"Token exchange response status: {response.status_code}")

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return response.json()

@app.post("/refresh")
async def refresh_token(request: RefreshTokenRequest):
    token_url = "https://osu.ppy.sh/oauth/token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": request.refresh_token,
        "grant_type": "refresh_token"
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(token_url, data=payload, headers=headers)

    print(f"Token refresh response status: {response.status_code}")

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return response.json()

@app.get("/user")
async def get_user(authorization: str = Header()):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.replace("Bearer ", "")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get("https://osu.ppy.sh/api/v2/me", headers=headers)

        if response.status_code == 401:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        elif response.status_code != 200:
            print(f"API Error: {response.status_code} - {response.text}")
            raise HTTPException(status_code=response.status_code, detail=response.text)

        user_data = response.json()
        print(f"Got user data for: {user_data.get('username', 'unknown')}")

        mania_response = requests.get("https://osu.ppy.sh/api/v2/me/mania", headers=headers)

        if mania_response.status_code == 200:
            mania_data = mania_response.json()
            print(f"Got mania stats - PP: {mania_data.get('statistics', {}).get('pp', 'N/A')}")
            user_data["statistics"] = mania_data.get("statistics", {})
        else:
            print(f"Mania stats failed: {mania_response.status_code}")

        return user_data

    except requests.RequestException as e:
        print(f"Request failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user data")
