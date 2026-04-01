import { eq, desc, inArray, sql } from 'drizzle-orm'
import { actors, interventions, debates, interventionTags, tags, votes } from 'shared/schema'

export default defineEventHandler(async (event) => {
  const rawId = getRouterParam(event, 'id')
  const id = Number(rawId)

  if (!rawId || isNaN(id)) {
    throw createError({ statusCode: 400, message: 'Invalid deputy ID' })
  }

  const { page, limit, offset } = getPaginationParams(event)

  try {
    // Fetch the actor (deputy)
    const actorRows = await db
      .select()
      .from(actors)
      .where(eq(actors.id, id))
      .limit(1)

    if (!actorRows.length) {
      throw createError({ statusCode: 404, message: 'Deputy not found' })
    }

    const deputy = actorRows[0]

    // Fetch interventions with debate info (left join), paginated, ordered by createdAt DESC
    const interventionRows = await db
      .select({
        id: interventions.id,
        debateId: interventions.debateId,
        deputyId: interventions.actorId,
        speakerName: interventions.speakerName,
        speakerRole: interventions.speakerRole,
        content: interventions.content,
        orderInDebate: interventions.orderInDebate,
        createdAt: interventions.createdAt,
        debateTitle: debates.title,
        debateDate: debates.date,
        totalCount: sql<number>`count(*) over()`,
      })
      .from(interventions)
      .leftJoin(debates, eq(interventions.debateId, debates.id))
      .where(eq(interventions.actorId, id))
      .orderBy(desc(interventions.createdAt))
      .limit(limit)
      .offset(offset)

    const totalInterventions = Number(interventionRows.at(0)?.totalCount ?? 0)

    // Batch fetch tags for the returned interventions (avoid N+1)
    const interventionIds = interventionRows.map(i => i.id)
    const tagMap = new Map<number, { id: number; name: string; slug: string }[]>()

    if (interventionIds.length > 0) {
      const tagRows = await db
        .select({
          interventionId: interventionTags.interventionId,
          tagId: tags.id,
          tagName: tags.name,
          tagSlug: tags.slug,
        })
        .from(interventionTags)
        .innerJoin(tags, eq(interventionTags.tagId, tags.id))
        .where(inArray(interventionTags.interventionId, interventionIds))

      for (const row of tagRows) {
        if (!tagMap.has(row.interventionId)) {
          tagMap.set(row.interventionId, [])
        }
        tagMap.get(row.interventionId)!.push({
          id: row.tagId,
          name: row.tagName,
          slug: row.tagSlug,
        })
      }
    }

    // Enrich interventions with debate context and tags
    const enrichedInterventions = interventionRows.map(row => ({
      id: row.id,
      debateId: row.debateId,
      deputyId: row.deputyId,
      speakerName: row.speakerName,
      speakerRole: row.speakerRole,
      content: row.content,
      orderInDebate: row.orderInDebate,
      createdAt: row.createdAt,
      debate: {
        title: row.debateTitle,
        date: row.debateDate,
      },
      tags: tagMap.get(row.id) ?? [],
    }))

    // Compute tag distribution for this deputy across all their interventions
    const tagStatsRows = await db
      .select({
        name: tags.name,
        slug: tags.slug,
        count: sql<number>`count(*)`,
      })
      .from(interventionTags)
      .innerJoin(tags, eq(interventionTags.tagId, tags.id))
      .innerJoin(interventions, eq(interventionTags.interventionId, interventions.id))
      .where(eq(interventions.actorId, id))
      .groupBy(tags.name, tags.slug)
      .orderBy(desc(sql`count(*)`))

    const tagStats = tagStatsRows.map(row => ({
      name: row.name,
      slug: row.slug,
      count: Number(row.count),
    }))

    // Compute vote position breakdown for this actor
    const voteStatsRows = await db
      .select({
        position: votes.position,
        count: sql<number>`count(*)`,
      })
      .from(votes)
      .where(eq(votes.actorId, id))
      .groupBy(votes.position)

    const voteStats = voteStatsRows.map(row => ({
      position: row.position,
      count: Number(row.count),
    }))

    return {
      deputy,
      interventions: paginatedResponse(enrichedInterventions, totalInterventions, page, limit),
      tagStats,
      voteStats,
    }
  }
  catch (error) {
    // Re-throw H3 errors as-is
    if ((error as { statusCode?: number }).statusCode) {
      throw error
    }
    throw createError({ statusCode: 500, message: 'Failed to fetch deputy' })
  }
})
