# CLAUDE.md — Instruções Operacionais do Jarvis

> Lido automaticamente pelo Claude Code antes de qualquer tarefa.
> Contém instruções operacionais, convenções e atalhos do projeto.
> Para contexto completo do projeto, leia também: JARVIS_CONTEXT.md

---

## ⚡ Regras Operacionais (SEMPRE SIGA)

1. **Leia JARVIS_CONTEXT.md primeiro** em sessões novas para ter contexto completo
2. **Nunca leia arquivos desnecessários** — use o contexto já fornecido
3. **Um commit por feature** — nunca acumule múltiplas mudanças num commit
4. **Sempre faça commit e push** ao final de cada tarefa concluída
5. **Atualize JARVIS_CONTEXT.md** ao final de cada sessão
6. **Prompts cirúrgicos** — mexa APENAS no que foi pedido, nada mais
7. **Bugs visíveis = corrigir sem pedir permissão** — se durante a leitura do código encontrar inconsistência, CSS conflitante, ou comportamento não intencional, corrige junto com a tarefa principal e documenta no commit.
8. **Design dopaminérgico é padrão** — todo novo componente deve ter: animação de entrada (`pvFadeUp` ou similar), hover com feedback visual (lift + shadow), ação com micro-interação (scale press, confetti em milestone).

---

## 📁 Mapa de Arquivos (não leia o que não precisa)

### Backend (`/Users/zacche/Downloads/jarvisIA-main`)
| Arquivo | Quando ler |
|---|---|
| `api.py` | Mudanças no chat, ferramentas, rotas |
| `prompts.py` | Mudanças de personalidade/tom |
| `supabase_client.py` | Mudanças no banco de dados |
| `agent.py` | Mudanças no agente de voz LiveKit |
| `automacao_jarvis.py` | NÃO TOCAR — legacy Windows |

### Frontend (`/Users/zacche/Desktop/jarvisnewfront`)
| Arquivo | Quando ler |
|---|---|
| `public/index.html` | Mudanças no chat, visual, componentes, telas internas |
| `src/app/api/chat/route.ts` | Mudanças no proxy do chat |
| `src/app/api/token/route.ts` | Mudanças no LiveKit token |
| `src/app/api/clients/route.ts` | Mudanças no proxy de clientes |
| `src/app/api/tasks/route.ts` | Mudanças no proxy de tarefas |
| `src/app/api/tasks/[id]/route.ts` | Mudanças no proxy de tarefas por ID |
| `src/app/api/context/route.ts` | Mudanças no proxy de contexto vivo |

---

## 🚀 Deploy

### Backend local (desenvolvimento)
```bash
cd /Users/zacche/Downloads/jarvisIA-main
python3 -m uvicorn api:app --reload   # porta 8000
```
**REGRA: não fazer `git push` no backend até a sessão ser encerrada.**
Acumula todos os commits locais e faz push apenas no final da sessão.

### Backend (Railway — produção)
```bash
cd /Users/zacche/Downloads/jarvisIA-main
git add .
git commit -m "tipo: descrição curta"
git push
# Railway faz deploy automático
```

### Frontend (Vercel)
```bash
cd /Users/zacche/Desktop/jarvisnewfront
git add .
git commit -m "tipo: descrição curta"
git push
# Vercel faz deploy automático
```

---

## 🎨 Convenções de Código

### Frontend (index.html)
- Fundo escuro/espacial — NUNCA mudar cores base
- Orb de partículas some ao iniciar chat (classe `.has-chat`)
- Textarea com auto-resize (min 1 linha, max 4 linhas)
- Animações: `fadeUp` para novas mensagens, `blink` para loading dots
- Sidebar: 56px de largura, ícones Tabler outline
- Cor primária: `#534AB7` (roxo)

### Backend (api.py)
- Ferramentas do Supabase + contexto vivo juntas em `TOOLS`
- `OBSIDIAN_TOOL_NAMES` não existe mais — foi removido
- Contexto vivo: título sempre `"contexto: NomeEntidade"`
- Entidades conhecidas: Gracie Barra, SoHo, DDpartssolution, Jarvis, autoescola, faculdade, financeiro

### Commits
```
feat: nova funcionalidade
fix: correção de bug
refactor: refatoração sem mudança de comportamento
docs: documentação
style: mudança visual sem lógica
```

---

## ❌ O Que NUNCA Fazer

- Não mudar o layout geral do frontend (sidebar, orb, cores base)
- Não tocar em `automacao_jarvis.py`
- Não criar novos arquivos de integração Obsidian (foi removido)
- Não instalar dependências sem necessidade
- Não refatorar código que não foi pedido
- Não fazer múltiplas mudanças num único prompt

---

## 💡 Atalhos de Contexto

Em vez de ler arquivos inteiros, use estas referências rápidas:

**"Como o chat funciona?"**
→ `public/index.html`: função `submit()` envia para `/api/chat` → `src/app/api/chat/route.ts` → Railway `/chat`

**"Como a tela de Tarefas funciona?"**
→ `public/index.html`: `TasksView` (React.createElement) → `/api/tasks` → Railway `/tasks`

**"Como a tela de Clientes funciona?"**
→ `public/index.html`: `ClientsView` com `_FIXED_CLIENTS` base → `/api/clients` + `/api/context?name=X` → Railway `/clients` e `/context`

**"Como o Jarvis decide o que fazer?"**
→ `api.py`: Gemini recebe system prompt + ferramentas → function calling → `_executar_ferramenta()`

**"Como o banco funciona?"**
→ `supabase_client.py`: 6 tabelas, tudo passa pela tabela `entries` com `type` + `content` JSONB

**"Como fazer deploy?"**
→ `git add . && git commit -m "..." && git push` em qualquer pasta — auto-deploy configurado

---

## 🔧 Comandos Úteis

```bash
# Ver logs do Railway em tempo real
railway logs

# Testar backend local
cd /Users/zacche/Downloads/jarvisIA-main
uvicorn api:app --reload

# Testar frontend local
cd /Users/zacche/Desktop/jarvisnewfront
npm run dev

# Compactar contexto quando sessão estiver longa
/compact
```

---

## 📊 Stack Resumida

```
Frontend:  Next.js + HTML standalone (Vercel)
Backend:   Python FastAPI (Railway)
Banco:     Supabase PostgreSQL
Memória:   Mem0
LLM:       Gemini 2.5 Flash
Voz:       LiveKit (configurado, não integrado ao front)
```
