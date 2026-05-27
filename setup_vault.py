"""
setup_vault.py
Cria a estrutura inicial do segundo cérebro do João no Obsidian.
Execute UMA VEZ: python setup_vault.py
"""

import asyncio
import os
import sys

# Carrega variáveis de ambiente do .env se existir
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configura as vars direto se não tiver .env
if not os.getenv("OBSIDIAN_API_KEY"):
    os.environ["OBSIDIAN_API_KEY"] = "696ca72a4c7abcacd35b5ca45603f11db226d0c41c7b3d9eb799352a6a8b02f7"
if not os.getenv("OBSIDIAN_BASE_URL"):
    os.environ["OBSIDIAN_BASE_URL"] = "https://127.0.0.1:27124"

from obsidian_client import criar_ou_atualizar_nota, status_obsidian
from obsidian_templates import (
    template_indice_principal,
    template_cliente,
    template_area_vida,
    template_projeto,
)


ESTRUTURA_VAULT = {
    # Índice principal
    "README.md": template_indice_principal(),

    # Clientes ativos
    "Clientes/Gracie Barra.md": template_cliente("Gracie Barra", "cliente"),
    "Clientes/SoHo.md": template_cliente("SoHo", "cliente"),
    "Clientes/DDpartssolution.md": template_cliente("DDpartssolution", "cliente"),

    # Projetos
    "Projetos/Jarvis.md": template_projeto(
        "Jarvis",
        descricao="Assistente pessoal de IA — o melhor do mundo."
    ),

    # Áreas da vida
    "Areas/Financeiro.md": template_area_vida(
        "Financeiro",
        "Controle de receitas, despesas, metas financeiras."
    ),
    "Areas/Saude.md": template_area_vida(
        "Saúde",
        "Bem-estar físico e mental."
    ),
    "Areas/Carreira.md": template_area_vida(
        "Carreira",
        "Evolução profissional, habilidades, networking."
    ),
    "Areas/Pessoal.md": template_area_vida(
        "Pessoal",
        "Vida pessoal, relacionamentos, hobbies."
    ),

    # Aprendizados
    "Aprendizados/Cursos.md": template_area_vida(
        "Cursos",
        "Todos os cursos que estou fazendo ou já fiz."
    ),
    "Aprendizados/Autoescola.md": template_area_vida(
        "Autoescola",
        "Progresso na autoescola, provas, datas."
    ),
    "Aprendizados/Faculdade.md": template_area_vida(
        "Faculdade",
        "Disciplinas, notas, trabalhos, provas."
    ),
    "Aprendizados/Trafego Pago.md": template_area_vida(
        "Tráfego Pago",
        "Conhecimentos, estratégias e aprendizados sobre tráfego pago."
    ),

    # Recursos
    "Recursos/Ferramentas.md": template_area_vida(
        "Ferramentas",
        "Ferramentas, softwares e serviços que uso."
    ),
    "Recursos/Referencias.md": template_area_vida(
        "Referências",
        "Links, artigos e materiais de referência."
    ),
    "Recursos/Contatos.md": template_area_vida(
        "Contatos",
        "Pessoas importantes: clientes, parceiros, mentores."
    ),
}


async def setup():
    print("🔍 Verificando conexão com o Obsidian...")
    status = await status_obsidian()

    if not status["online"]:
        print("❌ Obsidian não está acessível!")
        print("   Verifique se:")
        print("   1. O Obsidian está aberto")
        print("   2. O plugin Local REST API está ativo")
        print("   3. A URL é https://127.0.0.1:27124")
        sys.exit(1)

    print(f"✅ Obsidian online! Info: {status.get('info', {})}")
    print(f"\n📁 Criando estrutura do vault ({len(ESTRUTURA_VAULT)} notas)...\n")

    criadas = 0
    erros = 0

    for caminho, conteudo in ESTRUTURA_VAULT.items():
        try:
            sucesso = await criar_ou_atualizar_nota(caminho, conteudo)
            if sucesso:
                print(f"   ✅ {caminho}")
                criadas += 1
            else:
                print(f"   ❌ {caminho} — falhou")
                erros += 1
        except Exception as e:
            print(f"   ❌ {caminho} — erro: {e}")
            erros += 1

    print(f"\n{'='*50}")
    print(f"✅ {criadas} notas criadas com sucesso!")
    if erros:
        print(f"❌ {erros} erros")
    print(f"\n🧠 Segundo cérebro do João pronto no Obsidian!")
    print(f"   Estrutura criada:")
    print(f"   📁 Clientes/ (Gracie Barra, SoHo, DDpartssolution)")
    print(f"   📁 Projetos/ (Jarvis)")
    print(f"   📁 Areas/ (Financeiro, Saúde, Carreira, Pessoal)")
    print(f"   📁 Aprendizados/ (Cursos, Autoescola, Faculdade, Tráfego Pago)")
    print(f"   📁 Recursos/ (Ferramentas, Referências, Contatos)")


if __name__ == "__main__":
    asyncio.run(setup())
