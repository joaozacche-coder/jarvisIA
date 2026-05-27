from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import asyncio
from datetime import datetime
import pytz
from dotenv import load_dotenv
from google import genai
from mem0 import AsyncMemoryClient
from prompts import AGENT_INSTRUCTION
import supabase_client as sb
from obsidian_tools import OBSIDIAN_TOOL_DEFINITIONS, executar_obsidian_tool

load_dotenv()

app = FastAPI()

PROACTIVE_RULES = """
REGRAS DE PROATIVIDADE — SEMPRE SIGA:

1. DETECÇÃO AUTOMÁTICA DE TAREFAS:
Se o usuário mencionar algo que precisa ser feito
(ex: "preciso ligar pro cliente", "tenho que revisar o código",
"não esquecer de pagar a conta") → cria a tarefa no Supabase
automaticamente.

2. ACOMPANHAMENTO DE TAREFAS PENDENTES:
A cada conversa, com base nas tarefas pendentes injetadas no contexto:
- Se uma tarefa está vencida → alerta o usuário
- Se uma tarefa está próxima do prazo → lembra proativamente
- Se o usuário diz "terminei X" ou "fiz X" → marca como concluída automaticamente

3. DETECÇÃO DE GASTOS:
Se o usuário mencionar que gastou dinheiro
(ex: "fui no mercado", "paguei R$50 de uber") →
registra a transação automaticamente.

4. DETECÇÃO DE LEMBRETES:
Se o usuário mencionar datas ou horários
(ex: "reunião amanhã às 14h", "dentista sexta") →
cria lembrete automaticamente.

5. VINCULAÇÃO DE CLIENTES:
Se o usuário mencionar um cliente ou empresa pelo nome
(ex: "Gracie Barra", "SoHo", "DDpartssolution") →
cria ou vincula automaticamente como project ou contact, conforme o contexto.

6. NUNCA PERGUNTE SE DEVE CRIAR — APENAS CRIE E CONFIRME.

REGRAS DE ESTILO — OBRIGATÓRIAS:

- NUNCA use markdown: sem asteriscos, sem negrito, sem itálico, sem listas com hífens.
  Escreva em texto puro e natural, como uma pessoa falando.
- RESPOSTAS CONCISAS: confirmações simples em no máximo 3 linhas.
  Não repita o que acabou de fazer. Uma frase elegante basta.
  Só expanda quando o usuário pedir detalhes.
- NUNCA liste de volta as informações que o usuário acabou de te dar.
  Confirme a ação, não o conteúdo.

TIPOS DE ENTRY DISPONÍVEIS:
task, note, event, project, habit, goal, transaction, reminder, contact
"""

OBSIDIAN_RULES = """
SEGUNDO CÉREBRO — OBSIDIAN (REGRAS OBRIGATÓRIAS):

O vault do Obsidian é a memória permanente do João. Estrutura:
- Clientes/ → Gracie Barra.md, SoHo.md, DDpartssolution.md
- Projetos/ → Jarvis.md e outros
- Aprendizados/ → Cursos.md, Autoescola.md, Faculdade.md, Trafego Pago.md
- Areas/ → Financeiro.md, Saude.md, Carreira.md, Pessoal.md
- Recursos/ → Ferramentas.md, Referencias.md, Contatos.md
- Diario/ → notas diárias no formato YYYY-MM-DD.md

QUANDO USAR O OBSIDIAN:

A) SEMPRE registre no Obsidian quando o usuário mencionar:
   - Resultado de campanha, lead, conversão → obsidian_registrar_historico no cliente
   - Reunião realizada ou agendada → obsidian_registrar_historico
   - Pagamento recebido ou enviado → obsidian_registrar_historico (tipo: financeiro)
   - Novo aprendizado, curso, aula → obsidian_salvar_informacao em Aprendizados/
   - Decisão importante → obsidian_salvar_informacao na área relevante
   - Informação sobre cliente → obsidian_registrar_historico no cliente

B) SEMPRE leia o Obsidian antes de responder sobre:
   - Qualquer cliente (Gracie Barra, SoHo, DDpartssolution ou novo)
   - Progresso em cursos, faculdade, autoescola
   - Status de projetos
   Use obsidian_ler_nota para ter contexto atualizado.

C) CRIE nota automaticamente quando:
   - Usuário menciona novo cliente → obsidian_criar_nota_cliente
   - Usuário menciona novo projeto → obsidian_salvar_informacao em Projetos/

D) Se o Obsidian retornar erro de conexão:
   Avise: "Preciso que você abra o Obsidian no seu Mac, Chefe."
   Não tente novamente — continue a conversa normalmente.

IMPORTANTE: Use Supabase E Obsidian em conjunto.
Supabase = dados estruturados e tarefas.
Obsidian = contexto rico, histórico narrativo, segundo cérebro.
"""

