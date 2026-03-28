import { sql } from 'drizzle-orm'

export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const q = (query.q as string | undefined)?.trim()

  if (!q) {
    throw createError({ statusCode: 400, message: 'Missing required query parameter: q' })
  }

  const deputyIdRaw = query.deputyId as string | undefined
  const debateIdRaw = query.debateId as string | undefined
  const tag = (query.tag as string | undefined)?.trim() || null

  const deputyId = deputyIdRaw ? Number(deputyIdRaw) : null
  const debateId = debateIdRaw ? Number(debateIdRaw) : null

  if (deputyIdRaw && (isNaN(deputyId!) || deputyId! <= 0)) {
    throw createError({ statusCode: 400, message: 'Invalid deputyId' })
  }
  if (debateIdRaw && (isNaN(debateId!) || debateId! <= 0)) {
    throw createError({ statusCode: 400, message: 'Invalid debateId' })
  }

  const { page, limit, offset } = getPaginationParams(event)

  try {
    // Build optional filter clauses
    const actorFilter = deputyId !== null
      ? sql` AND i.actor_id = ${deputyId}`
      : sql``

    const debateFilter = debateId !== null
      ? sql` AND i.debate_id = ${debateId}`
      : sql``

    const tagFilter = tag !== null
      ? sql` AND EXISTS (
          SELECT 1
          FROM intervention_tags it
          JOIN tags t ON it.tag_id = t.id
          WHERE it.intervention_id = i.id
            AND t.slug = ${tag}
        )`
      : sql``

    const rows = await db.execute(sql`
      SELECT
        i.id,
        i.speaker_name AS "speakerName",
        i.speaker_role AS "speakerRole",
        i.order_in_debate AS "orderInDebate",
        ts_rank(
          to_tsvector('french', i.content),
          websearch_to_tsquery('french', ${q})
        ) AS rank,
        ts_headline(
          'french',
          i.content,
          websearch_to_tsquery('french', ${q}),
          'StartSel=<mark>, StopSel=</mark>, MaxWords=35, MinWords=15, MaxFragments=2, FragmentDelimiter= ... '
        ) AS highlight,
        d.id AS "debateId",
        d.title AS "debateTitle",
        d.date AS "debateDate",
        d.session_type AS "sessionType",
        dep.id AS "deputyId",
        dep.full_name AS "deputyName",
        dep.political_group AS "deputyGroup",
        dep.photo_url AS "deputyPhoto",
        count(*) OVER() AS total_count,
        (
          SELECT COALESCE(json_agg(json_build_object('name', t.name, 'slug', t.slug)), '[]'::json)
          FROM intervention_tags it2
          JOIN tags t ON it2.tag_id = t.id
          WHERE it2.intervention_id = i.id
        ) AS tags
      FROM interventions i
      LEFT JOIN debates d ON i.debate_id = d.id
      LEFT JOIN actors dep ON i.actor_id = dep.id
      WHERE to_tsvector('french', i.content) @@ websearch_to_tsquery('french', ${q})
      ${actorFilter}
      ${debateFilter}
      ${tagFilter}
      ORDER BY rank DESC, i.id DESC
      LIMIT ${limit} OFFSET ${offset}
    `)

    const results = rows as unknown as Array<{
      id: number
      speakerName: string
      speakerRole: string | null
      orderInDebate: number
      rank: number
      highlight: string
      debateId: number
      debateTitle: string
      debateDate: string
      sessionType: string | null
      deputyId: number | null
      deputyName: string | null
      deputyGroup: string | null
      deputyPhoto: string | null
      total_count: string
      tags: Array<{ name: string, slug: string }> | string
    }>

    const total = Number(results.at(0)?.total_count ?? 0)

    const data = results.map(row => ({
      id: row.id,
      speakerName: row.speakerName,
      speakerRole: row.speakerRole,
      orderInDebate: row.orderInDebate,
      rank: Number(row.rank),
      highlight: row.highlight.replace(/\ufffd/g, ''),
      debate: {
        id: row.debateId,
        title: row.debateTitle,
        date: row.debateDate,
        sessionType: row.sessionType,
      },
      deputy: row.deputyId ? {
        id: row.deputyId,
        fullName: row.deputyName,
        group: row.deputyGroup,
        photoUrl: row.deputyPhoto,
      } : null,
      tags: typeof row.tags === 'string' ? JSON.parse(row.tags) : (row.tags ?? []),
    }))

    return paginatedResponse(data, total, page, limit)
  }
  catch (error) {
    if ((error as { statusCode?: number }).statusCode) {
      throw error
    }
    throw createError({ statusCode: 500, message: 'Failed to perform search' })
  }
})
