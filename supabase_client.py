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
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _start_of_today_iso() -> str:
    hoje = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return hoje.isoformat().replace("+00:00", "Z")


def _tomorrow_start_iso() -> str:
    amanha = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    return amanha.isoformat().replace("+00:00", "Z")


def _clean_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in payload.items() if v is not None}


# ─────────────────────────────────────────
# VOZ (inalterado)
# ─────────────────────────────────────────

async def iniciar_sessao_voz(user_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
    client = _get_client()
    payload = _clean_payload({
        "user_id": user_id or _get_user_id(),
        "status": "active",
        "started_at": _now_iso(),
    })
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


# ─────────────────────────────────────────
# FUNÇÕES UNIVERSAIS — tabela entries
# ─────────────────────────────────────────

async def get_or_create_user(user_id: str, name: Optional[str] = None) -> Dict[str, Any]:
    client = _get_client()
    payload = _clean_payload({"user_id": user_id, "name": name, "updated_at": _now_iso()})
    response = await _execute_sync(
        lambda: client.table("users_profile").upsert(payload, on_conflict="user_id").execute()
    )
    data = getattr(response, "data", None) or []
    return data[0] if data else {}


async def atualizar_perfil(user_id: str, updates: Dict[str, Any]) -> bool:
    client = _get_client()
    updates["updated_at"] = _now_iso()
    response = await _execute_sync(
        lambda: client.table("users_profile").update(updates).eq("user_id", user_id).execute()
    )
    return bool(getattr(response, "data", None))


async def criar_entry(
    user_id: str,
    type: str,
    title: str,
    content: Optional[Dict[str, Any]] = None,
    status: str = "active",
    priority: int = 0,
    date: Optional[str] = None,
    due_date: Optional[str] = None,
    tags: Optional[List[str]] = None,
    parent_id: Optional[str] = None,
) -> Dict[str, Any]:
    client = _get_client()
    payload = _clean_payload({
        "user_id": user_id,
        "type": type,
        "title": title,
        "content": content or {},
        "status": status,
        "priority": priority,
        "date": date,
        "due_date": due_date,
        "tags": tags or [],
        "parent_id": parent_id,
    })
    response = await _execute_sync(lambda: client.table("entries").insert(payload).execute())
    data = getattr(response, "data", None) or []
    return data[0] if data else {}


async def listar_entries(
    user_id: str,
    type: Optional[str] = None,
    status: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    client = _get_client()

    def _query():
        q = client.table("entries").select("*").eq("user_id", user_id)
        if type:
            q = q.eq("type", type)
        if status:
            q = q.eq("status", status)
        if tags:
            q = q.contains("tags", tags)
        return q.order("created_at", desc=True).limit(limit).execute()

    response = await _execute_sync(_query)
    return getattr(response, "data", None) or []


async def atualizar_entry(
    entry_id: str,
    user_id: str,
    updates: Dict[str, Any],
) -> bool:
    client = _get_client()
    updates["updated_at"] = _now_iso()
    response = await _execute_sync(
        lambda: client.table("entries")
        .update(updates)
        .eq("id", entry_id)
        .eq("user_id", user_id)
        .execute()
    )
    return bool(getattr(response, "data", None))


async def deletar_entry(entry_id: str, user_id: str) -> bool:
    client = _get_client()
    response = await _execute_sync(
        lambda: client.table("entries")
        .delete()
        .eq("id", entry_id)
        .eq("user_id", user_id)
        .execute()
    )
    return bool(getattr(response, "data", None))


async def buscar_entries(
    query: str,
    user_id: str,
    type: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    client = _get_client()

    def _query_fn():
        q = client.table("entries").select("*").eq("user_id", user_id).ilike("title", f"%{query}%")
        if type:
            q = q.eq("type", type)
        return q.limit(limit).execute()

    response = await _execute_sync(_query_fn)
    return getattr(response, "data", None) or []


async def criar_reminder_entry(entry_id: str, remind_at: str, user_id: str) -> Dict[str, Any]:
    client = _get_client()
    payload = {"user_id": user_id, "entry_id": entry_id, "remind_at": remind_at, "sent": False}
    response = await _execute_sync(lambda: client.table("reminders").insert(payload).execute())
    data = getattr(response, "data", None) or []
    return data[0] if data else {}


async def listar_reminders_pendentes(user_id: str) -> List[Dict[str, Any]]:
    client = _get_client()
    response = await _execute_sync(
        lambda: client.table("reminders")
        .select("*, entries(title, type)")
        .eq("user_id", user_id)
        .eq("sent", False)
        .gte("remind_at", _now_iso())
        .order("remind_at", desc=False)
        .execute()
    )
    return getattr(response, "data", None) or []


async def criar_relacao(
    entry_a: str,
    entry_b: str,
    relation_type: str,
    user_id: str,
) -> Dict[str, Any]:
    client = _get_client()
    payload = {"user_id": user_id, "entry_a": entry_a, "entry_b": entry_b, "relation_type": relation_type}
    response = await _execute_sync(lambda: client.table("relations").insert(payload).execute())
    data = getattr(response, "data", None) or []
    return data[0] if data else {}


# ─────────────────────────────────────────
# TAREFAS — wrappers
# ─────────────────────────────────────────

_STATUS_TO_ENTRY = {"pendente": "active", "concluida": "done", "cancelada": "cancelled"}
_STATUS_FROM_ENTRY = {"active": "pendente", "done": "concluida", "cancelled": "cancelada"}


async def criar_tarefa(
    titulo: str,
    descricao: Optional[str] = None,
    due_date: Optional[str] = None,
    prioridade: str = "média",
    status: str = "pendente",
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    uid = user_id or _get_user_id()
    result = await criar_entry(
        user_id=uid,
        type="task",
        title=titulo,
        content=_clean_payload({"description": descricao, "priority": prioridade}),
        due_date=due_date,
        status=_STATUS_TO_ENTRY.get(status, status),
    )
    return [result] if result else []


async def listar_tarefas(
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    projeto_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    uid = user_id or _get_user_id()
    mapped = _STATUS_TO_ENTRY.get(status, status) if status else None
    entries = await listar_entries(user_id=uid, type="task", status=mapped)
    if projeto_id:
        entries = [e for e in entries if e.get("content", {}).get("project_id") == projeto_id]
    return entries


async def concluir_tarefa(task_id: str, user_id: Optional[str] = None) -> bool:
    return await atualizar_entry(
        entry_id=task_id,
        user_id=user_id or _get_user_id(),
        updates={"status": "done"},
    )


async def atualizar_tarefa(
    task_id: str,
    titulo: Optional[str] = None,
    status: Optional[str] = None,
    prioridade: Optional[str] = None,
    user_id: Optional[str] = None,
) -> bool:
    updates = _clean_payload({
        "title": titulo,
        "status": _STATUS_TO_ENTRY.get(status, status) if status else None,
    })
    if prioridade:
        updates["content"] = {"priority": prioridade}
    if not updates:
        return False
    return await atualizar_entry(entry_id=task_id, user_id=user_id or _get_user_id(), updates=updates)


async def deletar_tarefa(task_id: str, user_id: Optional[str] = None) -> bool:
    return await deletar_entry(entry_id=task_id, user_id=user_id or _get_user_id())


async def marcar_tarefa_concluida(task_id: str, user_id: Optional[str] = None) -> bool:
    return await concluir_tarefa(task_id=task_id, user_id=user_id)


# ─────────────────────────────────────────
# LEMBRETES — wrappers
# ─────────────────────────────────────────

async def criar_lembrete(
    titulo: str,
    remind_at: str,
    descricao: Optional[str] = None,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    uid = user_id or _get_user_id()
    entry = await criar_entry(
        user_id=uid,
        type="reminder",
        title=titulo,
        content=_clean_payload({"description": descricao, "remind_at": remind_at}),
    )
    if entry.get("id"):
        await criar_reminder_entry(entry_id=entry["id"], remind_at=remind_at, user_id=uid)
    return [entry] if entry else []


async def listar_lembretes(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    return await listar_entries(user_id=user_id or _get_user_id(), type="reminder")


# ─────────────────────────────────────────
# CONTATOS — wrappers
# ─────────────────────────────────────────

async def criar_contato(
    nome: str,
    email: Optional[str] = None,
    telefone: Optional[str] = None,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    uid = user_id or _get_user_id()
    result = await criar_entry(
        user_id=uid,
        type="contact",
        title=nome,
        content=_clean_payload({"email": email, "phone": telefone}),
    )
    return [result] if result else []


async def buscar_contato(termo: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    return await buscar_entries(query=termo, user_id=user_id or _get_user_id(), type="contact")


async def listar_contatos(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    return await listar_entries(user_id=user_id or _get_user_id(), type="contact")


async def atualizar_contato(
    contact_id: str,
    nome: Optional[str] = None,
    email: Optional[str] = None,
    telefone: Optional[str] = None,
    user_id: Optional[str] = None,
) -> bool:
    updates = _clean_payload({"title": nome})
    content = _clean_payload({"email": email, "phone": telefone})
    if content:
        updates["content"] = content
    if not updates:
        return False
    return await atualizar_entry(entry_id=contact_id, user_id=user_id or _get_user_id(), updates=updates)


# ─────────────────────────────────────────
# NOTAS — wrappers
# ─────────────────────────────────────────

async def criar_nota(
    titulo: str,
    conteudo: str,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    uid = user_id or _get_user_id()
    result = await criar_entry(
        user_id=uid,
        type="note",
        title=titulo,
        content={"body": conteudo},
    )
    return [result] if result else []


async def listar_notas(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    return await listar_entries(user_id=user_id or _get_user_id(), type="note")


async def buscar_nota(query: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    return await buscar_entries(query=query, user_id=user_id or _get_user_id(), type="note")


async def atualizar_nota(
    note_id: str,
    titulo: Optional[str] = None,
    conteudo: Optional[str] = None,
    user_id: Optional[str] = None,
) -> bool:
    updates = _clean_payload({"title": titulo})
    if conteudo:
        updates["content"] = {"body": conteudo}
    if not updates:
        return False
    return await atualizar_entry(entry_id=note_id, user_id=user_id or _get_user_id(), updates=updates)


# ─────────────────────────────────────────
# EVENTOS — wrappers
# ─────────────────────────────────────────

async def criar_evento(
    titulo: str,
    start_time: str,
    end_time: Optional[str] = None,
    descricao: Optional[str] = None,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    uid = user_id or _get_user_id()
    result = await criar_entry(
        user_id=uid,
        type="event",
        title=titulo,
        content=_clean_payload({"description": descricao, "end_time": end_time}),
        date=start_time,
    )
    return [result] if result else []


async def listar_eventos_hoje(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    events = await listar_entries(user_id=user_id or _get_user_id(), type="event", limit=200)
    today = _start_of_today_iso()
    tomorrow = _tomorrow_start_iso()
    return [e for e in events if e.get("date") and today <= e["date"] < tomorrow]


async def listar_eventos(
    user_id: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
) -> List[Dict[str, Any]]:
    events = await listar_entries(user_id=user_id or _get_user_id(), type="event", limit=200)
    if data_inicio:
        events = [e for e in events if e.get("date") and e["date"] >= data_inicio]
    if data_fim:
        events = [e for e in events if e.get("date") and e["date"] <= data_fim]
    return sorted(events, key=lambda e: e.get("date") or "")


async def deletar_evento(event_id: str, user_id: Optional[str] = None) -> bool:
    return await deletar_entry(entry_id=event_id, user_id=user_id or _get_user_id())


# ─────────────────────────────────────────
# FINANÇAS — wrappers
# ─────────────────────────────────────────

async def registrar_transacao(
    descricao: str,
    valor: float,
    tipo: str = "despesa",
    categoria: Optional[str] = None,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    uid = user_id or _get_user_id()
    result = await criar_entry(
        user_id=uid,
        type="transaction",
        title=descricao,
        content=_clean_payload({"amount": valor, "transaction_type": tipo, "category": categoria}),
        date=_now_iso(),
    )
    return [result] if result else []


async def listar_transacoes(
    user_id: Optional[str] = None,
    categoria: Optional[str] = None,
    tipo: Optional[str] = None,
) -> List[Dict[str, Any]]:
    entries = await listar_entries(user_id=user_id or _get_user_id(), type="transaction", limit=500)
    if categoria:
        entries = [e for e in entries if e.get("content", {}).get("category") == categoria]
    if tipo:
        entries = [e for e in entries if e.get("content", {}).get("transaction_type") == tipo]
    return entries


async def resumo_financeiro(user_id: Optional[str] = None) -> Dict[str, Any]:
    transacoes = await listar_transacoes(user_id=user_id)
    receitas = sum(float(t["content"].get("amount", 0)) for t in transacoes if t.get("content", {}).get("transaction_type") == "receita")
    despesas = sum(float(t["content"].get("amount", 0)) for t in transacoes if t.get("content", {}).get("transaction_type") == "despesa")
    por_categoria: Dict[str, float] = {}
    for t in transacoes:
        cat = t.get("content", {}).get("category") or "Outros"
        por_categoria[cat] = por_categoria.get(cat, 0) + float(t.get("content", {}).get("amount", 0))
    return {
        "receitas": receitas,
        "despesas": despesas,
        "saldo": receitas - despesas,
        "por_categoria": por_categoria,
        "total_transacoes": len(transacoes),
    }


# ─────────────────────────────────────────
# INTERAÇÕES — wrapper
# ─────────────────────────────────────────

async def registrar_interacao(
    tipo: str,
    conteudo: str,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    uid = user_id or _get_user_id()
    result = await criar_entry(
        user_id=uid,
        type="interaction",
        title=tipo,
        content={"content": conteudo},
    )
    return [result] if result else []


# ─────────────────────────────────────────
# PROJETOS — wrappers
# ─────────────────────────────────────────

async def criar_projeto(
    titulo: str,
    descricao: Optional[str] = None,
    prazo: Optional[str] = None,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    uid = user_id or _get_user_id()
    result = await criar_entry(
        user_id=uid,
        type="project",
        title=titulo,
        content=_clean_payload({"description": descricao, "progress": 0}),
        due_date=prazo,
    )
    return [result] if result else []


async def listar_projetos(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    return await listar_entries(user_id=user_id or _get_user_id(), type="project")


async def atualizar_projeto(
    project_id: str,
    titulo: Optional[str] = None,
    status: Optional[str] = None,
    progresso: Optional[int] = None,
    user_id: Optional[str] = None,
) -> bool:
    updates = _clean_payload({"title": titulo, "status": status})
    if progresso is not None:
        updates["content"] = {"progress": progresso}
    if not updates:
        return False
    return await atualizar_entry(entry_id=project_id, user_id=user_id or _get_user_id(), updates=updates)


# ─────────────────────────────────────────
# HÁBITOS — wrappers
# ─────────────────────────────────────────

async def criar_habito(
    titulo: str,
    frequencia: str,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    uid = user_id or _get_user_id()
    result = await criar_entry(
        user_id=uid,
        type="habit",
        title=titulo,
        content={"frequency": frequencia},
    )
    return [result] if result else []


async def registrar_checkin(habito_id: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    uid = user_id or _get_user_id()
    result = await criar_entry(
        user_id=uid,
        type="checkin",
        title="check-in",
        date=_now_iso(),
        parent_id=habito_id,
    )
    return [result] if result else []


async def listar_habitos(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    return await listar_entries(user_id=user_id or _get_user_id(), type="habit")


# ─────────────────────────────────────────
# METAS — wrappers
# ─────────────────────────────────────────

async def criar_meta(
    titulo: str,
    valor_alvo: float,
    valor_atual: float = 0,
    prazo: Optional[str] = None,
    user_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    uid = user_id or _get_user_id()
    result = await criar_entry(
        user_id=uid,
        type="goal",
        title=titulo,
        content={"target_value": valor_alvo, "current_value": valor_atual},
        due_date=prazo,
    )
    return [result] if result else []


async def atualizar_progresso_meta(goal_id: str, valor_atual: float) -> bool:
    client = _get_client()
    # Fetch current content to merge
    response = await _execute_sync(
        lambda: client.table("entries").select("content").eq("id", goal_id).execute()
    )
    data = getattr(response, "data", None) or []
    content = data[0].get("content", {}) if data else {}
    content["current_value"] = valor_atual
    return await atualizar_entry(
        entry_id=goal_id,
        user_id=_get_user_id(),
        updates={"content": content},
    )


async def listar_metas(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    return await listar_entries(user_id=user_id or _get_user_id(), type="goal")


# ─────────────────────────────────────────
# IA — inalterado
# ─────────────────────────────────────────

async def salvar_conversa_ia(
    titulo: str,
    mensagens: List[Dict[str, str]],
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    client = _get_client()
    conversation_payload = _clean_payload({
        "title": titulo,
        "user_id": user_id or _get_user_id(),
    })
    conversation_response = await _execute_sync(
        lambda: client.table("ai_conversations").insert(conversation_payload).execute()
    )
    conversation_data = getattr(conversation_response, "data", None) or []
    if not conversation_data:
        return {"conversation": None, "messages": []}
    conversation = conversation_data[0]
    conversation_id = conversation.get("id")
    message_payloads = [
        _clean_payload({
            "conversation_id": conversation_id,
            "role": m.get("role"),
            "content": m.get("content"),
        })
        for m in mensagens
    ]
    if message_payloads:
        await _execute_sync(lambda: client.table("ai_messages").insert(message_payloads).execute())
    return {"conversation": conversation, "messages": message_payloads}
