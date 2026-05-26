from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()


class ChatRequest(BaseModel):
    message: str
    user_id: str = "JoaoZacche"


@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        import google.generativeai as genai

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="GOOGLE_API_KEY não configurada.")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        result = model.generate_content(req.message)
        return {"response": result.text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}
