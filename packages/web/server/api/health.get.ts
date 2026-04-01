import { sql } from 'drizzle-orm'

defineRouteMeta({
  openAPI: {
    tags: ['system'],
    summary: 'Health check',
    description: 'Verifie la connexion a la base de donnees.',
  },
})

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
