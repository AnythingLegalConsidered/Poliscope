import { asc } from 'drizzle-orm'
import { debates, actors } from 'shared/schema'

export default defineSitemapEventHandler(async () => {
  const [debateRows, actorRows] = await Promise.all([
    db.select({ id: debates.id, date: debates.date }).from(debates).orderBy(asc(debates.id)),
    db.select({ id: actors.id }).from(actors).orderBy(asc(actors.id)),
  ])

  const debateUrls = debateRows.map(d => ({
    loc: `/debates/${d.id}`,
    lastmod: d.date ? new Date(d.date).toISOString().split('T')[0] : undefined,
  }))

  const deputyUrls = actorRows.map(d => ({
    loc: `/deputies/${d.id}`,
  }))

  return [...debateUrls, ...deputyUrls]
})
