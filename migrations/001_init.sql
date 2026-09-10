-- TaskBuddy reference schema (Postgres). App also creates tables on boot.

CREATE TABLE IF NOT EXISTS projects (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    key VARCHAR(64) NOT NULL,
    name VARCHAR(120) NOT NULL,
    kind VARCHAR(16) NOT NULL DEFAULT 'custom',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    UNIQUE (user_id, key)
);

CREATE INDEX IF NOT EXISTS ix_projects_user_active ON projects (user_id, deleted_at);

CREATE TABLE IF NOT EXISTS items (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    project_id BIGINT NOT NULL REFERENCES projects(id),
    type VARCHAR(16) NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    priority VARCHAR(1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_items_user_type_active ON items (user_id, type, deleted_at);
CREATE INDEX IF NOT EXISTS ix_items_user_project_active ON items (user_id, project_id, deleted_at);