FULL_INSTRUCTION = AGENT_INSTRUCTION + PROACTIVE_RULES + OBSIDIAN_RULES


class ChatRequest(BaseModel):
    message: str
    user_id: str = "JoaoZacche"


# ─────────────────────────────────────────
# FERRAMENTAS — Supabase + Obsidian
# ─────────────────────────────────────────

SUPABASE_TOOL_DECLARATIONS = [
    {
        "name": "criar_entry",
        "description": (
            "Cria qualquer tipo de entrada no sistema. "
            "Types: task (tarefa), note (nota), event (evento), project (projeto), "
            "habit (hábito), goal (meta), transaction (gasto/receita), "
            "reminder (lembrete), contact (contato)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "title": {"type": "string"},
                "descricao": {"type": "string"},
                "due_date": {"type": "string", "description": "ISO 8601"},
                "date": {"type": "string", "description": "ISO 8601 — data principal (ex: start_time de eventos)"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "amount": {"type": "number", "description": "Para transaction: valor em reais"},
                "transaction_type": {"type": "string", "description": "receita ou despesa"},
                "category": {"type": "string", "description": "Para transaction: categoria"},
                "frequency": {"type": "string", "description": "Para habit: daily, weekly, weekdays"},
                "target_value": {"type": "number", "description": "Para goal: valor alvo"},
                "email": {"type": "string", "description": "Para contact"},
                "phone": {"type": "string", "description": "Para contact"},
            },
            "required": ["type", "title"],
        },
    },
    {
        "name": "listar_entries",
        "description": "Lista entradas por tipo e filtros opcionais.",
        "parameters": {
            "type": "object",
            "properties": {
                "type": {"type": "string"},
                "status": {"type": "string", "description": "active, done, cancelled"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
            },
        },
    },
    {
        "name": "atualizar_entry",
        "description": "Atualiza título, status, descrição ou prazo de uma entrada.",
        "parameters": {
            "type": "object",
            "properties": {
                "entry_id": {"type": "string"},
                "title": {"type": "string"},
                "status": {"type": "string", "description": "active, done, cancelled"},
                "descricao": {"type": "string"},
                "due_date": {"type": "string"},
                "valor_atual": {"type": "number", "description": "Para goal: atualiza current_value"},
            },
            "required": ["entry_id"],
        },
    },
    {
        "name": "deletar_entry",
        "description": "Deleta uma entrada pelo ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "entry_id": {"type": "string"},
            },
            "required": ["entry_id"],
        },
    },
    {
        "name": "buscar_entries",
        "description": "Busca entradas por texto no título.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "type": {"type": "string"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "criar_reminder",
        "description": "Cria um lembrete vinculado a uma entry existente.",
        "parameters": {
            "type": "object",
            "properties": {
                "entry_id": {"type": "string"},
                "remind_at": {"type": "string", "description": "ISO 8601"},
            },
            "required": ["entry_id", "remind_at"],
        },
    },
]

