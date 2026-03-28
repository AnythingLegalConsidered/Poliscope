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
  chamber: text('chamber').default('AN'),  // 'AN' | 'Senat'
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

export const legislatures = pgTable('legislatures', {
  id: integer('id').primaryKey().generatedAlwaysAsIdentity(),
  number: integer('number').notNull().unique(),   // e.g. 17
  startDate: timestamp('start_date').notNull(),
  endDate: timestamp('end_date'),
  chamber: text('chamber').notNull(),             // 'AN' | 'Senat'
  createdAt: timestamp('created_at').defaultNow().notNull(),
})

export const organs = pgTable('organs', {
  id: integer('id').primaryKey().generatedAlwaysAsIdentity(),
  officialId: text('official_id').notNull().unique(),  // e.g. 'PO800490'
  name: text('name').notNull(),
  shortName: text('short_name'),                       // e.g. 'RN', 'LFI-NFP'
  organType: text('organ_type').notNull(),             // 'group' | 'commission' | 'delegation' | 'other'
  chamber: text('chamber').notNull(),                  // 'AN' | 'Senat'
  legislatureId: integer('legislature_id').references(() => legislatures.id),
  parentOrganId: integer('parent_organ_id'),           // self-ref for sub-commissions (no FK to avoid circular — resolved at app level)
  startDate: timestamp('start_date'),
  endDate: timestamp('end_date'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
}, (t) => [
  index('idx_organs_type').on(t.organType),
  index('idx_organs_chamber').on(t.chamber),
])

export const scrutins = pgTable('scrutins', {
  id: integer('id').primaryKey().generatedAlwaysAsIdentity(),
  officialId: text('official_id').notNull().unique(),  // e.g. 'VTANR5L17V4785'
  title: text('title').notNull(),
  date: timestamp('date').notNull(),
  chamber: text('chamber').notNull(),                  // 'AN' | 'Senat'
  sessionId: integer('session_id').references(() => debates.id),  // links to the debate session (nullable)
  legislatureId: integer('legislature_id').references(() => legislatures.id),
  scrutinType: text('scrutin_type'),                   // 'ordinary' | 'solemn' | 'other'
  result: text('result'),                              // 'adopted' | 'rejected'
  votesFor: integer('votes_for'),
  votesAgainst: integer('votes_against'),
  votesAbstain: integer('votes_abstain'),
  sourceUrl: text('source_url'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
}, (t) => [
  index('idx_scrutins_date').on(t.date),
  index('idx_scrutins_chamber').on(t.chamber),
  index('idx_scrutins_session').on(t.sessionId),
])

export const votes = pgTable('votes', {
  id: integer('id').primaryKey().generatedAlwaysAsIdentity(),
  scrutinId: integer('scrutin_id').notNull().references(() => scrutins.id, { onDelete: 'cascade' }),
  actorId: integer('actor_id').notNull().references(() => actors.id, { onDelete: 'cascade' }),
  position: text('position').notNull(),                // 'for' | 'against' | 'abstain' | 'absent'
  delegationActorId: integer('delegation_actor_id').references(() => actors.id),  // if voted by delegation
  createdAt: timestamp('created_at').defaultNow().notNull(),
}, (t) => [
  index('idx_votes_scrutin').on(t.scrutinId),
  index('idx_votes_actor').on(t.actorId),
  index('idx_votes_position').on(t.position),
])

export const questions = pgTable('questions', {
  id: integer('id').primaryKey().generatedAlwaysAsIdentity(),
  officialId: text('official_id').notNull().unique(),
  questionType: text('question_type').notNull(),       // 'QAG' | 'QE' | 'QOSD'
  title: text('title').notNull(),
  content: text('content'),
  actorId: integer('actor_id').references(() => actors.id),
  chamber: text('chamber').notNull(),
  date: timestamp('date').notNull(),
  answerDate: timestamp('answer_date'),
  answerContent: text('answer_content'),
  legislatureId: integer('legislature_id').references(() => legislatures.id),
  sourceUrl: text('source_url'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  searchVector: tsvector('search_vector')
    .generatedAlwaysAs((): SQL =>
      sql`to_tsvector('french', coalesce(${questions.title}, '') || ' ' || coalesce(${questions.content}, ''))`
    ),
}, (t) => [
  index('idx_questions_actor').on(t.actorId),
  index('idx_questions_type').on(t.questionType),
  index('idx_questions_chamber').on(t.chamber),
  index('idx_questions_fts').using('gin', t.searchVector as unknown as SQL),
])

export const amendments = pgTable('amendments', {
  id: integer('id').primaryKey().generatedAlwaysAsIdentity(),
  officialId: text('official_id').notNull().unique(),
  title: text('title'),
  content: text('content'),
  actorId: integer('actor_id').references(() => actors.id),  // first signatory
  chamber: text('chamber').notNull(),
  status: text('status'),                              // 'adopted' | 'rejected' | 'withdrawn' | 'pending'
  date: timestamp('date'),
  legislatureId: integer('legislature_id').references(() => legislatures.id),
  sourceUrl: text('source_url'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
}, (t) => [
  index('idx_amendments_actor').on(t.actorId),
  index('idx_amendments_chamber').on(t.chamber),
  index('idx_amendments_status').on(t.status),
])

export const crossReferences = pgTable('cross_references', {
  id: integer('id').primaryKey().generatedAlwaysAsIdentity(),
  actorId: integer('actor_id').notNull().references(() => actors.id, { onDelete: 'cascade' }),
  sourceType: text('source_type').notNull(),           // 'PA' | 'nosdeputes_slug' | 'dila_href' | 'senat'
  sourceId: text('source_id').notNull(),               // the raw identifier value
  createdAt: timestamp('created_at').defaultNow().notNull(),
}, (t) => [
  index('idx_cross_ref_actor').on(t.actorId),
  index('idx_cross_ref_source').on(t.sourceType, t.sourceId),
])
