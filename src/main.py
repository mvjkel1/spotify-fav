from fastapi import FastAPI, HTTPException, Request
import httpx
from models import TokenRequest
from dotenv import load_dotenv
import os
import urllib.parse

app = FastAPI()
load_dotenv()


@app.post("/generate_token")
async def generate_token(request: TokenRequest):
    url = "https://accounts.spotify.com/api/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": request.client_id,
        "client_secret": request.client_secret,
        "scope": "user-read-currently-playing",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, data=data)
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)


async def get_access_token(client_id: str, client_secret: str) -> str:
    token_request = TokenRequest(client_id=client_id, client_secret=client_secret)
    token_response = await generate_token(token_request)
    return token_response["access_token"]


@app.get("/current_music")
async def current_music(access_token: str):
    url = "https://api.spotify.com/v1/me/player/currently-playing"
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)


@app.get("/login")
async def login():
    params = {
        "client_id": os.getenv("CLIENT_ID"),
        "response_type": "code",
        "redirect_uri": os.getenv("REDIRECT_URI"),
        "scope": "user-read-currently-playing",
    }
    url = os.getenv("SPOTIFY_AUTH_URL") + "?" + urllib.parse.urlencode(params)
    return {"url": url}


@app.get("/callback")
async def callback(request: Request):
    code = request.query_params.get("code")
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": os.getenv("REDIRECT_URI"),
        "client_id": os.getenv("CLIENT_ID"),
        "client_secret": os.getenv("CLIENT_SECRET"),
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            os.getenv("SPOTIFY_TOKEN_URL"), headers=headers, data=data
        )
        if response.status_code == 200:
            token_response = response.json()
            return {"access_token": token_response["access_token"]}
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)
