import { eq, asc, inArray } from 'drizzle-orm'
import { debates, interventions, deputies, interventionTags, tags } from '../../db/schema'

export default defineEventHandler(async (event) => {
  const rawId = getRouterParam(event, 'id')
  const id = Number(rawId)

  if (!rawId || isNaN(id)) {
    throw createError({ statusCode: 400, message: 'Invalid debate ID' })
  }

  try {
    // Fetch the debate
    const debateRows = await db
      .select()
      .from(debates)
      .where(eq(debates.id, id))
      .limit(1)

    if (!debateRows.length) {
      throw createError({ statusCode: 404, message: 'Debate not found' })
    }

    const debate = debateRows[0]

    // Fetch interventions with deputy info (left join)
    const interventionRows = await db
      .select({
        id: interventions.id,
        debateId: interventions.debateId,
        deputyId: interventions.deputyId,
        speakerName: interventions.speakerName,
        speakerRole: interventions.speakerRole,
        content: interventions.content,
        orderInDebate: interventions.orderInDebate,
        createdAt: interventions.createdAt,
        deputyFullName: deputies.fullName,
        deputyGroup: deputies.group,
        deputyPhotoUrl: deputies.photoUrl,
      })
      .from(interventions)
      .leftJoin(deputies, eq(interventions.deputyId, deputies.id))
      .where(eq(interventions.debateId, id))
      .orderBy(asc(interventions.orderInDebate))

    // Batch fetch tags for all interventions (avoid N+1)
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

    // Attach tags to each intervention
    const enrichedInterventions = interventionRows.map(row => ({
      id: row.id,
      debateId: row.debateId,
      deputyId: row.deputyId,
      speakerName: row.speakerName,
      speakerRole: row.speakerRole,
      content: row.content,
      orderInDebate: row.orderInDebate,
      createdAt: row.createdAt,
      deputy: row.deputyId
        ? {
            fullName: row.deputyFullName,
            group: row.deputyGroup,
            photoUrl: row.deputyPhotoUrl,
          }
        : null,
      tags: tagMap.get(row.id) ?? [],
    }))

    return {
      debate,
      interventions: enrichedInterventions,
    }
  }
  catch (error) {
    // Re-throw H3 errors as-is
    if ((error as { statusCode?: number }).statusCode) {
      throw error
    }
    throw createError({ statusCode: 500, message: 'Failed to fetch debate' })
  }
})
