import { asc } from 'drizzle-orm'
import { debates, actors, scrutins } from 'shared/schema'

export default defineSitemapEventHandler(async () => {
  const [debateRows, actorRows, scrutinRows] = await Promise.all([
    db.select({ id: debates.id, date: debates.date }).from(debates).orderBy(asc(debates.id)),
    db.select({ id: actors.id }).from(actors).orderBy(asc(actors.id)),
    db.select({ id: scrutins.id, date: scrutins.date }).from(scrutins).orderBy(asc(scrutins.id)),
  ])

  const debateUrls = debateRows.map(d => ({
    loc: `/debates/${d.id}`,
    lastmod: d.date ? new Date(d.date).toISOString().split('T')[0] : undefined,
  }))

  const deputyUrls = actorRows.map(d => ({
    loc: `/deputies/${d.id}`,
  }))

  const scrutinUrls = scrutinRows.map(s => ({
    loc: `/votes/${s.id}`,
    lastmod: s.date ? new Date(s.date).toISOString().split('T')[0] : undefined,
  }))

  return [...debateUrls, ...deputyUrls, ...scrutinUrls]
})
