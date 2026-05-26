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

PROACTIVE_RULES = """
REGRAS DE PROATIVIDADE — SEMPRE SIGA:

1. DETECÇÃO AUTOMÁTICA DE TAREFAS:
Se o usuário mencionar algo que precisa ser feito
(ex: "preciso ligar pro cliente", "tenho que revisar o código",
"não esquecer de pagar a conta") → cria a tarefa no Supabase
automaticamente e confirma: "Anotei como tarefa: [título]"

2. ACOMPANHAMENTO DE TAREFAS PENDENTES:
A cada conversa, busca tarefas pendentes no Supabase e:
- Se uma tarefa está vencida → alerta o usuário
- Se uma tarefa está próxima do prazo → lembra proativamente
- Se o usuário diz "terminei X" ou "fiz X" → marca como
  concluída no Supabase automaticamente

3. DETECÇÃO DE GASTOS:
Se o usuário mencionar que gastou dinheiro
(ex: "fui no mercado", "paguei R$50 de uber") →
registra a transação automaticamente

4. DETECÇÃO DE LEMBRETES:
Se o usuário mencionar datas ou horários
(ex: "reunião amanhã às 14h", "dentista sexta") →
cria lembrete automaticamente

5. NUNCA PERGUNTE SE DEVE CRIAR — APENAS CRIE E CONFIRME.
"""

FULL_INSTRUCTION = AGENT_INSTRUCTION + PROACTIVE_RULES


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
            {
                "name": "marcar_tarefa_concluida",
                "description": "Marca uma tarefa como concluída no Supabase",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "ID da tarefa a concluir"},
                    },
                    "required": ["task_id"],
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

    if fn == "marcar_tarefa_concluida":
        ok = await sb.concluir_tarefa(task_id=args["task_id"], user_id=user_id)
        return "Tarefa marcada como concluída!" if ok else "Não encontrei essa tarefa."

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

        # Busca tarefas pendentes para contexto proativo
        tarefas_pendentes = ""
        try:
            tarefas = await sb.listar_tarefas(user_id=user_id)
            pendentes = [t for t in tarefas if t.get("status") not in ("concluida", "cancelada")]
            if pendentes:
                linhas = [
                    f"- [id:{t.get('id')}] {t.get('title')}"
                    + (f" (vence: {t.get('due_date')})" if t.get("due_date") else "")
                    for t in pendentes
                ]
                tarefas_pendentes = "\n".join(linhas)
        except Exception:
            pass

        system = FULL_INSTRUCTION
        if memory_text:
            system += f"\n\n[Memórias do usuário]\n{memory_text}"
        if tarefas_pendentes:
            system += f"\n\n[Tarefas pendentes do usuário]\n{tarefas_pendentes}"

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
