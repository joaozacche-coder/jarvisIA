# JARVIS — Contexto Completo do Projeto
> Arquivo de contexto para o Claude (sócio de desenvolvimento).
> Sempre leia este arquivo antes de qualquer sessão de desenvolvimento.
> Atualizado após cada sessão pelo Claude Code.

---

## 👤 Identidade do Criador

- **Nome:** João Zacche
- **GitHub:** joaozacche-coder
- **Trabalho:** Gestor de Tráfego Pago (Meta Ads, Google Ads)
- **Clientes ativos:** Gracie Barra (Taquara + Pechincha), SoHo (casa de shows), DDpartssolution
- **Contexto pessoal:** tem TDAH, precisa de organização total da vida
- **Visão:** construir o melhor assistente pessoal do mundo e vender como SaaS

---

## 🎯 Visão do Produto

O Jarvis não é um assistente de produtividade — é um **assistente de VIDA**.
Ele sabe sobre trabalho, saúde, finanças, relacionamentos, sonhos, rotina, clientes, projetos pessoais, tudo.

Inspirações de UX: Linear, Raycast, Superhuman, Arc Browser, Nectar IA (meu-nectar.com)
Objetivo: zero fricção, contexto sempre presente, resposta certeira, visual que dá prazer de usar.

---

## 🏗️ Infraestrutura Atual

| Componente | Tecnologia | URL/Local |
|---|---|---|
| Frontend | Next.js | `/Users/zacche/Desktop/jarvisnewfront` → https://jarvisnewfront.vercel.app |
| Backend | Python FastAPI | `/Users/zacche/Downloads/jarvisIA-main` → https://jarvisia-production.up.railway.app |
| Banco | Supabase | Projeto: rare-smile |
| Memória | Mem0 | user_id: JoaoZacche |
| Voz | LiveKit | Configurado, não integrado ao front ainda |
| LLM | Gemini 2.5 Flash | Via Google AI SDK |
| Deploy Backend | Railway | Auto-deploy via GitHub push |
| Deploy Frontend | Vercel | Auto-deploy via GitHub push |

---

## 📁 Arquivos do Backend (`jarvisIA-main`)

| Arquivo | Função |
|---|---|
| `api.py` | FastAPI — rota POST /chat (Gemini + Mem0 + Supabase + contexto vivo) |
| `agent.py` | Agente LiveKit de voz (Google Realtime Model + Mem0) |
| `supabase_client.py` | Funções universais do banco (criar, listar, atualizar, deletar, buscar entries) |
| `prompts.py` | AGENT_INSTRUCTION + SESSION_INSTRUCTION — personalidade do Jarvis |
| `automacao_jarvis.py` | Controle de arquivos/sistema (Windows only, wrapped em try/except) |
| `Procfile` | `web: uvicorn api:app` + `worker: python agent.py dev` |

---

## 🗄️ Arquitetura do Banco (Supabase)

6 tabelas universais escaláveis para 10k+ usuários:

| Tabela | Função |
|---|---|
| `users_profile` | Perfil do usuário |
| `entries` | Coração do sistema — qualquer dado da vida (type + content JSONB) |
| `relations` | Relações entre entries |
| `files` | Arquivos vinculados a entries |
| `reminders` | Lembretes para qualquer entry |
| `sessions` | Histórico de conversas para analytics |

**Tipos de entry disponíveis:**
`task, note, event, project, habit, goal, transaction, reminder, contact`

**Convenção do segundo cérebro (contexto vivo):**
Notas do tipo `note` com título `"contexto: NomeCliente"` e tags `["contexto-vivo", "nome-cliente"]`

---

## 🔧 Ferramentas do Agente (api.py)

### Supabase:
- `criar_entry` — cria task, note, event, project, habit, goal, transaction, reminder, contact
- `listar_entries` — filtra por tipo, status, tags
- `atualizar_entry` — edita qualquer campo
- `deletar_entry` — remove
- `buscar_entries` — busca semântica por título
- `criar_reminder` — lembra de qualquer entry

