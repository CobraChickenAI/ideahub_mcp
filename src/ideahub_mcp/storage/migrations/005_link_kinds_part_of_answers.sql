-- 005: allow the link kinds part_of and answers.
--   part_of: from the part to the whole.
--   answers: from the answer to the question.
--
-- SQLite cannot change a CHECK constraint in place, so idea_link is rebuilt:
-- create a new table, copy every row (rowid included), drop the old table,
-- rename the new one. Columns, primary key and ON DELETE CASCADE are the same
-- as before; only the CHECK list grows. idea_link has no indexes or triggers
-- of its own besides the primary key.
--
-- Safety: everything runs in one transaction, so a failure leaves the old
-- table as it was. Foreign keys stay on. No table references idea_link, so
-- dropping it cannot cascade into anything else, and every copied row is
-- checked against idea(id). The leading DROP makes a rerun safe if a previous
-- attempt stopped after COMMIT but before schema_version was written.
BEGIN;

DROP TABLE IF EXISTS idea_link_new;

CREATE TABLE idea_link_new (
  source_idea_id TEXT NOT NULL REFERENCES idea(id) ON DELETE CASCADE,
  target_idea_id TEXT NOT NULL REFERENCES idea(id) ON DELETE CASCADE,
  kind           TEXT NOT NULL CHECK (kind IN (
                   'related','supersedes','evolved_from','duplicate','part_of','answers')),
  created_at     TEXT NOT NULL,
  task_ref       TEXT,
  PRIMARY KEY (source_idea_id, target_idea_id, kind)
);

INSERT INTO idea_link_new (rowid, source_idea_id, target_idea_id, kind, created_at, task_ref)
  SELECT rowid, source_idea_id, target_idea_id, kind, created_at, task_ref
  FROM idea_link
  ORDER BY rowid;

DROP TABLE idea_link;

ALTER TABLE idea_link_new RENAME TO idea_link;

COMMIT;
