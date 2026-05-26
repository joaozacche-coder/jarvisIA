-- ─────────────────────────────────────────
-- migrations_v3.sql — Arquitetura universal escalável
-- Rode no SQL Editor do Supabase
-- ─────────────────────────────────────────

-- PERFIL DO USUÁRIO
CREATE TABLE IF NOT EXISTS users_profile (
    user_id       TEXT PRIMARY KEY,
    name          TEXT,
    age           INTEGER,
    city          TEXT,
    profession    TEXT,
    timezone      TEXT DEFAULT 'America/Sao_Paulo',
    language      TEXT DEFAULT 'pt-BR',
    content       JSONB DEFAULT '{}',
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ENTRIES (coração do sistema)
CREATE TABLE IF NOT EXISTS entries (
    id          UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id     TEXT        NOT NULL REFERENCES users_profile(user_id),
    type        TEXT        NOT NULL,
    title       TEXT        NOT NULL,
    content     JSONB       DEFAULT '{}',
    status      TEXT        DEFAULT 'active',
    priority    INTEGER     DEFAULT 0,
    date        TIMESTAMPTZ,
    due_date    TIMESTAMPTZ,
    tags        TEXT[]      DEFAULT '{}',
    parent_id   UUID        REFERENCES entries(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- RELATIONS
CREATE TABLE IF NOT EXISTS relations (
    id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id       TEXT NOT NULL REFERENCES users_profile(user_id),
    entry_a       UUID REFERENCES entries(id) ON DELETE CASCADE,
    entry_b       UUID REFERENCES entries(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- FILES
CREATE TABLE IF NOT EXISTS files (
    id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users_profile(user_id),
    entry_id   UUID REFERENCES entries(id) ON DELETE CASCADE,
    url        TEXT NOT NULL,
    type       TEXT,
    name       TEXT,
    size       INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- REMINDERS (substitui a tabela antiga)
CREATE TABLE IF NOT EXISTS reminders (
    id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users_profile(user_id),
    entry_id   UUID REFERENCES entries(id) ON DELETE CASCADE,
    remind_at  TIMESTAMPTZ NOT NULL,
    sent       BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- SESSIONS (histórico de conversas para analytics)
CREATE TABLE IF NOT EXISTS sessions (
    id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users_profile(user_id),
    channel    TEXT DEFAULT 'chat',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at   TIMESTAMPTZ,
    messages   INTEGER DEFAULT 0
);

-- ─────────────────────────────────────────
-- ÍNDICES para performance com 10k+ usuários
-- ─────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_entries_user_type
    ON entries(user_id, type);
CREATE INDEX IF NOT EXISTS idx_entries_user_status
    ON entries(user_id, status);
CREATE INDEX IF NOT EXISTS idx_entries_due_date
    ON entries(user_id, due_date) WHERE due_date IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_entries_tags
    ON entries USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_entries_content
    ON entries USING GIN(content);
CREATE INDEX IF NOT EXISTS idx_entries_parent
    ON entries(parent_id) WHERE parent_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_reminders_pending
    ON reminders(remind_at) WHERE sent = FALSE;
CREATE INDEX IF NOT EXISTS idx_relations_entry_a
    ON relations(entry_a);
CREATE INDEX IF NOT EXISTS idx_relations_entry_b
    ON relations(entry_b);

-- ─────────────────────────────────────────
-- RLS (cada usuário vê só os seus dados)
-- ─────────────────────────────────────────
ALTER TABLE users_profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE entries       ENABLE ROW LEVEL SECURITY;
ALTER TABLE relations     ENABLE ROW LEVEL SECURITY;
ALTER TABLE files         ENABLE ROW LEVEL SECURITY;
ALTER TABLE reminders     ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions      ENABLE ROW LEVEL SECURITY;
