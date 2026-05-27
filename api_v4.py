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

SEGUNDO_CEREBRO_RULES = """
SEGUNDO CÉREBRO — CONTEXTO VIVO (REGRAS OBRIGATÓRIAS):

Cada cliente, projeto ou área importante tem UMA nota de contexto vivo no Supabase.
Essa nota representa o ESTADO ATUAL — não eventos isolados.
Ela é sempre atualizada, nunca duplicada.

CONVENÇÃO DE TÍTULOS (use exatamente assim):
- "contexto: Gracie Barra" → cliente Gracie Barra
- "contexto: SoHo" → cliente SoHo
- "contexto: DDpartssolution" → cliente DDpartssolution
- "contexto: Jarvis" → projeto Jarvis
- "contexto: autoescola" → área autoescola
- "contexto: faculdade" → área faculdade
- "contexto: financeiro" → área financeiro
(sempre minúsculo após "contexto: ", exceto nomes próprios)

ESTRUTURA DA NOTA DE CONTEXTO VIVO:
- situacao_atual: o que está acontecendo AGORA
- ultimo_passo: o que foi feito por último e quando
- proximo_passo: o que precisa ser feito agora
- historico_resumido: linha do tempo acumulativa dos eventos importantes

REGRA DE OURO — SALVAR AUTOMATICAMENTE:
Se o usuário mencionar QUALQUER informação sobre cliente, projeto ou área,
você DEVE chamar atualizar_contexto_vivo IMEDIATAMENTE, sem perguntar.
Isso inclui:
- "tive reunião com X" → salva
- "X gerou Y leads" → salva
- "fiz aula de X" → salva
- "paguei X" → salva em financeiro
- "decidi X" → salva
- "próximo passo é X" → salva
NÃO ESPERE SER PEDIDO. SALVE SEMPRE. É obrigação sua, não do usuário.

FLUXO OBRIGATÓRIO A CADA MENSAGEM:
1. Usuário menciona cliente/projeto/área
2. Chama atualizar_contexto_vivo com as novas informações
3. Confirma naturalmente para o Chefe (sem mencionar o processo técnico)

QUANDO LER O CONTEXTO VIVO:
- Quando o usuário PERGUNTAR sobre o status de algo
- Use buscar_contexto_vivo para responder com precisão

NUNCA crie duas notas de contexto para o mesmo cliente/projeto.
Se já existe, ATUALIZE. Se não existe, CRIE.
"""

FULL_INSTRUCTION = AGENT_INSTRUCTION + PROACTIVE_RULES + SEGUNDO_CEREBRO_RULES


class ChatRequest(BaseModel):
    message: str
    user_id: str = "JoaoZacche"


# ─────────────────────────────────────────
# FERRAMENTAS
# ─────────────────────────────────────────

