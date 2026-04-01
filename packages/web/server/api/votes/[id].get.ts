import { sql, eq, and, asc } from 'drizzle-orm'
import type { SQL } from 'drizzle-orm'
import { scrutins, votes, actors } from 'shared/schema'

defineRouteMeta({
  openAPI: {
    tags: ['votes'],
    summary: 'Detail d\'un scrutin',
    description: 'Retourne les metadonnees du scrutin et la liste paginee des votes par acteur.',
    parameters: [
      { in: 'path', name: 'id', required: true, schema: { type: 'integer' }, description: 'ID du scrutin' },
      { in: 'query', name: 'position', schema: { type: 'string', enum: ['for', 'against', 'abstain', 'absent'] }, description: 'Filtrer par position' },
      { in: 'query', name: 'page', schema: { type: 'integer', default: 1 } },
      { in: 'query', name: 'limit', schema: { type: 'integer', default: 20, maximum: 100 } },
    ],
  },
})

export default defineEventHandler(async (event) => {
  const rawId = getRouterParam(event, 'id')
  const id = Number(rawId)

  if (!rawId || isNaN(id)) {
    throw createError({ statusCode: 400, message: 'Invalid scrutin ID' })
  }

  const { page, limit, offset } = getPaginationParams(event)
  const query = getQuery(event)
  const position = query.position as string | undefined

  try {
    // Fetch the scrutin
    const scrutinRows = await db
      .select()
      .from(scrutins)
      .where(eq(scrutins.id, id))
      .limit(1)

    if (!scrutinRows.length) {
      throw createError({ statusCode: 404, message: 'Scrutin not found' })
    }

    const scrutin = scrutinRows[0]

    // Build vote WHERE conditions
    const voteConditions: SQL[] = [eq(votes.scrutinId, id)]
    const validPositions = ['for', 'against', 'abstain', 'absent']
    if (position && validPositions.includes(position)) {
      voteConditions.push(eq(votes.position, position))
    }

    // Fetch per-actor votes with pagination (mandatory — 1.3M votes total)
    const voteRows = await db
      .select({
        id: votes.id,
        actorId: votes.actorId,
        position: votes.position,
        actorFullName: actors.fullName,
        actorGroup: actors.group,
        actorPhotoUrl: actors.photoUrl,
        // Window function: count total rows matching the same WHERE clause
        totalCount: sql<number>`count(*) over()`,
      })
      .from(votes)
      .leftJoin(actors, eq(votes.actorId, actors.id))
      .where(and(...voteConditions))
      .orderBy(asc(actors.lastName))
      .limit(limit)
      .offset(offset)

    const totalVotes = Number(voteRows.at(0)?.totalCount ?? 0)
    const voteData = voteRows.map(({ totalCount, ...rest }) => rest)

    return {
      scrutin,
      votes: paginatedResponse(voteData, totalVotes, page, limit),
    }
  }
  catch (error) {
    // Re-throw H3 errors as-is
    if ((error as { statusCode?: number }).statusCode) {
      throw error
    }
    throw createError({ statusCode: 500, message: 'Failed to fetch scrutin' })
  }
})
