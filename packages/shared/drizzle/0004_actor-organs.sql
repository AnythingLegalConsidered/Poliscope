CREATE TABLE IF NOT EXISTS actor_organs (
  id INTEGER PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  actor_id INTEGER NOT NULL REFERENCES actors(id) ON DELETE CASCADE,
  organ_id INTEGER NOT NULL REFERENCES organs(id) ON DELETE CASCADE,
  role TEXT,
  start_date TIMESTAMP,
  end_date TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW() NOT NULL,
  CONSTRAINT actor_organs_actor_organ_unique UNIQUE (actor_id, organ_id)
);
CREATE INDEX IF NOT EXISTS idx_actor_organs_actor ON actor_organs(actor_id);
CREATE INDEX IF NOT EXISTS idx_actor_organs_organ ON actor_organs(organ_id);
GRANT ALL ON TABLE actor_organs TO poliscope;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO poliscope;
