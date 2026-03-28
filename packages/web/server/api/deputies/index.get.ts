import { sql, asc, eq, ilike, and } from 'drizzle-orm'
import { actors } from 'shared/schema'
import type { SQL } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  const { page, limit, offset } = getPaginationParams(event)
  const query = getQuery(event)
  const group = query.group as string | undefined
  const searchRaw = query.search as string | undefined

  // Strip SQL wildcard characters from search input before using in ilike
  const search = searchRaw ? searchRaw.replace(/[%_]/g, '') : undefined

  // Build WHERE conditions
  const conditions: SQL[] = []
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
