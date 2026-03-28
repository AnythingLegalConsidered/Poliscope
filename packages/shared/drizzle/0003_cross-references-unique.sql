ALTER TABLE cross_references
  ADD CONSTRAINT cross_references_actor_source_unique
  UNIQUE (actor_id, source_type, source_id);