TOOLS = [
    {
        "function_declarations": [
            {
                "name": "criar_entry",
                "description": (
                    "Cria qualquer tipo de entrada no sistema. "
                    "Types: task, note, event, project, habit, goal, transaction, reminder, contact."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "title": {"type": "string"},
                        "descricao": {"type": "string"},
                        "due_date": {"type": "string", "description": "ISO 8601"},
                        "date": {"type": "string", "description": "ISO 8601"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "amount": {"type": "number"},
                        "transaction_type": {"type": "string", "description": "receita ou despesa"},
                        "category": {"type": "string"},
                        "frequency": {"type": "string", "description": "daily, weekly, weekdays"},
                        "target_value": {"type": "number"},
                        "email": {"type": "string"},
                        "phone": {"type": "string"},
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
                        "status": {"type": "string"},
                        "descricao": {"type": "string"},
                        "due_date": {"type": "string"},
                        "valor_atual": {"type": "number"},
                    },
                    "required": ["entry_id"],
                },
            },
            {
                "name": "deletar_entry",
                "description": "Deleta uma entrada pelo ID.",
                "parameters": {
                    "type": "object",
                    "properties": {"entry_id": {"type": "string"}},
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
            {
                "name": "buscar_contexto_vivo",
                "description": (
                    "Lê o estado atual de um cliente, projeto ou área. "
                    "SEMPRE use isso antes de responder sobre Gracie Barra, SoHo, DDpartssolution, "
                    "Jarvis, autoescola, faculdade, financeiro, ou qualquer cliente/projeto mencionado. "
                    "Retorna a situação atual, último passo, próximo passo e histórico resumido."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "nome": {
                            "type": "string",
                            "description": "Nome do cliente/projeto/área. Ex: 'Gracie Barra', 'Jarvis', 'autoescola'",
                        }
                    },
                    "required": ["nome"],
                },
            },
            {
                "name": "atualizar_contexto_vivo",
                "description": (
                    "Atualiza o estado atual de um cliente, projeto ou área. "
                    "Use SEMPRE que houver nova informação: reunião, resultado, decisão, nova etapa. "
                    "Mantém UMA nota por cliente/projeto — atualiza em vez de criar duplicatas."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "nome": {
                            "type": "string",
                            "description": "Nome do cliente/projeto/área. Ex: 'Gracie Barra', 'Jarvis', 'autoescola'",
                        },
                        "situacao_atual": {
                            "type": "string",
                            "description": "O que está acontecendo AGORA neste cliente/projeto.",
                        },
                        "ultimo_passo": {
                            "type": "string",
                            "description": "O que foi feito por último e quando.",
                        },
                        "proximo_passo": {
                            "type": "string",
                            "description": "O que precisa ser feito agora.",
                        },
                        "historico_resumido": {
                            "type": "string",
                            "description": "Linha do tempo dos eventos importantes (acumulativa, não apaga).",
                        },
                    },
                    "required": ["nome", "situacao_atual"],
                },
            },
        ]
    }
]


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


def _titulo_contexto(nome: str) -> str:
    return f"contexto: {nome}"


# ─────────────────────────────────────────
# HANDLER DAS FERRAMENTAS
# ─────────────────────────────────────────

