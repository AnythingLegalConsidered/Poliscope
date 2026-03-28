import { sql, asc, eq, ilike, and } from 'drizzle-orm'
import { deputies } from '../../db/schema'
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
    conditions.push(eq(deputies.group, group))
  }
  if (search) {
    conditions.push(ilike(deputies.fullName, `%${search}%`))
  }

  try {
    const rows = await db
      .select({
        id: deputies.id,
        officialId: deputies.officialId,
        firstName: deputies.firstName,
        lastName: deputies.lastName,
        fullName: deputies.fullName,
        group: deputies.group,
        photoUrl: deputies.photoUrl,
        constituency: deputies.constituency,
        isActive: deputies.isActive,
        createdAt: deputies.createdAt,
        updatedAt: deputies.updatedAt,
        // Window function: count total rows matching the same WHERE clause
        totalCount: sql<number>`count(*) over()`,
      })
      .from(deputies)
      .where(conditions.length > 0 ? and(...conditions) : undefined)
      .orderBy(asc(deputies.lastName), asc(deputies.firstName))
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
