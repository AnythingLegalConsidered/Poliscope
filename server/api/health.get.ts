import { sql } from 'drizzle-orm'

export default defineEventHandler(async () => {
  try {
    await db.execute(sql`SELECT 1`)
    return { status: 'ok', db: 'connected', timestamp: new Date().toISOString() }
  } catch (error) {
    throw createError({
      statusCode: 503,
      message: 'Database connection failed',
    })
  }
})
