import { pgTable, text, integer, timestamp, boolean, index, primaryKey } from 'drizzle-orm/pg-core'
import { sql } from 'drizzle-orm'

export const deputies = pgTable('deputies', {
  id: integer('id').primaryKey().generatedAlwaysAsIdentity(),
  officialId: text('official_id').notNull().unique(),
  firstName: text('first_name').notNull(),
  lastName: text('last_name').notNull(),
  fullName: text('full_name').notNull(),
  group: text('political_group'),
  photoUrl: text('photo_url'),
  constituency: text('constituency'),
  isActive: boolean('is_active').default(true),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
})

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
  deputyId: integer('deputy_id').references(() => deputies.id),
  speakerName: text('speaker_name').notNull(),
  speakerRole: text('speaker_role'),
  content: text('content').notNull(),
  orderInDebate: integer('order_in_debate').notNull(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
}, (table) => [
  index('idx_interventions_debate').on(table.debateId),
  index('idx_interventions_deputy').on(table.deputyId),
  index('idx_interventions_fts').using(
    'gin',
    sql`to_tsvector('french', ${table.content})`
  ),
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