### Segundo Cérebro (Contexto Vivo):
- `buscar_contexto_vivo` — lê estado atual de cliente/projeto/área
- `atualizar_contexto_vivo` — atualiza UMA nota por entidade (nunca duplica)

**Entidades conhecidas com contexto vivo:**
Gracie Barra, SoHo, DDpartssolution, Jarvis, autoescola, faculdade, financeiro

---

## 🧠 Personalidade do Jarvis

Tom: **sócio inteligente que já trabalhou contigo por anos**.
Referência: Alfred do Batman + sócio de agência.

**Regras de ouro:**
- NUNCA confirma ações como robô ("Entendido! Tarefa criada!")
- Máximo 2 linhas para confirmações
- Antecipa próximo passo em vez de só confirmar
- Nunca faz múltiplas perguntas — só UMA por resposta
- Celebra conquistas de forma seca e genuína (sem emojis)
- Percebe estresse e adapta o tom
- Para assuntos pessoais (saúde, família), muda para tom humano sem virar terapeuta
- Chama o usuário de "Chefe" naturalmente

**Exemplos corretos:**
- "preciso subir campanha da SoHo" → "Feito. Prazo?"
- "tive reunião com Gracie Barra" → "E aí, fechou alguma coisa?"
- "não dormi bem" → "Que horas vai conseguir parar hoje?"
- "fechei um cliente novo" → "Qual? Vou já abrir o dossiê."

---

## 🌐 Variáveis de Ambiente

### Railway (backend):
```
GOOGLE_API_KEY=...
MEM0_API_KEY=...
SUPABASE_URL=...
SUPABASE_SERVICE_KEY=...
LIVEKIT_URL=...
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
JARVIS_USER_ID=JoaoZacche
```

### Vercel (frontend):
```
LIVEKIT_URL=...
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
```

---

## 🎨 Frontend Atual

**Arquivo principal:** `public/index.html` (HTML standalone servido via rewrite no Next.js)

**Visual atual:**
- Fundo escuro/espacial com estrelas
- Orb de partículas 3D (VoiceOrb) centralizado — some quando chat inicia
- Sidebar com ícones à esquerda
- Chat ocupa tela inteira quando ativo
- Input bar na parte inferior (textarea com auto-resize)
- 3 dots animados quando Jarvis está pensando
- Botão copiar em cada resposta
- Retry inline em caso de erro
- Auto-scroll suave para última mensagem
- `white-space: pre-wrap` nas respostas

**Arquivos Next.js:**
- `src/app/api/token/route.ts` — gera JWT do LiveKit
- `src/app/api/chat/route.ts` — proxy para o backend Railway
- `src/app/api/clients/route.ts` — proxy para GET /clients
- `src/app/api/tasks/route.ts` — proxy para GET/POST /tasks
- `src/app/api/tasks/[id]/route.ts` — proxy para PATCH/DELETE /tasks/:id
- `src/app/api/context/route.ts` — proxy para GET /context?name=X

---

## ✅ O Que Está Funcionando

- Chat com personalidade do Jarvis (chama de "Chefe")
- Memória persistente entre sessões via Mem0
- Criação automática de tarefas/projetos/contatos
- Proatividade — lembra tarefas pendentes em cada conversa
- Data e hora de Brasília no contexto
- Segundo cérebro com contexto vivo por cliente/projeto
- Salva contexto automaticamente sem precisar pedir
- Lembra entre sessões (testado: Gracie Barra)
- Frontend bonito na Vercel
- Backend no Railway com redeploy automático via GitHub
- Railway CLI configurado localmente
- Orb some ao iniciar conversa

---

## 🚧 O Que Está Pendente (ordem de prioridade)

