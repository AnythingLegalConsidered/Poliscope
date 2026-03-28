import { pgTable, text, integer, timestamp, boolean, index, primaryKey, customType } from 'drizzle-orm/pg-core'
import { SQL, sql } from 'drizzle-orm'

// Custom tsvector type for stored FTS columns
const tsvector = customType<{ data: string }>({
  dataType() { return 'tsvector' },
})

export const actors = pgTable('actors', {
  id: integer('id').primaryKey().generatedAlwaysAsIdentity(),
  officialId: text('official_id').notNull().unique(),
  firstName: text('first_name').notNull(),
  lastName: text('last_name').notNull(),
  fullName: text('full_name').notNull(),
  group: text('political_group'),
  photoUrl: text('photo_url'),
  constituency: text('constituency'),
  isActive: boolean('is_active').default(true),
  actorType: text('actor_type').notNull().default('deputy'),
  chamber: text('chamber'),
  legislature: integer('legislature'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
  searchVector: tsvector('search_vector').generatedAlwaysAs((): SQL => sql`to_tsvector('french', coalesce(${actors.fullName}, ''))`),
}, (table) => [
  index('idx_actors_fts').using('gin', table.searchVector as unknown as SQL),
  index('idx_actors_type').on(table.actorType),
  index('idx_actors_active').on(table.isActive),
])

export const debates = pgTable('debates', {
  id: integer('id').primaryKey().generatedAlwaysAsIdentity(),
  officialId: text('official_id').notNull().unique(),
  title: text('title').notNull(),
  date: timestamp('date').notNull(),
  legislature: integer('legislature').notNull(),
  sessionType: text('session_type'),
  presidingOfficer: text('presiding_officer'),
  sourceUrl: text('source_url'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
})

export const interventions = pgTable('interventions', {
  id: integer('id').primaryKey().generatedAlwaysAsIdentity(),
  debateId: integer('debate_id').notNull().references(() => debates.id),
  actorId: integer('actor_id').references(() => actors.id),
  speakerName: text('speaker_name').notNull(),
  speakerRole: text('speaker_role'),
  content: text('content').notNull(),
  orderInDebate: integer('order_in_debate').notNull(),
  chamber: text('chamber').default('AN'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  searchVector: tsvector('search_vector').generatedAlwaysAs((): SQL => sql`to_tsvector('french', ${interventions.content})`),
}, (table) => [
  index('idx_interventions_debate').on(table.debateId),
  index('idx_interventions_actor').on(table.actorId),
  index('idx_interventions_fts').using('gin', table.searchVector as unknown as SQL),
])

export const tags = pgTable('tags', {
  id: integer('id').primaryKey().generatedAlwaysAsIdentity(),
  name: text('name').notNull().unique(),
  slug: text('slug').notNull().unique(),
})

export const interventionTags = pgTable('intervention_tags', {
  interventionId: integer('intervention_id').notNull().references(() => interventions.id),
  tagId: integer('tag_id').notNull().references(() => tags.id),
}, (table) => [
  primaryKey({ columns: [table.interventionId, table.tagId] }),
  index('idx_intervention_tags_intervention').on(table.interventionId),
  index('idx_intervention_tags_tag').on(table.tagId),
])
