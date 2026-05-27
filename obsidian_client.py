"""
obsidian_client.py
Cliente HTTP para o Obsidian Local REST API & MCP Server
URL: https://127.0.0.1:27124/
"""

import httpx
import os
from typing import Optional

OBSIDIAN_BASE_URL = os.getenv("OBSIDIAN_BASE_URL", "https://127.0.0.1:27124")
OBSIDIAN_API_KEY = os.getenv("OBSIDIAN_API_KEY", "")

# Headers padrão para todas as requisições
def _headers():
    return {
        "Authorization": f"Bearer {OBSIDIAN_API_KEY}",
        "Content-Type": "application/json",
    }

# Ignora verificação SSL do certificado self-signed do Obsidian
_client = httpx.AsyncClient(verify=False, timeout=10.0)


async def ler_nota(caminho: str) -> Optional[str]:
    """
    Lê o conteúdo de uma nota pelo caminho relativo no vault.
    Ex: 'Clientes/Gracie Barra.md'
    """
    try:
        url = f"{OBSIDIAN_BASE_URL}/vault/{caminho}"
        resp = await _client.get(url, headers=_headers())
        if resp.status_code == 200:
            return resp.text
        elif resp.status_code == 404:
            return None
        else:
            raise Exception(f"Erro ao ler nota: {resp.status_code} - {resp.text}")
    except httpx.RequestError as e:
        raise Exception(f"Obsidian não está acessível: {e}")


async def criar_ou_atualizar_nota(caminho: str, conteudo: str) -> bool:
    """
    Cria ou sobrescreve uma nota no vault.
    Ex: caminho='Clientes/Gracie Barra.md', conteudo='# Gracie Barra\n...'
    """
    try:
        url = f"{OBSIDIAN_BASE_URL}/vault/{caminho}"
        resp = await _client.put(
            url,
            headers={**_headers(), "Content-Type": "text/markdown"},
            content=conteudo.encode("utf-8"),
        )
        return resp.status_code in (200, 201, 204)
    except httpx.RequestError as e:
        raise Exception(f"Obsidian não está acessível: {e}")


async def adicionar_conteudo_nota(caminho: str, conteudo: str) -> bool:
    """
    Adiciona conteúdo ao FINAL de uma nota existente (append).
    Se a nota não existir, cria ela.
    """
    existente = await ler_nota(caminho)
    if existente is None:
        novo_conteudo = conteudo
    else:
        novo_conteudo = existente.rstrip() + "\n\n" + conteudo
    return await criar_ou_atualizar_nota(caminho, novo_conteudo)


async def listar_notas(pasta: str = "") -> list[str]:
    """
    Lista todos os arquivos em uma pasta do vault.
    Ex: pasta='Clientes/' retorna lista de caminhos
    """
    try:
        url = f"{OBSIDIAN_BASE_URL}/vault/{pasta}"
        resp = await _client.get(url, headers=_headers())
        if resp.status_code == 200:
            data = resp.json()
            return data.get("files", [])
        return []
    except httpx.RequestError as e:
        raise Exception(f"Obsidian não está acessível: {e}")


async def buscar_no_vault(query: str) -> list[dict]:
    """
    Busca texto em todas as notas do vault.
    Retorna lista de {filename, score, matches}
    """
    try:
        url = f"{OBSIDIAN_BASE_URL}/search/simple/"
        resp = await _client.post(
            url,
            headers=_headers(),
            params={"query": query, "contextLength": 200},
        )
        if resp.status_code == 200:
            return resp.json()
        return []
    except httpx.RequestError as e:
        raise Exception(f"Obsidian não está acessível: {e}")


async def deletar_nota(caminho: str) -> bool:
    """
    Deleta uma nota do vault.
    """
    try:
        url = f"{OBSIDIAN_BASE_URL}/vault/{caminho}"
        resp = await _client.delete(url, headers=_headers())
        return resp.status_code in (200, 204)
    except httpx.RequestError as e:
        raise Exception(f"Obsidian não está acessível: {e}")


async def status_obsidian() -> dict:
    """
    Verifica se o Obsidian está online e retorna info do vault.
    """
    try:
        url = f"{OBSIDIAN_BASE_URL}/"
        resp = await _client.get(url, headers=_headers())
        if resp.status_code == 200:
            return {"online": True, "info": resp.json()}
        return {"online": False}
    except Exception:
        return {"online": False}
