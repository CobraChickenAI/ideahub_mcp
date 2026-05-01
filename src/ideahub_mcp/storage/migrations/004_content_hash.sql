ALTER TABLE idea ADD COLUMN content_hash TEXT;

-- Partial index: dedup lookup is only meaningful for live (non-archived)
-- rows. Archiving an idea must not block a fresh capture of similar
-- content, and the partial index keeps lookups cheap as the archived
-- corpus grows.
CREATE INDEX idea_scope_hash_idx
  ON idea (scope, content_hash) WHERE archived_at IS NULL;
