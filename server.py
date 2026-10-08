import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import supabase

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
PORT = int(os.getenv("PORT", 3000))

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY in .env")

supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()


class SignupRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@app.on_event("startup")
def on_startup():
    print("Server running and connected to Supabase")


@app.get("/health")
async def health():
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{SUPABASE_URL}/auth/v1/health",
                headers={"apikey": SUPABASE_KEY},
                timeout=5.0,
            )
            supabase_ok = resp.status_code == 200
    except Exception:
        supabase_ok = False

    return JSONResponse(
        status_code=200 if supabase_ok else 503,
        content={
            "status": "ok" if supabase_ok else "degraded",
            "server": "running",
            "supabase": "connected" if supabase_ok else "unreachable",
        },
    )


@app.post("/auth/signup", status_code=201)
async def signup(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    email = body.get("email")
    password = body.get("password")

    if not email or not password:
        return JSONResponse(status_code=400, content={"error": "Email and password are required"})

    try:
        result = supabase_client.auth.sign_up({"email": email, "password": password})
        user = result.user
        return {"user": {"id": user.id, "email": user.email, "created_at": user.created_at}}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@app.post("/auth/login")
async def login(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    email = body.get("email")
    password = body.get("password")

    if not email or not password:
        return JSONResponse(status_code=400, content={"error": "Email and password are required"})

    try:
        result = supabase_client.auth.sign_in_with_password({"email": email, "password": password})
        access_token = result.session.access_token
        refresh_token = result.session.refresh_token
        return {"access_token": access_token, "refresh_token": refresh_token}
    except Exception:
        return JSONResponse(status_code=401, content={"error": "Invalid login credentials"})


@app.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile")
async def protected_profile(request: Request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer ") or not auth_header[len("Bearer "):].strip():
        return JSONResponse(status_code=401, content={"error": "Access token required"})
    return JSONResponse(status_code=401, content={"error": "Token verification not implemented"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=PORT)