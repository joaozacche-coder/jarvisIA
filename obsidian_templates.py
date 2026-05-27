"""
obsidian_templates.py
Templates de notas para o segundo cérebro do João no Obsidian.
"""

from datetime import datetime


def template_cliente(nome: str, tipo: str = "cliente") -> str:
    hoje = datetime.now().strftime("%d/%m/%Y")
    return f"""# {nome}

> **Tipo:** {tipo}  
> **Criado em:** {hoje}  
> **Gerenciado pelo Jarvis** 🤖

---

## 📋 Visão Geral

<!-- Descrição geral do cliente/projeto -->

---

## 🎯 Objetivos

<!-- O que o cliente quer alcançar -->

---

## 📊 Status Atual

<!-- Situação atual dos projetos -->

---

## 📝 Histórico de Ações

<!-- Jarvis vai atualizar automaticamente -->

---

## 💡 Informações Importantes

<!-- Dados relevantes: contatos, logins, preferências -->

---

## ✅ Tarefas Ativas

<!-- Sincronizado com o Supabase -->

---

## 📅 Próximos Passos

<!-- O que precisa ser feito -->

---

## 🗒️ Notas Avulsas

<!-- Anotações rápidas -->
"""


def template_area_vida(nome: str, descricao: str = "") -> str:
    hoje = datetime.now().strftime("%d/%m/%Y")
    return f"""# {nome}

> **Área de vida**  
> **Criado em:** {hoje}  
> {descricao}

---

## 📌 Resumo

---

## 🎯 Metas

---

## 📈 Progresso

---

## 📝 Anotações

---

## 🔗 Links Relacionados

"""


def template_projeto(nome: str, cliente: str = "", descricao: str = "") -> str:
    hoje = datetime.now().strftime("%d/%m/%Y")
    return f"""# {nome}

> **Projeto**  
> **Cliente:** {cliente if cliente else "Pessoal"}  
> **Iniciado em:** {hoje}  
> {descricao}

---

## 🎯 Objetivo

---

## 📋 Escopo

---

## 🚀 Status

- [ ] Planejamento
- [ ] Em execução
- [ ] Revisão
- [ ] Concluído

---

## 📝 Tarefas

---

## 📅 Linha do Tempo

---

## 💰 Financeiro

---

## 📎 Recursos & Links

---

## 🗒️ Notas

"""


def template_indice_principal() -> str:
    hoje = datetime.now().strftime("%d/%m/%Y")
    return f"""# 🧠 Segundo Cérebro - João Zacche

> Gerenciado pelo **Jarvis** 🤖  
> Última atualização: {hoje}

---

## 👤 Sobre Mim

- **Nome:** João Zacche
- **Trabalho:** Gestor de Tráfego Pago
- **GitHub:** joaozacche-coder

---

## 💼 Clientes Ativos

- [[Clientes/Gracie Barra]]
- [[Clientes/SoHo]]
- [[Clientes/DDpartssolution]]

---

## 🚀 Projetos

- [[Projetos/Jarvis]]

---

## 📚 Aprendizados

- [[Aprendizados/Cursos]]
- [[Aprendizados/Autoescola]]
- [[Aprendizados/Faculdade]]

---

## 🌱 Áreas da Vida

- [[Areas/Financeiro]]
- [[Areas/Saude]]
- [[Areas/Carreira]]
- [[Areas/Pessoal]]

---

## 📋 Recursos

- [[Recursos/Ferramentas]]
- [[Recursos/Referencias]]

---

## 📅 Diário

- [[Diario/Hoje]]

"""


def entrada_historico(texto: str, tipo: str = "nota") -> str:
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    emoji = {
        "nota": "📝",
        "tarefa": "✅",
        "reuniao": "🤝",
        "lembrete": "⏰",
        "resultado": "📊",
        "contato": "👤",
        "financeiro": "💰",
    }.get(tipo, "📌")
    return f"- **{agora}** {emoji} {texto}"