### FASE 1 — Telas internas
1. ~~**Tela de Tarefas**~~ ✅ — dados reais do Supabase, loading state, modal Nova Tarefa, toggle done/undone, stats ao vivo
2. ~~**Tela de Clientes**~~ ✅ — 3 clientes fixos sempre visíveis, CountUp, avatar, ponto pulsante, divider animado, cursor piscando, estado vazio, modal Novo Cliente, busca de contexto robusta
3. ~~**Tela de Finanças**~~ ✅ — transações reais, saldo, gráfico de barras, modal Nova Transação, animações fin-*
4. **Tela de Agenda** — eventos do dia/semana
5. **Tela de Segundo Cérebro** — notas, aprendizados, áreas de vida

### FASE 2 — Chat inteligente com blocos
6. Componentes visuais reutilizáveis (card de tarefa, card de cliente, pill de métrica)
7. Jarvis retorna JSON estruturado quando relevante
8. Chat usa os mesmos componentes das telas

### FASE 3 — Voz
9. Conectar microfone do frontend ao agente LiveKit que já está rodando

### FASE 4 — Automação e proatividade
10. Briefing diário automático toda manhã
11. Notificações push de lembretes

### FASE 5 — Escala
12. Autenticação multi-usuário
13. Onboarding para novos usuários
14. PWA mobile com notificações
15. Integrações externas (Gmail, Google Calendar, WhatsApp)

---

## 🔑 Decisões Tomadas (não reverter)

| Decisão | Motivo |
|---|---|
| Segundo cérebro no Supabase (não Obsidian) | Obsidian não escala para múltiplos usuários |
| Gemini 2.5 Flash como LLM | Gratuito, rápido, function calling robusto |
| Sem Tavily/busca web por agora | Quando trocar para Claude API ou GPT-4o, busca vem nativa |
| Sem OpenClaw | É produto concorrente local, não componente integrável |
| 6 tabelas universais com JSONB | Cobre qualquer nicho sem criar novas tabelas |
| Contexto vivo por entidade (não eventos isolados) | Jarvis sempre sabe o estado atual, não só histórico |
| HTML standalone em public/index.html | Funciona como SPA sem complexidade Next.js |

---

## 🐛 Problemas Conhecidos

- `automacao_jarvis.py` — automação de PC parou de funcionar (Windows only, baixa prioridade)
- LiveKit microfone não conecta no frontend ainda (fase 3)
- ngrok URL muda a cada reinício — script `~/jarvis_start.sh` automatiza mas não é mais necessário (Obsidian removido)

---

## 📝 Histórico de Sessões

**Jarvis 1:** Setup inicial, curso Python + LiveKit + Gemini, frontend básico
**Jarvis 2:** Supabase estruturado, 6 tabelas universais, conectou agente ao banco
**Jarvis 3:** Frontend redesenhado, orb de partículas, integração chat↔backend
**Jarvis 4:** Tentativa de integrar Obsidian, problemas de contexto de limite
**Jarvis 5:**
- Obsidian integrado e depois removido (não escala)
- Segundo cérebro migrado 100% para Supabase
- Contexto vivo implementado (buscar_contexto_vivo + atualizar_contexto_vivo)
- Personalidade do Jarvis reescrita (Alfred + sócio de agência)
- Frontend melhorado: textarea auto-resize, loading dots, orb some ao chatear
- Railway CLI configurado
- Mockup de novo frontend criado (blocos dopaminérgicos estilo Nectar)
- Decisão: construir telas internas antes de gamificar o chat

