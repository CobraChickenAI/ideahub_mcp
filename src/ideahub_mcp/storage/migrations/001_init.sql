CREATE TABLE actor (
  id            TEXT PRIMARY KEY,
  kind          TEXT NOT NULL CHECK (kind IN ('agent','human')),
  display_name  TEXT NOT NULL,
  first_seen_at TEXT NOT NULL
);

CREATE TABLE idea (
  id            TEXT PRIMARY KEY,
  content       TEXT NOT NULL,
  scope         TEXT NOT NULL,
  actor_id      TEXT NOT NULL REFERENCES actor(id),
  originator_id TEXT REFERENCES actor(id),
  tags          TEXT NOT NULL DEFAULT '[]',
  created_at    TEXT NOT NULL,
  archived_at   TEXT
);
CREATE INDEX idea_scope_created_idx ON idea (scope, created_at DESC);
CREATE INDEX idea_actor_idx         ON idea (actor_id);
CREATE INDEX idea_originator_idx    ON idea (originator_id);

CREATE TABLE idea_note (
  id            TEXT PRIMARY KEY,
  idea_id       TEXT NOT NULL REFERENCES idea(id) ON DELETE CASCADE,
  kind          TEXT,
  content       TEXT NOT NULL,
  actor_id      TEXT NOT NULL REFERENCES actor(id),
  originator_id TEXT REFERENCES actor(id),
  created_at    TEXT NOT NULL
);
CREATE INDEX idea_note_idea_idx ON idea_note (idea_id, created_at DESC);

CREATE TABLE idea_link (
  source_idea_id TEXT NOT NULL REFERENCES idea(id) ON DELETE CASCADE,
  target_idea_id TEXT NOT NULL REFERENCES idea(id) ON DELETE CASCADE,
  kind           TEXT NOT NULL CHECK (kind IN ('related','supersedes','evolved_from','duplicate')),
  created_at     TEXT NOT NULL,
  PRIMARY KEY (source_idea_id, target_idea_id, kind)
);

CREATE VIRTUAL TABLE idea_fts USING fts5(content, content='idea', content_rowid='rowid');

CREATE TRIGGER idea_ai AFTER INSERT ON idea BEGIN
  INSERT INTO idea_fts(rowid, content) VALUES (new.rowid, new.content);
END;
CREATE TRIGGER idea_ad AFTER DELETE ON idea BEGIN
  INSERT INTO idea_fts(idea_fts, rowid, content) VALUES('delete', old.rowid, old.content);
END;
CREATE TRIGGER idea_au AFTER UPDATE OF content ON idea BEGIN
  INSERT INTO idea_fts(idea_fts, rowid, content) VALUES('delete', old.rowid, old.content);
  INSERT INTO idea_fts(rowid, content) VALUES (new.rowid, new.content);
END;
