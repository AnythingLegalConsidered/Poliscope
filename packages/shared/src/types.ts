import type { InferSelectModel, InferInsertModel } from 'drizzle-orm'
import { actors, debates, interventions, tags, interventionTags } from './schema'

export type Actor = InferSelectModel<typeof actors>
export type NewActor = InferInsertModel<typeof actors>
export type Debate = InferSelectModel<typeof debates>
export type NewDebate = InferInsertModel<typeof debates>
export type Intervention = InferSelectModel<typeof interventions>
export type NewIntervention = InferInsertModel<typeof interventions>
export type Tag = InferSelectModel<typeof tags>
export type InterventionTag = InferSelectModel<typeof interventionTags>
