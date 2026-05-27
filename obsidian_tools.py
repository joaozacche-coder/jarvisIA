"""
obsidian_tools.py
6 ferramentas que o Jarvis (Gemini) usa para interagir com o Obsidian.
Adicione estas ferramentas na lista TOOLS do api.py.
"""

import json
from obsidian_client import (
    ler_nota,
    criar_ou_atualizar_nota,
    adicionar_conteudo_nota,
    listar_notas,
    buscar_no_vault,
    deletar_nota,
    status_obsidian,
)
from obsidian_templates import (
    template_cliente,
    template_area_vida,
    template_projeto,
    template_indice_principal,
    entrada_historico,
)

# ─────────────────────────────────────────────
# DEFINIÇÕES DAS FERRAMENTAS (para o Gemini)
# ─────────────────────────────────────────────

OBSIDIAN_TOOL_DEFINITIONS = [
    {
        "name": "obsidian_ler_nota",
        "description": (
            "Lê o conteúdo de uma nota do Obsidian (segundo cérebro do João). "
            "Use quando o usuário perguntar sobre um cliente, projeto, área de vida, "
            "curso, autoescola, faculdade, ou qualquer informação salva no vault."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "caminho": {
                    "type": "string",
                    "description": (
                        "Caminho relativo da nota no vault. Exemplos: "
                        "'Clientes/Gracie Barra.md', 'Projetos/Jarvis.md', "
                        "'Aprendizados/Autoescola.md', 'Areas/Financeiro.md'"
                    ),
                }
            },
            "required": ["caminho"],
        },
    },
    {
        "name": "obsidian_salvar_informacao",
        "description": (
            "Salva ou atualiza informação importante no Obsidian. "
            "Use quando o usuário mencionar algo relevante sobre clientes, projetos, "
            "cursos, faculdade, autoescola, finanças, metas, contatos, aprendizados, "
            "ou qualquer coisa importante da vida dele. "
            "SEMPRE salve informações importantes no segundo cérebro!"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "caminho": {
                    "type": "string",
                    "description": (
                        "Caminho da nota. Use a estrutura: "
                        "Clientes/NomeCliente.md, Projetos/NomeProjeto.md, "
                        "Aprendizados/Tema.md, Areas/Financeiro.md, "
                        "Recursos/Ferramentas.md, Diario/YYYY-MM-DD.md"
                    ),
                },
                "conteudo": {
                    "type": "string",
                    "description": "Texto em Markdown a ser adicionado ou salvo na nota.",
                },
                "modo": {
                    "type": "string",
                    "enum": ["adicionar", "substituir"],
                    "description": (
                        "'adicionar' para appender ao final da nota existente (padrão). "
                        "'substituir' para sobrescrever a nota inteira."
                    ),
                },
            },
            "required": ["caminho", "conteudo"],
        },
    },
    {
        "name": "obsidian_criar_nota_cliente",
        "description": (
            "Cria uma nota estruturada para um cliente no Obsidian. "
            "Use quando o usuário mencionar um novo cliente ou quiser organizar "
            "informações de um cliente existente (Gracie Barra, SoHo, DDpartssolution, etc)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "nome_cliente": {
                    "type": "string",
                    "description": "Nome do cliente. Ex: 'Gracie Barra', 'SoHo', 'DDpartssolution'",
                },
                "tipo": {
                    "type": "string",
                    "description": "Tipo: 'cliente', 'projeto', 'parceiro'. Default: 'cliente'",
                },
                "informacoes_iniciais": {
                    "type": "string",
                    "description": "Informações iniciais a adicionar na nota (opcional).",
                },
            },
            "required": ["nome_cliente"],
        },
    },
    {
        "name": "obsidian_buscar",
        "description": (
            "Busca informações em todas as notas do Obsidian. "
            "Use quando o usuário perguntar algo e você não souber em qual nota está, "
            "ou quando quiser encontrar referências a um tema específico."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Texto a buscar no vault. Ex: 'reunião', 'campanha', 'pagamento'",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "obsidian_listar_notas",
        "description": (
            "Lista todas as notas de uma pasta do vault. "
            "Use para ver o que existe em Clientes/, Projetos/, Aprendizados/, etc."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "pasta": {
                    "type": "string",
                    "description": "Nome da pasta. Ex: 'Clientes', 'Projetos', 'Aprendizados', 'Areas'",
                }
            },
            "required": ["pasta"],
        },
    },
    {
        "name": "obsidian_registrar_historico",
        "description": (
            "Registra uma ação, evento ou informação importante no histórico de um cliente ou projeto. "
            "Use após reuniões, resultados de campanhas, pagamentos recebidos, "
            "decisões tomadas, ou qualquer evento relevante."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "destino": {
                    "type": "string",
                    "description": "Caminho da nota. Ex: 'Clientes/Gracie Barra.md'",
                },
                "texto": {
                    "type": "string",
                    "description": "Descrição do evento/ação. Ex: 'Campanha de maio gerou 150 leads'",
                },
                "tipo": {
                    "type": "string",
                    "enum": ["nota", "tarefa", "reuniao", "lembrete", "resultado", "contato", "financeiro"],
                    "description": "Tipo do registro para categorização.",
                },
            },
            "required": ["destino", "texto"],
        },
    },
]