# Junta ferramentas do Supabase + Obsidian em uma lista só para o Gemini
TOOLS = [
    {
        "function_declarations": SUPABASE_TOOL_DECLARATIONS + OBSIDIAN_TOOL_DEFINITIONS
    }
]

# Set com nomes das ferramentas do Obsidian para roteamento rápido
OBSIDIAN_TOOL_NAMES = {t["name"] for t in OBSIDIAN_TOOL_DEFINITIONS}


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

_TYPE_LABELS = {
    "task": "Tarefa", "note": "Nota", "event": "Evento",
    "project": "Projeto", "habit": "Hábito", "goal": "Meta",
    "transaction": "Transação", "reminder": "Lembrete", "contact": "Contato",
}


def _build_content(args: dict) -> dict:
    content: dict = {}
    for field in ("descricao", "amount", "transaction_type", "category",
                  "frequency", "target_value", "email", "phone"):
        if args.get(field) is not None:
            key = "description" if field == "descricao" else field
            content[key] = args[field]
    return content


def _format_entry(e: dict) -> str:
    label = _TYPE_LABELS.get(e.get("type", ""), e.get("type", ""))
    line = f"- [{label}] {e.get('title')} [{e.get('status')}]"
    if e.get("due_date"):
        line += f" (prazo: {e['due_date']})"
    if e.get("id"):
        line += f" [id:{e['id']}]"
    return line


# ─────────────────────────────────────────
# HANDLER DAS FERRAMENTAS
# ─────────────────────────────────────────

async def _executar_ferramenta(fn: str, args: dict, user_id: str) -> str:

    # ── Ferramentas do Obsidian ──
    if fn in OBSIDIAN_TOOL_NAMES:
        return await executar_obsidian_tool(fn, args)

    # ── Ferramentas do Supabase ──
    if fn == "criar_entry":
        entry_type = args["type"]
        content = _build_content(args)
        entry = await sb.criar_entry(
            user_id=user_id,
            type=entry_type,
            title=args["title"],
            content=content,
            due_date=args.get("due_date"),
            date=args.get("date"),
            tags=list(args["tags"]) if args.get("tags") else [],
        )
        label = _TYPE_LABELS.get(entry_type, entry_type)
        entry_id = entry.get("id", "")
        return f"{label} '{args['title']}' criado(a)!" + (f" [id:{entry_id}]" if entry_id else "")

    if fn == "listar_entries":
        entries = await sb.listar_entries(
            user_id=user_id,
            type=args.get("type"),
            status=args.get("status"),
            tags=list(args["tags"]) if args.get("tags") else None,
            limit=int(args.get("limit", 20)),
        )
        if not entries:
            return "Nenhuma entrada encontrada."
        return "\n".join(_format_entry(e) for e in entries)

    if fn == "atualizar_entry":
        updates: dict = {}
        if args.get("title"):
            updates["title"] = args["title"]
        if args.get("status"):
            updates["status"] = args["status"]
        if args.get("due_date"):
            updates["due_date"] = args["due_date"]
        if args.get("descricao"):
            updates["content"] = {"description": args["descricao"]}
        if args.get("valor_atual") is not None:
            updates["content"] = {"current_value": float(args["valor_atual"])}
        if not updates:
            return "Nenhum campo para atualizar."
        ok = await sb.atualizar_entry(entry_id=args["entry_id"], user_id=user_id, updates=updates)
        return "Entrada atualizada!" if ok else "Não encontrei essa entrada."

    if fn == "deletar_entry":
        ok = await sb.deletar_entry(entry_id=args["entry_id"], user_id=user_id)
        return "Entrada deletada!" if ok else "Não encontrei essa entrada."

    if fn == "buscar_entries":
        entries = await sb.buscar_entries(
            query=args["query"],
            user_id=user_id,
            type=args.get("type"),
        )
        if not entries:
            return f"Nenhuma entrada encontrada para '{args['query']}'."
        return "Encontrei:\n" + "\n".join(_format_entry(e) for e in entries)

    if fn == "criar_reminder":
        await sb.criar_reminder_entry(
            entry_id=args["entry_id"],
            remind_at=args["remind_at"],
            user_id=user_id,
        )
        return f"Lembrete criado para {args['remind_at']}!"

    return "Ferramenta não reconhecida."


