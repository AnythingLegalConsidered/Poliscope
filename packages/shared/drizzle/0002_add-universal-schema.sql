CREATE TABLE "amendments" (
	"id" integer PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "amendments_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 START WITH 1 CACHE 1),
	"official_id" text NOT NULL,
	"title" text,
	"content" text,
	"actor_id" integer,
	"chamber" text NOT NULL,
	"status" text,
	"date" timestamp,
	"legislature_id" integer,
	"source_url" text,
	"created_at" timestamp DEFAULT now() NOT NULL,
	CONSTRAINT "amendments_official_id_unique" UNIQUE("official_id")
);
--> statement-breakpoint
CREATE TABLE "cross_references" (
	"id" integer PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "cross_references_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 START WITH 1 CACHE 1),
	"actor_id" integer NOT NULL,
	"source_type" text NOT NULL,
	"source_id" text NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "legislatures" (
	"id" integer PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "legislatures_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 START WITH 1 CACHE 1),
	"number" integer NOT NULL,
	"start_date" timestamp NOT NULL,
	"end_date" timestamp,
	"chamber" text NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL,
	CONSTRAINT "legislatures_number_unique" UNIQUE("number")
);
--> statement-breakpoint
CREATE TABLE "organs" (
	"id" integer PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "organs_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 START WITH 1 CACHE 1),
	"official_id" text NOT NULL,
	"name" text NOT NULL,
	"short_name" text,
	"organ_type" text NOT NULL,
	"chamber" text NOT NULL,
	"legislature_id" integer,
	"parent_organ_id" integer,
	"start_date" timestamp,
	"end_date" timestamp,
	"created_at" timestamp DEFAULT now() NOT NULL,
	CONSTRAINT "organs_official_id_unique" UNIQUE("official_id")
);
--> statement-breakpoint
CREATE TABLE "questions" (
	"id" integer PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "questions_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 START WITH 1 CACHE 1),
	"official_id" text NOT NULL,
	"question_type" text NOT NULL,
	"title" text NOT NULL,
	"content" text,
	"actor_id" integer,
	"chamber" text NOT NULL,
	"date" timestamp NOT NULL,
	"answer_date" timestamp,
	"answer_content" text,
	"legislature_id" integer,
	"source_url" text,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"search_vector" "tsvector" GENERATED ALWAYS AS (to_tsvector('french', coalesce("questions"."title", '') || ' ' || coalesce("questions"."content", ''))) STORED,
	CONSTRAINT "questions_official_id_unique" UNIQUE("official_id")
);
--> statement-breakpoint
CREATE TABLE "scrutins" (
	"id" integer PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "scrutins_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 START WITH 1 CACHE 1),
	"official_id" text NOT NULL,
	"title" text NOT NULL,
	"date" timestamp NOT NULL,
	"chamber" text NOT NULL,
	"session_id" integer,
	"legislature_id" integer,
	"scrutin_type" text,
	"result" text,
	"votes_for" integer,
	"votes_against" integer,
	"votes_abstain" integer,
	"source_url" text,
	"created_at" timestamp DEFAULT now() NOT NULL,
	CONSTRAINT "scrutins_official_id_unique" UNIQUE("official_id")
);
--> statement-breakpoint
CREATE TABLE "votes" (
	"id" integer PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "votes_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 START WITH 1 CACHE 1),
	"scrutin_id" integer NOT NULL,
	"actor_id" integer NOT NULL,
	"position" text NOT NULL,
	"delegation_actor_id" integer,
	"created_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "debates" ADD COLUMN "chamber" text DEFAULT 'AN';--> statement-breakpoint
ALTER TABLE "amendments" ADD CONSTRAINT "amendments_actor_id_actors_id_fk" FOREIGN KEY ("actor_id") REFERENCES "public"."actors"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "amendments" ADD CONSTRAINT "amendments_legislature_id_legislatures_id_fk" FOREIGN KEY ("legislature_id") REFERENCES "public"."legislatures"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "cross_references" ADD CONSTRAINT "cross_references_actor_id_actors_id_fk" FOREIGN KEY ("actor_id") REFERENCES "public"."actors"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "organs" ADD CONSTRAINT "organs_legislature_id_legislatures_id_fk" FOREIGN KEY ("legislature_id") REFERENCES "public"."legislatures"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "questions" ADD CONSTRAINT "questions_actor_id_actors_id_fk" FOREIGN KEY ("actor_id") REFERENCES "public"."actors"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "questions" ADD CONSTRAINT "questions_legislature_id_legislatures_id_fk" FOREIGN KEY ("legislature_id") REFERENCES "public"."legislatures"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "scrutins" ADD CONSTRAINT "scrutins_session_id_debates_id_fk" FOREIGN KEY ("session_id") REFERENCES "public"."debates"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "scrutins" ADD CONSTRAINT "scrutins_legislature_id_legislatures_id_fk" FOREIGN KEY ("legislature_id") REFERENCES "public"."legislatures"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "votes" ADD CONSTRAINT "votes_scrutin_id_scrutins_id_fk" FOREIGN KEY ("scrutin_id") REFERENCES "public"."scrutins"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "votes" ADD CONSTRAINT "votes_actor_id_actors_id_fk" FOREIGN KEY ("actor_id") REFERENCES "public"."actors"("id") ON DELETE cascade ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "votes" ADD CONSTRAINT "votes_delegation_actor_id_actors_id_fk" FOREIGN KEY ("delegation_actor_id") REFERENCES "public"."actors"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "idx_amendments_actor" ON "amendments" USING btree ("actor_id");--> statement-breakpoint
CREATE INDEX "idx_amendments_chamber" ON "amendments" USING btree ("chamber");--> statement-breakpoint
CREATE INDEX "idx_amendments_status" ON "amendments" USING btree ("status");--> statement-breakpoint
CREATE INDEX "idx_cross_ref_actor" ON "cross_references" USING btree ("actor_id");--> statement-breakpoint
CREATE INDEX "idx_cross_ref_source" ON "cross_references" USING btree ("source_type","source_id");--> statement-breakpoint
CREATE INDEX "idx_organs_type" ON "organs" USING btree ("organ_type");--> statement-breakpoint
CREATE INDEX "idx_organs_chamber" ON "organs" USING btree ("chamber");--> statement-breakpoint
CREATE INDEX "idx_questions_actor" ON "questions" USING btree ("actor_id");--> statement-breakpoint
CREATE INDEX "idx_questions_type" ON "questions" USING btree ("question_type");--> statement-breakpoint
CREATE INDEX "idx_questions_chamber" ON "questions" USING btree ("chamber");--> statement-breakpoint
CREATE INDEX "idx_questions_fts" ON "questions" USING gin ("search_vector");--> statement-breakpoint
CREATE INDEX "idx_scrutins_date" ON "scrutins" USING btree ("date");--> statement-breakpoint
CREATE INDEX "idx_scrutins_chamber" ON "scrutins" USING btree ("chamber");--> statement-breakpoint
CREATE INDEX "idx_scrutins_session" ON "scrutins" USING btree ("session_id");--> statement-breakpoint
CREATE INDEX "idx_votes_scrutin" ON "votes" USING btree ("scrutin_id");--> statement-breakpoint
CREATE INDEX "idx_votes_actor" ON "votes" USING btree ("actor_id");--> statement-breakpoint
CREATE INDEX "idx_votes_position" ON "votes" USING btree ("position");