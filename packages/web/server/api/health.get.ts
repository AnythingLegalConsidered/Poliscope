import { sql, eq } from 'drizzle-orm'
import { systemMetadata } from 'shared/schema'

defineRouteMeta({
  openAPI: {
    tags: ['system'],
    summary: 'Health check',
    description: 'Verifie la connexion a la base de donnees. Retourne also last_refresh (horodatage du dernier rafraichissement des donnees).',
  },
})

export default defineEventHandler(async () => {
  try {
    await db.execute(sql`SELECT 1`)
    const meta = await db.select().from(systemMetadata).where(eq(systemMetadata.key, 'last_refresh'))
    return {
      status: 'ok',
      db: 'connected',
      last_refresh: meta[0]?.value ?? null,
      timestamp: new Date().toISOString(),
    }
  } catch (error) {
    throw createError({
      statusCode: 503,
      message: 'Database connection failed',
    })
  }
})
