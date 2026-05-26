from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from google import genai
from mem0 import AsyncMemoryClient
from prompts import AGENT_INSTRUCTION

load_dotenv()

app = FastAPI()


class ChatRequest(BaseModel):
    message: str
    user_id: str = "JoaoZacche"


@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="GOOGLE_API_KEY não configurada.")

        mem0_client = AsyncMemoryClient()
        user_id = req.user_id

        memories = await mem0_client.search(
            query=req.message,
            filters={"user_id": user_id},
            limit=10,
        )
        if isinstance(memories, dict):
            results = memories.get("results", [])
        else:
            results = memories or []

        memory_text = ""
        if results:
            items = [r.get("memory") or r.get("text") for r in results if isinstance(r, dict)]
            memory_text = "\n".join(f"- {m}" for m in items if m)

        system = AGENT_INSTRUCTION
        if memory_text:
            system += f"\n\n[Memórias do usuário]\n{memory_text}"

        client = genai.Client(api_key=api_key)
        result = client.models.generate_content(
            model="gemini-2.5-flash",
            config={"system_instruction": system},
            contents=req.message,
        )

        await mem0_client.add([
            {"role": "user", "content": req.message},
            {"role": "assistant", "content": result.text},
        ], user_id=user_id)

        return {"response": result.text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}
