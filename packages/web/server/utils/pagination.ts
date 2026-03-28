import type { H3Event } from 'h3'

/**
 * Extracts pagination parameters from an H3 event's query string.
 * Defaults: page=1, limit=20. Max limit: 100.
 */
export function getPaginationParams(event: H3Event): { page: number; limit: number; offset: number } {
  const query = getQuery(event)
  const page = Math.max(1, parseInt((query.page as string) || '1', 10) || 1)
  const limit = Math.min(100, Math.max(1, parseInt((query.limit as string) || '20', 10) || 20))
  const offset = (page - 1) * limit
  return { page, limit, offset }
}

/**
 * Wraps data in a standard paginated response shape.
 */
export function paginatedResponse<T>(
  data: T[],
  total: number,
  page: number,
  limit: number,
) {
  return {
    data,
    pagination: {
      page,
      limit,
      total,
      totalPages: Math.ceil(total / limit),
    },
  }
}