# ─────────────────────────────────────────────
# EXECUTORES DAS FERRAMENTAS
# ─────────────────────────────────────────────

async def executar_obsidian_tool(tool_name: str, tool_args: dict) -> str:
    """
    Executa a ferramenta do Obsidian e retorna resultado como string.
    Chame isso no seu loop de tool_use no api.py.
    """
    try:
        if tool_name == "obsidian_ler_nota":
            conteudo = await ler_nota(tool_args["caminho"])
            if conteudo is None:
                return f"Nota '{tool_args['caminho']}' não encontrada no vault."
            return f"Conteúdo da nota '{tool_args['caminho']}':\n\n{conteudo}"

        elif tool_name == "obsidian_salvar_informacao":
            caminho = tool_args["caminho"]
            conteudo = tool_args["conteudo"]
            modo = tool_args.get("modo", "adicionar")

            if modo == "substituir":
                sucesso = await criar_ou_atualizar_nota(caminho, conteudo)
            else:
                sucesso = await adicionar_conteudo_nota(caminho, conteudo)

            if sucesso:
                return f"✅ Informação salva com sucesso em '{caminho}'."
            return f"❌ Erro ao salvar em '{caminho}'."

        elif tool_name == "obsidian_criar_nota_cliente":
            nome = tool_args["nome_cliente"]
            tipo = tool_args.get("tipo", "cliente")
            info = tool_args.get("informacoes_iniciais", "")

            caminho = f"Clientes/{nome}.md"
            conteudo = template_cliente(nome, tipo)

            # Se veio info inicial, adiciona na seção de Visão Geral
            if info:
                conteudo = conteudo.replace(
                    "<!-- Descrição geral do cliente/projeto -->",
                    info
                )

            sucesso = await criar_ou_atualizar_nota(caminho, conteudo)
            if sucesso:
                return f"✅ Nota do cliente '{nome}' criada em '{caminho}'."
            return f"❌ Erro ao criar nota do cliente '{nome}'."

        elif tool_name == "obsidian_buscar":
            resultados = await buscar_no_vault(tool_args["query"])
            if not resultados:
                return f"Nenhum resultado encontrado para '{tool_args['query']}'."

            linhas = [f"Resultados para '{tool_args['query']}':"]
            for r in resultados[:5]:  # limita a 5 resultados
                filename = r.get("filename", "")
                matches = r.get("matches", [])
                trecho = matches[0].get("context", "") if matches else ""
                linhas.append(f"\n📄 **{filename}**\n> {trecho[:200]}")
            return "\n".join(linhas)

        elif tool_name == "obsidian_listar_notas":
            pasta = tool_args["pasta"].rstrip("/") + "/"
            arquivos = await listar_notas(pasta)
            if not arquivos:
                return f"Nenhuma nota encontrada em '{pasta}'."
            lista = "\n".join(f"- {f}" for f in arquivos)
            return f"Notas em '{pasta}':\n{lista}"

        elif tool_name == "obsidian_registrar_historico":
            destino = tool_args["destino"]
            texto = tool_args["texto"]
            tipo = tool_args.get("tipo", "nota")

            entrada = entrada_historico(texto, tipo)
            sucesso = await adicionar_conteudo_nota(destino, entrada)

            if sucesso:
                return f"✅ Registrado no histórico de '{destino}': {texto}"
            return f"❌ Erro ao registrar histórico em '{destino}'."

        else:
            return f"Ferramenta '{tool_name}' não reconhecida."

    except Exception as e:
        return f"❌ Erro no Obsidian ({tool_name}): {str(e)}. Verifique se o Obsidian está aberto."
