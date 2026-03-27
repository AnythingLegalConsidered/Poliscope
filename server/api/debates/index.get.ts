import { sql, desc } from 'drizzle-orm'
import { debates } from '../../db/schema'

export default defineEventHandler(async (event) => {
  const { page, limit, offset } = getPaginationParams(event)

  try {
    const rows = await db
      .select({
        id: debates.id,
        officialId: debates.officialId,
        title: debates.title,
        date: debates.date,
        legislature: debates.legislature,
        sessionType: debates.sessionType,
        sourceUrl: debates.sourceUrl,
        createdAt: debates.createdAt,
        // Window function: count total rows in same query
        totalCount: sql<number>`count(*) over()`,
      })
      .from(debates)
      .orderBy(desc(debates.date))
      .limit(limit)
      .offset(offset)

    const total = rows.length > 0 ? Number(rows[0].totalCount) : 0
    const data = rows.map(({ totalCount, ...rest }) => rest)

    return paginatedResponse(data, total, page, limit)
  }
  catch (error) {
    throw createError({ statusCode: 500, message: 'Failed to fetch debates' })
  }
})
