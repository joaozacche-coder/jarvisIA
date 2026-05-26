from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from google import genai
from mem0 import AsyncMemoryClient
from prompts import AGENT_INSTRUCTION
import supabase_client as sb

load_dotenv()

app = FastAPI()

class ChatRequest(BaseModel):
    message: str
    user_id: str = "JoaoZacche"


TOOLS = [
    {
        "function_declarations": [
            {
                "name": "criar_tarefa",
                "description": "Cria uma tarefa no Supabase",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "titulo": {"type": "string"},
                        "descricao": {"type": "string"},
                        "data_vencimento": {"type": "string"},
                        "prioridade": {"type": "string"},
                    },
                    "required": ["titulo"],
                },
            },
            {
                "name": "criar_lembrete",
                "description": "Cria um lembrete no Supabase",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "titulo": {"type": "string"},
                        "texto": {"type": "string"},
                        "quando": {"type": "string"},
                    },
                    "required": ["quando"],
                },
            },
            {
                "name": "registrar_gasto",
                "description": "Registra um gasto no Supabase",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "descricao": {"type": "string"},
                        "valor": {"type": "number"},
                        "categoria": {"type": "string"},
                    },
                    "required": ["descricao", "valor"],
                },
            },
            {
                "name": "ver_agenda_hoje",
                "description": "Lista eventos de hoje",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]
    }
]


async def _executar_ferramenta(fn: str, args: dict, user_id: str) -> str:
    if fn == "criar_tarefa":
        await sb.criar_tarefa(
            titulo=args["titulo"],
            descricao=args.get("descricao"),
            due_date=args.get("data_vencimento"),
            prioridade=args.get("prioridade", "média"),
            user_id=user_id,
        )
        return f"Tarefa '{args['titulo']}' criada com sucesso!"

    if fn == "criar_lembrete":
        await sb.criar_lembrete(
            titulo=args.get("titulo", "Lembrete"),
            remind_at=args["quando"],
            descricao=args.get("texto"),
            user_id=user_id,
        )
        return f"Lembrete criado para {args['quando']}!"

    if fn == "registrar_gasto":
        await sb.registrar_transacao(
            descricao=args["descricao"],
            valor=float(args["valor"]),
            tipo="despesa",
            categoria=args.get("categoria"),
            user_id=user_id,
        )
        return f"Gasto de R${args['valor']} registrado!"

    if fn == "ver_agenda_hoje":
        eventos = await sb.listar_eventos_hoje(user_id=user_id)
        if not eventos:
            return "Nenhum evento hoje."
        lista = "\n".join(f"- {e.get('title')}" for e in eventos)
        return f"Seus eventos hoje:\n{lista}"

    return "Ferramenta não reconhecida."


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

        gemini = genai.Client(api_key=api_key)
        result = gemini.models.generate_content(
            model="gemini-2.5-flash",
            config={"system_instruction": system, "tools": TOOLS},
            contents=req.message,
        )

        # Verifica function call
        response_text = None
        for part in result.candidates[0].content.parts:
            if hasattr(part, "function_call") and part.function_call:
                fn = part.function_call.name
                args = dict(part.function_call.args)
                response_text = await _executar_ferramenta(fn, args, user_id)
                break

        if response_text is None:
            response_text = result.text or ""

        await mem0_client.add([
            {"role": "user", "content": req.message},
            {"role": "assistant", "content": response_text},
        ], user_id=user_id)

        return {"response": response_text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}
