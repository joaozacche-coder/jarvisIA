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


async def listar_tarefas(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    client = _get_client()
    response = await _execute_sync(
        lambda: client.table("tasks")
        .select("*")
        .eq("user_id", user_id or _get_user_id())
        .order("due_date", desc=False)
        .execute()
    )
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
