import { sql, desc, eq, and, gte, lte } from 'drizzle-orm'
import type { SQL } from 'drizzle-orm'
import { scrutins } from 'shared/schema'

export default defineEventHandler(async (event) => {
  const { page, limit, offset } = getPaginationParams(event)
  const query = getQuery(event)
  const chamber = query.chambre as string | undefined
  const dateFrom = query.dateFrom as string | undefined
  const dateTo = query.dateTo as string | undefined
  const result = query.result as string | undefined

  // Build WHERE conditions
  const conditions: SQL[] = []
  if (chamber === 'AN' || chamber === 'Senat') {
    conditions.push(eq(scrutins.chamber, chamber))
  }
  if (dateFrom) {
    conditions.push(gte(scrutins.date, new Date(dateFrom)))
  }
  if (dateTo) {
    conditions.push(lte(scrutins.date, new Date(dateTo)))
  }
  if (result === 'adopted' || result === 'rejected') {
    conditions.push(eq(scrutins.result, result))
  }

  try {
    const rows = await db
      .select({
        id: scrutins.id,
        officialId: scrutins.officialId,
        title: scrutins.title,
        date: scrutins.date,
        chamber: scrutins.chamber,
        scrutinType: scrutins.scrutinType,
        result: scrutins.result,
        votesFor: scrutins.votesFor,
        votesAgainst: scrutins.votesAgainst,
        votesAbstain: scrutins.votesAbstain,
        sourceUrl: scrutins.sourceUrl,
        // Window function: count total rows matching the same WHERE clause
        totalCount: sql<number>`count(*) over()`,
      })
      .from(scrutins)
      .where(conditions.length > 0 ? and(...conditions) : undefined)
      .orderBy(desc(scrutins.date))
      .limit(limit)
      .offset(offset)

    const total = Number(rows.at(0)?.totalCount ?? 0)
    const data = rows.map(({ totalCount, ...rest }) => rest)

    return paginatedResponse(data, total, page, limit)
  }
  catch (error) {
    throw createError({ statusCode: 500, message: 'Failed to fetch votes' })
  }
})
