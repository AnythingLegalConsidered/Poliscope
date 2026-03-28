import { asc } from 'drizzle-orm'
import { debates, deputies } from '../../db/schema'

export default defineSitemapEventHandler(async () => {
  const [debateRows, deputyRows] = await Promise.all([
    db.select({ id: debates.id, date: debates.date }).from(debates).orderBy(asc(debates.id)),
    db.select({ id: deputies.id }).from(deputies).orderBy(asc(deputies.id)),
  ])

  const debateUrls = debateRows.map(d => ({
    loc: `/debates/${d.id}`,
    lastmod: d.date ? new Date(d.date).toISOString().split('T')[0] : undefined,
  }))

  const deputyUrls = deputyRows.map(d => ({
    loc: `/deputies/${d.id}`,
  }))

  return [...debateUrls, ...deputyUrls]
})
