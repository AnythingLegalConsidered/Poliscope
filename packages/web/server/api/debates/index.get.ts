import { sql, desc, eq, and } from 'drizzle-orm'
import type { SQL } from 'drizzle-orm'
import { debates } from 'shared/schema'

defineRouteMeta({
  openAPI: {
    tags: ['debates'],
    summary: 'Liste des debats parlementaires',
    description: 'Retourne la liste paginee des seances (AN + Senat) avec filtre chambre optionnel.',
    parameters: [
      { in: 'query', name: 'chamber', schema: { type: 'string', enum: ['AN', 'Senat'] }, description: 'Filtrer par chambre' },
      { in: 'query', name: 'page', schema: { type: 'integer', default: 1 } },
      { in: 'query', name: 'limit', schema: { type: 'integer', default: 20, maximum: 100 } },
    ],
  },
})

export default defineEventHandler(async (event) => {
  const { page, limit, offset } = getPaginationParams(event)
  const query = getQuery(event)
  const chamber = query.chamber as string | undefined

  // Build WHERE conditions
  const conditions: SQL[] = []
  if (chamber === 'AN' || chamber === 'Senat') {
    conditions.push(eq(debates.chamber, chamber))
  }

  try {
    const rows = await db
      .select({
        id: debates.id,
        officialId: debates.officialId,
        title: debates.title,
        date: debates.date,
        legislature: debates.legislature,
        sessionType: debates.sessionType,
        chamber: debates.chamber,
        sourceUrl: debates.sourceUrl,
        createdAt: debates.createdAt,
        // Window function: count total rows in same query
        totalCount: sql<number>`count(*) over()`,
      })
      .from(debates)
      .where(conditions.length > 0 ? and(...conditions) : undefined)
      .orderBy(desc(debates.date))
      .limit(limit)
      .offset(offset)

    const total = Number(rows.at(0)?.totalCount ?? 0)
    const data = rows.map(({ totalCount, ...rest }) => rest)

    return paginatedResponse(data, total, page, limit)
  }
  catch (error) {
    throw createError({ statusCode: 500, message: 'Failed to fetch debates' })
  }
})
