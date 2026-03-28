import type { InferSelectModel, InferInsertModel } from 'drizzle-orm'
import {
  actors, debates, interventions, tags, interventionTags,
  legislatures, organs, scrutins, votes, questions, amendments, crossReferences,
} from './schema'

export type Actor = InferSelectModel<typeof actors>
export type NewActor = InferInsertModel<typeof actors>
export type Debate = InferSelectModel<typeof debates>
export type NewDebate = InferInsertModel<typeof debates>
export type Intervention = InferSelectModel<typeof interventions>
export type NewIntervention = InferInsertModel<typeof interventions>
export type Tag = InferSelectModel<typeof tags>
export type InterventionTag = InferSelectModel<typeof interventionTags>
export type Legislature = InferSelectModel<typeof legislatures>
export type Organ = InferSelectModel<typeof organs>
export type Scrutin = InferSelectModel<typeof scrutins>
export type Vote = InferSelectModel<typeof votes>
export type Question = InferSelectModel<typeof questions>
export type Amendment = InferSelectModel<typeof amendments>
export type CrossReference = InferSelectModel<typeof crossReferences>