# ─────────────────────────────────────────
# ROTAS
# ─────────────────────────────────────────

@app.post("/chat")
async def chat(req: ChatRequest):
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="GOOGLE_API_KEY não configurada.")

        user_id = req.user_id

        # Garante que o usuário existe no perfil
        try:
            await sb.get_or_create_user(user_id=user_id)
        except Exception:
            pass

        mem0_client = AsyncMemoryClient()

        # Busca memórias e tarefas pendentes em paralelo
        memories_task = mem0_client.search(
            query=req.message,
            filters={"user_id": user_id},
            limit=10,
        )
        tarefas_task = sb.listar_entries(user_id=user_id, type="task", status="active")

        memories_resp, tarefas = await asyncio.gather(memories_task, tarefas_task, return_exceptions=True)

        # Memórias
        memory_text = ""
        if not isinstance(memories_resp, Exception):
            results = memories_resp.get("results", []) if isinstance(memories_resp, dict) else (memories_resp or [])
            items = [r.get("memory") or r.get("text") for r in results if isinstance(r, dict)]
            memory_text = "\n".join(f"- {m}" for m in items if m)

        # Tarefas pendentes
        tarefas_pendentes = ""
        if not isinstance(tarefas, Exception) and tarefas:
            linhas = [
                f"- [id:{t.get('id')}] {t.get('title')}"
                + (f" (vence: {t.get('due_date')})" if t.get("due_date") else "")
                for t in tarefas
            ]
            tarefas_pendentes = "\n".join(linhas)

        tz = pytz.timezone("America/Sao_Paulo")
        agora = datetime.now(tz)
        data_hora = agora.strftime("%A, %d de %B de %Y, %H:%M")

        system = FULL_INSTRUCTION + f"\n\nDATA E HORA ATUAL: {data_hora}"
        if memory_text:
            system += f"\n\n[Memórias do usuário]\n{memory_text}"
        if tarefas_pendentes:
            system += f"\n\n[Tarefas pendentes do usuário]\n{tarefas_pendentes}"

        mensagem_com_contexto = f"[Contexto: hoje é {data_hora}]\n\n{req.message}"

        gemini = genai.Client(api_key=api_key)
        result = gemini.models.generate_content(
            model="gemini-2.5-flash",
            config={"system_instruction": system, "tools": TOOLS},
            contents=mensagem_com_contexto,
        )

        # Coleta todos os function calls
        calls = [
            part.function_call
            for part in result.candidates[0].content.parts
            if hasattr(part, "function_call") and part.function_call
        ]

        if calls:
            # Executa todas as ferramentas (Supabase + Obsidian) em paralelo
            resultados = await asyncio.gather(*[
                _executar_ferramenta(call.name, dict(call.args), user_id)
                for call in calls
            ])
            resumo_tecnico = "\n".join(resultados)
            followup = gemini.models.generate_content(
                model="gemini-2.5-flash",
                config={"system_instruction": system},
                contents=(
                    f"Você acabou de executar com sucesso as seguintes ações. "
                    f"Resultado interno: {resumo_tecnico}. "
                    f"Confirme de forma natural e elegante para o Chefe, "
                    f"sem mostrar IDs técnicos, status internos ou colchetes."
                ),
            )
            response_text = followup.text or resumo_tecnico
        else:
            response_text = result.text or ""

        # Salva conversa no Mem0
        try:
            await mem0_client.add([
                {"role": "user", "content": req.message},
                {"role": "assistant", "content": response_text},
            ], user_id=user_id)
        except Exception:
            pass

        return {"response": response_text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {"status": "ok"}