**Jarvis 6:**
- SEGUNDO_CEREBRO_RULES reescrito: atualizar_contexto_vivo primeiro, buscar só quando perguntado
- AGENT_INSTRUCTION completamente reescrita — Jarvis como assistente de VIDA (Alfred + sócio de agência), inteligência emocional, tom adaptável, sem respostas de robô
- JARVIS_CONTEXT.md estabelecido como fonte de verdade — atualizado automaticamente ao final de cada sessão
- Tela de Tarefas conectada ao Supabase: REST endpoints no backend (GET/POST/PATCH/DELETE /tasks), proxy routes Next.js, dados reais, loading state, modal Nova Tarefa, toggle done com update otimista, stats ao vivo, status "Atrasada" para tarefas vencidas
- Tela de tarefas migrada para dentro do index.html: TasksView renderiza inline no mesmo visual escuro quando active === 'tasks', sem navegação de página; sidebar onSelect volta a ser setActive; CSS prefixado com .tv-
- TasksView redesenhada — visual dopaminérgico Linear/Nectar: keyframes (tvFadeUp, tvSlideDown, tvSlideOut, tvShimmer, tvScaleIn, tvPulse), orb some ao entrar em tarefas (.is-tasks), cards de stats com hover, tabs como pills (Todas/A Fazer/Concluídas/Atrasadas), checkboxes circulares com SVG, tags de cliente coloridas, animação de saída ao marcar como concluída (dying Set), skeleton shimmer no loading, modal com priority pills (não select), modal com spring animation

**Jarvis 7:**
- Backend /clients: _KNOWN_CLIENTS garante 3 clientes fixos sempre, campo has_context, task_count por cliente, asyncio.gather para queries paralelas
- Next.js route /api/clients criada (proxy para Railway /clients)
- ClientsView completamente redesenhada: CountUp animado, avatar com initial + crmRotateIn, ponto pulsante verde (crmPulse), divider animado (crmDivider), cursor piscando no próximo passo (crmBlink), estado vazio com ⚡ para clientes sem histórico, modal Novo Cliente com spring animation, onChat genérico (suporta mensagens customizadas)
- CSS CRM expandido: crm-modal-overlay, crm-modal-input, crm-modal-actions, crm-empty-state, crm-card--empty

**Jarvis 8:**
- BUG FIX — 3 clientes sempre visíveis: _FIXED_CLIENTS hardcodado no frontend como base imutável; backend enriquece via merge por client_name; fallback garante os 3 mesmo se API falhar
- BUG FIX — contexto não encontrado: /clients endpoint trocou listar_entries(tags=["contexto-vivo"]) por buscar_entries(query="contexto:") que usa ilike — funciona independente das tags
- Novo endpoint GET /context?name=X no backend: usa a mesma lógica exata do buscar_contexto_vivo do agente (busca por título exato "contexto: NomeCliente"), retorna situacao_atual, proximo_passo, ultimo_passo, updated_at com fallback de campos (situacao_atual > body, proximo_passo > next_step)
- Next.js route /api/context/route.ts criada (proxy para Railway /context)
- Frontend: após fetch do /clients, enriquece via Promise.all cada cliente sem has_context via /api/context?name=X separado — garante que Gracie Barra e outros mostrem contexto mesmo que /clients não retorne has_context=true

**Jarvis 9 (atual):**
- Backend: endpoints GET /transactions e POST /transactions adicionados em api.py; TransactionBody Pydantic model; entries tipo "transaction" com content.amount, content.transaction_type (receita/despesa), content.category
- Next.js route /api/transactions/route.ts criada (proxy para Railway /transactions)
- Tela de Finanças (FinanceView) construída no index.html: header com saldo total CountUp pt-BR, 3 cards de resumo (receitas/despesas/saldo com animação staggered), gráfico de barras CSS-only últimos 6 meses (finBarGrow via --fh CSS var), lista de transações agrupada por data (Hoje/Ontem/Esta semana/Mais antigas), FAB fixo + modal Nova Transação com toggle receita/despesa e pills de categoria, estado vazio animado
- CountUp atualizado com prop locale para pt-BR (toLocaleString)
- is-finance adicionado ao App className; orb some quando finance ativa; FinanceView adicionado ao render chain do App
- CSS prefixado com fin- (finFadeUp, finSlideIn, finBarGrow, finPop keyframes)
