import os
from dotenv import load_dotenv
from fastapi import FastAPI
import supabase

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
PORT = int(os.getenv("PORT", 3000))

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY in .env")

supabase_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()


@app.on_event("startup")
def on_startup():
    print("Server running and connected to Supabase")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=PORT)
