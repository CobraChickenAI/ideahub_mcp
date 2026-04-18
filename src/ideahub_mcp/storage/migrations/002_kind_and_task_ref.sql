ALTER TABLE idea ADD COLUMN kind TEXT NOT NULL DEFAULT 'idea'
  CHECK (kind IN ('idea','checkpoint'));
ALTER TABLE idea ADD COLUMN task_ref TEXT;

ALTER TABLE idea_note ADD COLUMN task_ref TEXT;
ALTER TABLE idea_link ADD COLUMN task_ref TEXT;

CREATE INDEX idea_kind_idx     ON idea (kind);
CREATE INDEX idea_task_ref_idx ON idea (task_ref) WHERE task_ref IS NOT NULL;
