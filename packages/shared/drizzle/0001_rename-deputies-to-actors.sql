-- Rename table
ALTER TABLE "deputies" RENAME TO "actors";

-- Rename the sequence (GENERATED ALWAYS AS IDENTITY uses a sequence)
ALTER SEQUENCE "deputies_id_seq" RENAME TO "actors_id_seq";

-- Rename the unique constraint
ALTER TABLE "actors" RENAME CONSTRAINT "deputies_official_id_unique" TO "actors_official_id_unique";

-- Rename the FK constraint on interventions
ALTER TABLE "interventions" RENAME CONSTRAINT "interventions_deputy_id_deputies_id_fk"
  TO "interventions_actor_id_actors_id_fk";

-- Rename the FK column on interventions
ALTER TABLE "interventions" RENAME COLUMN "deputy_id" TO "actor_id";

-- Rename the index on interventions (deputy -> actor)
ALTER INDEX "idx_interventions_deputy" RENAME TO "idx_interventions_actor";

-- Add new columns to actors
ALTER TABLE "actors" ADD COLUMN "actor_type" text NOT NULL DEFAULT 'deputy';
ALTER TABLE "actors" ADD COLUMN "chamber" text;
ALTER TABLE "actors" ADD COLUMN "legislature" integer;

-- Add stored generated tsvector column to actors
ALTER TABLE "actors" ADD COLUMN "search_vector" tsvector
  GENERATED ALWAYS AS (to_tsvector('french', coalesce("full_name", ''))) STORED;

-- Create GIN index on actors search_vector
CREATE INDEX "idx_actors_fts" ON "actors" USING gin ("search_vector");

-- Create indexes on new actor columns
CREATE INDEX "idx_actors_type" ON "actors" USING btree ("actor_type");
CREATE INDEX "idx_actors_active" ON "actors" USING btree ("is_active");

-- Add stored generated tsvector column to interventions
ALTER TABLE "interventions" ADD COLUMN "search_vector" tsvector
  GENERATED ALWAYS AS (to_tsvector('french', "content")) STORED;

-- Create GIN index on interventions search_vector (stored version)
CREATE INDEX "idx_interventions_fts_stored" ON "interventions" USING gin ("search_vector");

-- Drop old functional GIN index (replaced by stored column index above)
DROP INDEX IF EXISTS "idx_interventions_fts";

-- Add chamber column to interventions
ALTER TABLE "interventions" ADD COLUMN "chamber" text DEFAULT 'AN';