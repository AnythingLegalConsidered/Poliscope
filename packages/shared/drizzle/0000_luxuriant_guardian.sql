CREATE TABLE "debates" (
	"id" integer PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "debates_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 START WITH 1 CACHE 1),
	"official_id" text NOT NULL,
	"title" text NOT NULL,
	"date" timestamp NOT NULL,
	"legislature" integer NOT NULL,
	"session_type" text,
	"presiding_officer" text,
	"source_url" text,
	"created_at" timestamp DEFAULT now() NOT NULL,
	CONSTRAINT "debates_official_id_unique" UNIQUE("official_id")
);
--> statement-breakpoint
CREATE TABLE "deputies" (
	"id" integer PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "deputies_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 START WITH 1 CACHE 1),
	"official_id" text NOT NULL,
	"first_name" text NOT NULL,
	"last_name" text NOT NULL,
	"full_name" text NOT NULL,
	"political_group" text,
	"photo_url" text,
	"constituency" text,
	"is_active" boolean DEFAULT true,
	"created_at" timestamp DEFAULT now() NOT NULL,
	"updated_at" timestamp DEFAULT now() NOT NULL,
	CONSTRAINT "deputies_official_id_unique" UNIQUE("official_id")
);
--> statement-breakpoint
CREATE TABLE "intervention_tags" (
	"intervention_id" integer NOT NULL,
	"tag_id" integer NOT NULL,
	CONSTRAINT "intervention_tags_intervention_id_tag_id_pk" PRIMARY KEY("intervention_id","tag_id")
);
--> statement-breakpoint
CREATE TABLE "interventions" (
	"id" integer PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "interventions_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 START WITH 1 CACHE 1),
	"debate_id" integer NOT NULL,
	"deputy_id" integer,
	"speaker_name" text NOT NULL,
	"speaker_role" text,
	"content" text NOT NULL,
	"order_in_debate" integer NOT NULL,
	"created_at" timestamp DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "tags" (
	"id" integer PRIMARY KEY GENERATED ALWAYS AS IDENTITY (sequence name "tags_id_seq" INCREMENT BY 1 MINVALUE 1 MAXVALUE 2147483647 START WITH 1 CACHE 1),
	"name" text NOT NULL,
	"slug" text NOT NULL,
	CONSTRAINT "tags_name_unique" UNIQUE("name"),
	CONSTRAINT "tags_slug_unique" UNIQUE("slug")
);
--> statement-breakpoint
ALTER TABLE "intervention_tags" ADD CONSTRAINT "intervention_tags_intervention_id_interventions_id_fk" FOREIGN KEY ("intervention_id") REFERENCES "public"."interventions"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "intervention_tags" ADD CONSTRAINT "intervention_tags_tag_id_tags_id_fk" FOREIGN KEY ("tag_id") REFERENCES "public"."tags"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "interventions" ADD CONSTRAINT "interventions_debate_id_debates_id_fk" FOREIGN KEY ("debate_id") REFERENCES "public"."debates"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "interventions" ADD CONSTRAINT "interventions_deputy_id_deputies_id_fk" FOREIGN KEY ("deputy_id") REFERENCES "public"."deputies"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "idx_intervention_tags_intervention" ON "intervention_tags" USING btree ("intervention_id");--> statement-breakpoint
CREATE INDEX "idx_intervention_tags_tag" ON "intervention_tags" USING btree ("tag_id");--> statement-breakpoint
CREATE INDEX "idx_interventions_debate" ON "interventions" USING btree ("debate_id");--> statement-breakpoint
CREATE INDEX "idx_interventions_deputy" ON "interventions" USING btree ("deputy_id");--> statement-breakpoint
CREATE INDEX "idx_interventions_fts" ON "interventions" USING gin (to_tsvector('french', "content"));