async def _executar_ferramenta(fn: str, args: dict, user_id: str) -> str:

    # ── Contexto vivo — leitura ──
    if fn == "buscar_contexto_vivo":
        nome = args["nome"]
        titulo = _titulo_contexto(nome)
        entries = await sb.buscar_entries(query=titulo, user_id=user_id, type="note")
        # Filtra para achar exatamente o contexto desse nome
        match = next((e for e in entries if e.get("title", "").lower() == titulo.lower()), None)
        if not match:
            return f"Nenhum contexto vivo encontrado para '{nome}'. Ainda não há registro deste cliente/projeto."
        content = match.get("content", {})
        if isinstance(content, dict):
            situacao = content.get("situacao_atual", "")
            ultimo = content.get("ultimo_passo", "")
            proximo = content.get("proximo_passo", "")
            historico = content.get("historico_resumido", "")
            entry_id = match.get("id", "")
            return (
                f"[id:{entry_id}] Contexto vivo de '{nome}':\n"
                f"Situação atual: {situacao}\n"
                f"Último passo: {ultimo}\n"
                f"Próximo passo: {proximo}\n"
                f"Histórico: {historico}"
            )
        return f"Contexto de '{nome}': {content}"

    # ── Contexto vivo — atualização ──
    if fn == "atualizar_contexto_vivo":
        nome = args["nome"]
        titulo = _titulo_contexto(nome)

        # Busca se já existe
        entries = await sb.buscar_entries(query=titulo, user_id=user_id, type="note")
        match = next((e for e in entries if e.get("title", "").lower() == titulo.lower()), None)

        agora = datetime.now(pytz.timezone("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")

        novo_content = {
            "situacao_atual": args.get("situacao_atual", ""),
            "ultimo_passo": args.get("ultimo_passo", f"Atualizado em {agora}"),
            "proximo_passo": args.get("proximo_passo", ""),
            "historico_resumido": args.get("historico_resumido", ""),
            "ultima_atualizacao": agora,
        }

        if match:
            # Preserva histórico anterior se não foi passado novo
            content_atual = match.get("content", {})
            if isinstance(content_atual, dict) and not args.get("historico_resumido"):
                historico_anterior = content_atual.get("historico_resumido", "")
                if historico_anterior:
                    novo_content["historico_resumido"] = historico_anterior

            ok = await sb.atualizar_entry(
                entry_id=match["id"],
                user_id=user_id,
                updates={"content": novo_content},
            )
            return f"Contexto vivo de '{nome}' atualizado." if ok else f"Erro ao atualizar contexto de '{nome}'."
        else:
            # Cria novo contexto vivo
            entry = await sb.criar_entry(
                user_id=user_id,
                type="note",
                title=titulo,
                content=novo_content,
                tags=["contexto-vivo", nome.lower().replace(" ", "-")],
            )
            return f"Contexto vivo de '{nome}' criado." if entry else f"Erro ao criar contexto de '{nome}'."

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

        try:
            await sb.get_or_create_user(user_id=user_id)
        except Exception:
            pass

        mem0_client = AsyncMemoryClient()

        # Busca memórias e tarefas em paralelo
        memories_task = mem0_client.search(
            query=req.message,
            filters={"user_id": user_id},
            limit=10,
        )
        tarefas_task = sb.listar_entries(user_id=user_id, type="task", status="active")

        # Detecta clientes/projetos mencionados na mensagem para pré-carregar contexto
        ENTIDADES_CONHECIDAS = [
            "Gracie Barra", "SoHo", "DDpartssolution", "Jarvis",
            "autoescola", "faculdade", "financeiro"
        ]
        entidades_mencionadas = [
            e for e in ENTIDADES_CONHECIDAS
            if e.lower() in req.message.lower()
        ]

        # Busca contextos vivos das entidades mencionadas em paralelo
        contextos_tasks = [
            sb.buscar_entries(query=_titulo_contexto(e), user_id=user_id, type="note")
            for e in entidades_mencionadas
        ]

        resultados = await asyncio.gather(
            memories_task, tarefas_task, *contextos_tasks,
            return_exceptions=True
        )

        memories_resp = resultados[0]
        tarefas = resultados[1]
        contextos_results = resultados[2:]

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

        # Contextos vivos pré-carregados
        contextos_injetados = ""
        for i, entidade in enumerate(entidades_mencionadas):
            if i < len(contextos_results) and not isinstance(contextos_results[i], Exception):
                entries = contextos_results[i]
                titulo = _titulo_contexto(entidade)
                match = next((e for e in entries if e.get("title", "").lower() == titulo.lower()), None)
                if match:
                    content = match.get("content", {})
                    if isinstance(content, dict):
                        situacao = content.get("situacao_atual", "")
                        proximo = content.get("proximo_passo", "")
                        ultimo = content.get("ultimo_passo", "")
                        entry_id = match.get("id", "")
                        contextos_injetados += (
                            f"\n[Contexto vivo — {entidade}] [id:{entry_id}]\n"
                            f"Situação atual: {situacao}\n"
                            f"Último passo: {ultimo}\n"
                            f"Próximo passo: {proximo}\n"
                        )

        tz = pytz.timezone("America/Sao_Paulo")
        agora = datetime.now(tz)
        data_hora = agora.strftime("%A, %d de %B de %Y, %H:%M")

        system = FULL_INSTRUCTION + f"\n\nDATA E HORA ATUAL: {data_hora}"
        if memory_text:
            system += f"\n\n[Memórias do usuário]\n{memory_text}"
        if tarefas_pendentes:
            system += f"\n\n[Tarefas pendentes]\n{tarefas_pendentes}"
        if contextos_injetados:
            system += f"\n\n[Contextos vivos carregados automaticamente]{contextos_injetados}"

        mensagem_com_contexto = f"[Contexto: hoje é {data_hora}]\n\n{req.message}"

        gemini = genai.Client(api_key=api_key)
        result = gemini.models.generate_content(
            model="gemini-2.5-flash",
            config={"system_instruction": system, "tools": TOOLS},
            contents=mensagem_com_contexto,
        )

        calls = [
            part.function_call
            for part in result.candidates[0].content.parts
            if hasattr(part, "function_call") and part.function_call
        ]

        if calls:
            resultados_tools = await asyncio.gather(*[
                _executar_ferramenta(call.name, dict(call.args), user_id)
                for call in calls
            ])
            resumo_tecnico = "\n".join(resultados_tools)
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

        # Salva no Mem0
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
