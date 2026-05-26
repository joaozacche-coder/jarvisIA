import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()


def _get_supabase_config() -> tuple[str, str]:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL e SUPABASE_SERVICE_KEY não estão configuradas no .env"
        )

    return url, key


def _get_user_id() -> str:
    return os.getenv("JARVIS_USER_ID") or os.getenv("MEM0_USER_ID") or "JoãoZacche"


def _get_client():
    url, key = _get_supabase_config()
    return create_client(url, key)


async def _execute_sync(operation):
    return await asyncio.to_thread(operation)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _start_of_today_iso() -> str:
    hoje = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return hoje.isoformat().replace("+00:00", "Z")


def _tomorrow_start_iso() -> str:
    amanha = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return amanha.isoformat().replace("+00:00", "Z")


def _clean_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


async def iniciar_sessao_voz(user_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
    client = _get_client()
    payload = _clean_payload(
        {
            "user_id": user_id or _get_user_id(),
            "status": "active",
            "started_at": _now_iso(),
        }
    )

    response = await _execute_sync(lambda: client.table("voice_sessions").insert(payload).execute())
    data = getattr(response, "data", None) or []

    if not data:
        return None

    return data[0].get("id") or data[0].get("session_id")


async def encerrar_sessao_voz(session_id: Optional[str] = None, user_id: Optional[str] = None) -> bool:
    client = _get_client()

    if session_id:
        response = await _execute_sync(
            lambda: client.table("voice_sessions")
            .update({"status": "ended", "ended_at": _now_iso()})
            .eq("id", session_id)
            .execute()
        )
        return bool(getattr(response, "data", None))

    query = client.table("voice_sessions").select("*").eq("user_id", user_id or _get_user_id()).eq("status", "active")
    response = await _execute_sync(lambda: query.execute())
    data = getattr(response, "data", None) or []

    if not data:
        return False

    latest = data[0]
    update_response = await _execute_sync(
        lambda: client.table("voice_sessions")
        .update({"status": "ended", "ended_at": _now_iso()})
        .eq("id", latest.get("id"))
        .execute()
    )

    return bool(getattr(update_response, "data", None))


async def criar_tarefa(
    titulo: str,
    descricao: Optional[str] = None,
    due_date: Optional[str] = None,
    prioridade: str = "média",
    status: str = "pendente",
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    client = _get_client()
    payload = _clean_payload(
        {
            "title": titulo,
            "description": descricao,
            "due_date": due_date,
            "priority": prioridade,
            "status": status,
            "user_id": user_id or _get_user_id(),
        }
    )

    response = await _execute_sync(lambda: client.table("tasks").insert(payload).execute())
    return getattr(response, "data", None) or []


async def listar_tarefas(
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    projeto_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    client = _get_client()

    def _query():
        q = client.table("tasks").select("*").eq("user_id", user_id or _get_user_id())
        if status:
            q = q.eq("status", status)
        if projeto_id:
            q = q.eq("project_id", projeto_id)
        return q.order("due_date", desc=False).execute()

    response = await _execute_sync(_query)
    return getattr(response, "data", None) or []


async def concluir_tarefa(task_id: str, user_id: Optional[str] = None) -> bool:
    client = _get_client()
    response = await _execute_sync(
        lambda: client.table("tasks")
        .update({"status": "concluida"})
        .eq("id", task_id)
        .eq("user_id", user_id or _get_user_id())
        .execute()
    )
    return bool(getattr(response, "data", None))


async def criar_lembrete(
    titulo: str,
    remind_at: str,
    descricao: Optional[str] = None,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    client = _get_client()
    payload = _clean_payload(
        {
            "title": titulo,
            "description": descricao,
            "remind_at": remind_at,
            "user_id": user_id or _get_user_id(),
        }
    )

    response = await _execute_sync(lambda: client.table("reminders").insert(payload).execute())
    return getattr(response, "data", None) or []


async def listar_lembretes(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    client = _get_client()
    response = await _execute_sync(
        lambda: client.table("reminders")
        .select("*")
        .eq("user_id", user_id or _get_user_id())
        .order("remind_at", desc=False)
        .execute()
    )
    return getattr(response, "data", None) or []


async def criar_contato(
    nome: str,
    email: Optional[str] = None,
    telefone: Optional[str] = None,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    client = _get_client()
    payload = _clean_payload(
        {
            "name": nome,
            "email": email,
            "phone": telefone,
            "user_id": user_id or _get_user_id(),
        }
    )

    response = await _execute_sync(lambda: client.table("contacts").insert(payload).execute())
    return getattr(response, "data", None) or []


async def buscar_contato(termo: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    client = _get_client()
    response = await _execute_sync(
        lambda: client.table("contacts")
        .select("*")
        .eq("user_id", user_id or _get_user_id())
        .execute()
    )
    contatos = getattr(response, "data", None) or []

    termo_normalizado = termo.lower()
    return [
        contato
        for contato in contatos
        if termo_normalizado in str(contato.get("name", "")).lower()
        or termo_normalizado in str(contato.get("email", "")).lower()
        or termo_normalizado in str(contato.get("phone", "")).lower()
    ]


async def registrar_interacao(
    tipo: str,
    conteudo: str,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    client = _get_client()
    payload = _clean_payload(
        {
            "user_id": user_id or _get_user_id(),
            "interaction_type": tipo,
            "content": conteudo,
        }
    )

    response = await _execute_sync(lambda: client.table("interactions").insert(payload).execute())
    return getattr(response, "data", None) or []


async def criar_nota(
    titulo: str,
    conteudo: str,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    client = _get_client()
    payload = _clean_payload(
        {
            "title": titulo,
            "content": conteudo,
            "user_id": user_id or _get_user_id(),
        }
    )

    response = await _execute_sync(lambda: client.table("notes").insert(payload).execute())
    return getattr(response, "data", None) or []


async def criar_evento(
    titulo: str,
    start_time: str,
    end_time: Optional[str] = None,
    descricao: Optional[str] = None,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    client = _get_client()
    payload = _clean_payload(
        {
            "title": titulo,
            "description": descricao,
            "start_time": start_time,
            "end_time": end_time,
            "user_id": user_id or _get_user_id(),
        }
    )

    response = await _execute_sync(lambda: client.table("events").insert(payload).execute())
    return getattr(response, "data", None) or []


async def listar_eventos_hoje(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    client = _get_client()
    response = await _execute_sync(
        lambda: client.table("events")
        .select("*")
        .eq("user_id", user_id or _get_user_id())
        .gte("start_time", _start_of_today_iso())
        .lt("start_time", _tomorrow_start_iso())
        .order("start_time", desc=False)
        .execute()
    )
    return getattr(response, "data", None) or []


async def registrar_transacao(
    descricao: str,
    valor: float,
    tipo: str = "despesa",
    categoria: Optional[str] = None,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    client = _get_client()
    payload = _clean_payload(
        {
            "description": descricao,
            "amount": valor,
            "type": tipo,
            "category": categoria,
            "user_id": user_id or _get_user_id(),
            "occurred_at": _now_iso(),
        }
    )

    response = await _execute_sync(lambda: client.table("transactions").insert(payload).execute())
    return getattr(response, "data", None) or []


async def salvar_conversa_ia(
    titulo: str,
    mensagens: List[Dict[str, str]],
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    client = _get_client()
    conversation_payload = _clean_payload(
        {
            "title": titulo,
            "user_id": user_id or _get_user_id(),
        }
    )

    conversation_response = await _execute_sync(
        lambda: client.table("ai_conversations").insert(conversation_payload).execute()
    )
    conversation_data = getattr(conversation_response, "data", None) or []

    if not conversation_data:
        return {"conversation": None, "messages": []}

    conversation = conversation_data[0]
    conversation_id = conversation.get("id")

    message_payloads = [
        _clean_payload(
            {
                "conversation_id": conversation_id,
                "role": mensagem.get("role"),
                "content": mensagem.get("content"),
            }
        )
        for mensagem in mensagens
    ]

    if message_payloads:
        await _execute_sync(lambda: client.table("ai_messages").insert(message_payloads).execute())

    return {"conversation": conversation, "messages": message_payloads}


# ─────────────────────────────────────────
# TAREFAS — funções faltantes
# ─────────────────────────────────────────

async def atualizar_tarefa(
    task_id: str,
    titulo: Optional[str] = None,
    status: Optional[str] = None,
    prioridade: Optional[str] = None,
    user_id: Optional[str] = None,
) -> bool:
    client = _get_client()
    updates = _clean_payload({"title": titulo, "status": status, "priority": prioridade})
    if not updates:
        return False
    response = await _execute_sync(
        lambda: client.table("tasks")
        .update(updates)
        .eq("id", task_id)
        .eq("user_id", user_id or _get_user_id())
        .execute()
    )
    return bool(getattr(response, "data", None))


async def deletar_tarefa(task_id: str, user_id: Optional[str] = None) -> bool:
    client = _get_client()
    response = await _execute_sync(
        lambda: client.table("tasks")
        .delete()
        .eq("id", task_id)
        .eq("user_id", user_id or _get_user_id())
        .execute()
    )
    return bool(getattr(response, "data", None))


async def marcar_tarefa_concluida(task_id: str, user_id: Optional[str] = None) -> bool:
    return await concluir_tarefa(task_id=task_id, user_id=user_id)


# ─────────────────────────────────────────
# AGENDA — funções faltantes
# ─────────────────────────────────────────

async def listar_eventos(
    user_id: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
) -> List[Dict[str, Any]]:
    client = _get_client()

    def _query():
        q = client.table("events").select("*").eq("user_id", user_id or _get_user_id())
        if data_inicio:
            q = q.gte("start_time", data_inicio)
        if data_fim:
            q = q.lte("start_time", data_fim)
        return q.order("start_time", desc=False).execute()

    response = await _execute_sync(_query)
    return getattr(response, "data", None) or []


async def deletar_evento(event_id: str, user_id: Optional[str] = None) -> bool:
    client = _get_client()
    response = await _execute_sync(
        lambda: client.table("events")
        .delete()
        .eq("id", event_id)
        .eq("user_id", user_id or _get_user_id())
        .execute()
    )
    return bool(getattr(response, "data", None))


# ─────────────────────────────────────────
# FINANÇAS — funções faltantes
# ─────────────────────────────────────────

async def listar_transacoes(
    user_id: Optional[str] = None,
    categoria: Optional[str] = None,
    tipo: Optional[str] = None,
) -> List[Dict[str, Any]]:
    client = _get_client()

    def _query():
        q = client.table("transactions").select("*").eq("user_id", user_id or _get_user_id())
        if categoria:
            q = q.eq("category", categoria)
        if tipo:
            q = q.eq("type", tipo)
        return q.order("occurred_at", desc=True).execute()

    response = await _execute_sync(_query)
    return getattr(response, "data", None) or []


async def resumo_financeiro(user_id: Optional[str] = None) -> Dict[str, Any]:
    transacoes = await listar_transacoes(user_id=user_id)
    receitas = sum(float(t.get("amount", 0)) for t in transacoes if t.get("type") == "receita")
    despesas = sum(float(t.get("amount", 0)) for t in transacoes if t.get("type") == "despesa")
    por_categoria: Dict[str, float] = {}
    for t in transacoes:
        cat = t.get("category") or "Outros"
        por_categoria[cat] = por_categoria.get(cat, 0) + float(t.get("amount", 0))
    return {
        "receitas": receitas,
        "despesas": despesas,
        "saldo": receitas - despesas,
        "por_categoria": por_categoria,
        "total_transacoes": len(transacoes),
    }


# ─────────────────────────────────────────
# CONTATOS — funções faltantes
# ─────────────────────────────────────────

async def listar_contatos(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    client = _get_client()
    response = await _execute_sync(
        lambda: client.table("contacts")
        .select("*")
        .eq("user_id", user_id or _get_user_id())
        .order("name", desc=False)
        .execute()
    )
    return getattr(response, "data", None) or []


async def atualizar_contato(
    contact_id: str,
    nome: Optional[str] = None,
    email: Optional[str] = None,
    telefone: Optional[str] = None,
    user_id: Optional[str] = None,
) -> bool:
    client = _get_client()
    updates = _clean_payload({"name": nome, "email": email, "phone": telefone})
    if not updates:
        return False
    response = await _execute_sync(
        lambda: client.table("contacts")
        .update(updates)
        .eq("id", contact_id)
        .eq("user_id", user_id or _get_user_id())
        .execute()
    )
    return bool(getattr(response, "data", None))


# ─────────────────────────────────────────
# NOTAS — funções faltantes
# ─────────────────────────────────────────

async def listar_notas(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    client = _get_client()
    response = await _execute_sync(
        lambda: client.table("notes")
        .select("*")
        .eq("user_id", user_id or _get_user_id())
        .order("created_at", desc=True)
        .execute()
    )
    return getattr(response, "data", None) or []


async def buscar_nota(query: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    notas = await listar_notas(user_id=user_id)
    q = query.lower()
    return [
        n for n in notas
        if q in str(n.get("title", "")).lower() or q in str(n.get("content", "")).lower()
    ]


async def atualizar_nota(
    note_id: str,
    titulo: Optional[str] = None,
    conteudo: Optional[str] = None,
    user_id: Optional[str] = None,
) -> bool:
    client = _get_client()
    updates = _clean_payload({"title": titulo, "content": conteudo})
    if not updates:
        return False
    response = await _execute_sync(
        lambda: client.table("notes")
        .update(updates)
        .eq("id", note_id)
        .eq("user_id", user_id or _get_user_id())
        .execute()
    )
    return bool(getattr(response, "data", None))


# ─────────────────────────────────────────
# PROJETOS (tabela nova: projects)
# ─────────────────────────────────────────

async def criar_projeto(
    titulo: str,
    descricao: Optional[str] = None,
    prazo: Optional[str] = None,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    client = _get_client()
    payload = _clean_payload({
        "title": titulo,
        "description": descricao,
        "deadline": prazo,
        "status": "ativo",
        "progress": 0,
        "user_id": user_id or _get_user_id(),
    })
    response = await _execute_sync(lambda: client.table("projects").insert(payload).execute())
    return getattr(response, "data", None) or []


async def listar_projetos(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    client = _get_client()
    response = await _execute_sync(
        lambda: client.table("projects")
        .select("*")
        .eq("user_id", user_id or _get_user_id())
        .order("created_at", desc=True)
        .execute()
    )
    return getattr(response, "data", None) or []


async def atualizar_projeto(
    project_id: str,
    titulo: Optional[str] = None,
    status: Optional[str] = None,
    progresso: Optional[int] = None,
    user_id: Optional[str] = None,
) -> bool:
    client = _get_client()
    updates = _clean_payload({"title": titulo, "status": status, "progress": progresso})
    if not updates:
        return False
    response = await _execute_sync(
        lambda: client.table("projects")
        .update(updates)
        .eq("id", project_id)
        .eq("user_id", user_id or _get_user_id())
        .execute()
    )
    return bool(getattr(response, "data", None))


# ─────────────────────────────────────────
# HÁBITOS (tabelas novas: habits, habit_checkins)
# ─────────────────────────────────────────

async def criar_habito(
    titulo: str,
    frequencia: str,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    client = _get_client()
    payload = _clean_payload({
        "title": titulo,
        "frequency": frequencia,
        "user_id": user_id or _get_user_id(),
    })
    response = await _execute_sync(lambda: client.table("habits").insert(payload).execute())
    return getattr(response, "data", None) or []


async def registrar_checkin(habito_id: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    client = _get_client()
    payload = {
        "habit_id": habito_id,
        "user_id": user_id or _get_user_id(),
        "checked_at": _now_iso(),
    }
    response = await _execute_sync(lambda: client.table("habit_checkins").insert(payload).execute())
    return getattr(response, "data", None) or []


async def listar_habitos(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    client = _get_client()
    response = await _execute_sync(
        lambda: client.table("habits")
        .select("*")
        .eq("user_id", user_id or _get_user_id())
        .order("created_at", desc=False)
        .execute()
    )
    return getattr(response, "data", None) or []


# ─────────────────────────────────────────
# METAS (tabela nova: goals)
# ─────────────────────────────────────────

async def criar_meta(
    titulo: str,
    valor_alvo: float,
    valor_atual: float = 0,
    prazo: Optional[str] = None,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    client = _get_client()
    payload = _clean_payload({
        "title": titulo,
        "target_value": valor_alvo,
        "current_value": valor_atual,
        "deadline": prazo,
        "user_id": user_id or _get_user_id(),
    })
    response = await _execute_sync(lambda: client.table("goals").insert(payload).execute())
    return getattr(response, "data", None) or []


async def atualizar_progresso_meta(goal_id: str, valor_atual: float) -> bool:
    client = _get_client()
    response = await _execute_sync(
        lambda: client.table("goals")
        .update({"current_value": valor_atual})
        .eq("id", goal_id)
        .execute()
    )
    return bool(getattr(response, "data", None))


async def listar_metas(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    client = _get_client()
    response = await _execute_sync(
        lambda: client.table("goals")
        .select("*")
        .eq("user_id", user_id or _get_user_id())
        .order("deadline", desc=False)
        .execute()
    )
    return getattr(response, "data", None) or []
