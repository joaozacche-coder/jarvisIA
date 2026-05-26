-- ─────────────────────────────────────────
-- Rode este arquivo no SQL Editor do Supabase
-- ─────────────────────────────────────────

-- ─────────────────────────────────────────
-- PROJETOS
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS projects (
    id          UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id     TEXT        NOT NULL,
    title       TEXT        NOT NULL,
    description TEXT,
    deadline    DATE,
    status      TEXT        DEFAULT 'ativo',
    progress    INTEGER     DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Adiciona project_id à tabela tasks (projects deve existir antes)
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS project_id UUID REFERENCES projects(id) ON DELETE SET NULL;

-- ─────────────────────────────────────────
-- HÁBITOS
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS habits (
    id          UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id     TEXT        NOT NULL,
    title       TEXT        NOT NULL,
    frequency   TEXT        NOT NULL,  -- ex: 'daily', 'weekly', 'weekdays'
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS habit_checkins (
    id          UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    habit_id    UUID        NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
    user_id     TEXT        NOT NULL,
    checked_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────
-- METAS
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS goals (
    id            UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id       TEXT        NOT NULL,
    title         TEXT        NOT NULL,
    target_value  NUMERIC     NOT NULL,
    current_value NUMERIC     DEFAULT 0,
    deadline      DATE,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);
