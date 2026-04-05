import { sql, asc, eq, ilike, and } from 'drizzle-orm'
import { actors } from 'shared/schema'
import type { SQL } from 'drizzle-orm'

defineRouteMeta({
  openAPI: {
    tags: ['deputies'],
    summary: 'Liste des parlementaires',
    description: 'Retourne la liste paginee des acteurs (deputes + senateurs) avec filtres.',
    parameters: [
      { in: 'query', name: 'chamber', schema: { type: 'string', enum: ['AN', 'Senat'] }, description: 'Filtrer par chambre' },
      { in: 'query', name: 'group', schema: { type: 'string' }, description: 'Filtrer par groupe politique' },
      { in: 'query', name: 'search', schema: { type: 'string' }, description: 'Recherche par nom' },
      { in: 'query', name: 'page', schema: { type: 'integer', default: 1 } },
      { in: 'query', name: 'limit', schema: { type: 'integer', default: 20, maximum: 100 } },
    ],
  },
})

export default defineEventHandler(async (event) => {
  const { page, limit, offset } = getPaginationParams(event)
  const query = getQuery(event)
  const group = query.group as string | undefined
  const searchRaw = query.search as string | undefined
  const chamber = query.chamber as string | undefined

  // Strip SQL wildcard characters from search input before using in ilike
  const search = searchRaw ? searchRaw.replace(/[%_]/g, '') : undefined

  // Build WHERE conditions
  const conditions: SQL[] = []
  if (chamber === 'AN' || chamber === 'Senat') {
    conditions.push(eq(actors.chamber, chamber))
  }
  if (group) {
    conditions.push(eq(actors.group, group))
  }
  if (search) {
    conditions.push(ilike(actors.fullName, `%${search}%`))
  }

  try {
    const rows = await db
      .select({
        id: actors.id,
        officialId: actors.officialId,
        firstName: actors.firstName,
        lastName: actors.lastName,
        fullName: actors.fullName,
        chamber: actors.chamber,
        group: actors.group,
        photoUrl: actors.photoUrl,
        constituency: actors.constituency,
        isActive: actors.isActive,
        createdAt: actors.createdAt,
        updatedAt: actors.updatedAt,
        // Window function: count total rows matching the same WHERE clause
        totalCount: sql<number>`count(*) over()`,
      })
      .from(actors)
      .where(conditions.length > 0 ? and(...conditions) : undefined)
      .orderBy(asc(actors.lastName), asc(actors.firstName))
      .limit(limit)
      .offset(offset)

    const total = Number(rows.at(0)?.totalCount ?? 0)
    const data = rows.map(({ totalCount, ...rest }) => rest)

    return paginatedResponse(data, total, page, limit)
  }
  catch (error) {
    throw createError({ statusCode: 500, message: 'Failed to fetch deputies' })
  }
})
