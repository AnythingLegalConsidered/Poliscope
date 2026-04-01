import { sql, inArray } from 'drizzle-orm'
import { interventionTags, tags } from 'shared/schema'
import { eq } from 'drizzle-orm'

defineRouteMeta({
  openAPI: {
    tags: ['search'],
    summary: 'Recherche full-text cross-type',
    description: 'Recherche dans les interventions et les scrutins. Retourne des resultats melanges avec type discriminant.',
    parameters: [
      { in: 'query', name: 'q', required: true, schema: { type: 'string' }, description: 'Terme de recherche' },
      { in: 'query', name: 'type', schema: { type: 'string', enum: ['intervention', 'scrutin'] }, description: 'Filtrer par type de resultat' },
      { in: 'query', name: 'chamber', schema: { type: 'string', enum: ['AN', 'Senat'] }, description: 'Filtrer par chambre' },
      { in: 'query', name: 'deputyId', schema: { type: 'integer' }, description: 'Filtrer par acteur (interventions uniquement)' },
      { in: 'query', name: 'debateId', schema: { type: 'integer' }, description: 'Filtrer par debat (interventions uniquement)' },
      { in: 'query', name: 'tag', schema: { type: 'string' }, description: 'Filtrer par tag (interventions uniquement)' },
      { in: 'query', name: 'page', schema: { type: 'integer', default: 1 } },
      { in: 'query', name: 'limit', schema: { type: 'integer', default: 20, maximum: 100 } },
    ],
  },
})

export default defineEventHandler(async (event) => {
  const query = getQuery(event)
  const q = (query.q as string | undefined)?.trim()

  if (!q) {
    throw createError({ statusCode: 400, message: 'Missing required query parameter: q' })
  }

  const deputyIdRaw = query.deputyId as string | undefined
  const debateIdRaw = query.debateId as string | undefined
  const tag = (query.tag as string | undefined)?.trim() || null
  const typeFilter = query.type as string | undefined
  const chamber = (query.chamber as string | undefined)?.trim() || null

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
    // Build optional filter clauses for interventions branch
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

    // Chamber filter for each branch (applied per-branch since SQL fragments differ)
    const interventionChamberFilter = (chamber === 'AN' || chamber === 'Senat')
      ? sql` AND d.chamber = ${chamber}`
      : sql``

    const scrutinChamberFilter = (chamber === 'AN' || chamber === 'Senat')
      ? sql` AND s.chamber = ${chamber}`
      : sql``

    // Determine which branches to include based on ?type filter
    const includeInterventions = !typeFilter || typeFilter === 'intervention'
    const includeScrutins = !typeFilter || typeFilter === 'scrutin'

    // Build the UNION ALL query — wrapping in subquery to allow window function on combined result
    // Strategy: build each branch as a fragment, combine only the needed branches
    const interventionBranch = sql`
      SELECT
        'intervention' AS type,
        i.id,
        ts_rank(i.search_vector, websearch_to_tsquery('french', ${q})) AS rank,
        ts_headline(
          'french',
          i.content,
          websearch_to_tsquery('french', ${q}),
          'StartSel=<mark>, StopSel=</mark>, MaxWords=35, MinWords=15, MaxFragments=2, FragmentDelimiter= ... '
        ) AS highlight,
        i.speaker_name AS speaker_name,
        d.id AS context_id,
        d.title AS context_title,
        d.date AS context_date,
        dep.id AS actor_id,
        dep.full_name AS actor_name,
        dep.political_group AS actor_group,
        dep.photo_url AS actor_photo,
        NULL::text AS result,
        NULL::integer AS votes_for,
        NULL::integer AS votes_against,
        NULL::integer AS votes_abstain,
        d.chamber AS chamber,
        i.speaker_role AS speaker_role,
        i.order_in_debate AS order_in_debate,
        d.session_type AS session_type
      FROM interventions i
      LEFT JOIN debates d ON i.debate_id = d.id
      LEFT JOIN actors dep ON i.actor_id = dep.id
      WHERE i.search_vector @@ websearch_to_tsquery('french', ${q})
      ${actorFilter}
      ${debateFilter}
      ${tagFilter}
      ${interventionChamberFilter}
    `

    const scrutinBranch = sql`
      SELECT
        'scrutin' AS type,
        s.id,
        ts_rank(to_tsvector('french', s.title), websearch_to_tsquery('french', ${q})) AS rank,
        ts_headline(
          'french',
          s.title,
          websearch_to_tsquery('french', ${q}),
          'StartSel=<mark>, StopSel=</mark>, MaxWords=35, MinWords=15, MaxFragments=1'
        ) AS highlight,
        NULL AS speaker_name,
        s.id AS context_id,
        s.title AS context_title,
        s.date AS context_date,
        NULL::integer AS actor_id,
        NULL AS actor_name,
        NULL AS actor_group,
        NULL AS actor_photo,
        s.result AS result,
        s.votes_for AS votes_for,
        s.votes_against AS votes_against,
        s.votes_abstain AS votes_abstain,
        s.chamber AS chamber,
        NULL AS speaker_role,
        NULL::integer AS order_in_debate,
        NULL AS session_type
      FROM scrutins s
      WHERE to_tsvector('french', s.title) @@ websearch_to_tsquery('french', ${q})
      ${scrutinChamberFilter}
    `

    // Assemble union based on which types are requested
    let unionSql: ReturnType<typeof sql>
    if (includeInterventions && includeScrutins) {
      unionSql = sql`${interventionBranch} UNION ALL ${scrutinBranch}`
    }
    else if (includeInterventions) {
      unionSql = interventionBranch
    }
    else {
      unionSql = scrutinBranch
    }

    const rows = await db.execute(sql`
      SELECT *, count(*) OVER() AS total_count
      FROM (${unionSql}) sub
      ORDER BY rank DESC, id DESC
      LIMIT ${limit} OFFSET ${offset}
    `)

    type RawRow = {
      type: 'intervention' | 'scrutin'
      id: number
      rank: string
      highlight: string
      speaker_name: string | null
      context_id: number
      context_title: string
      context_date: string
      actor_id: number | null
      actor_name: string | null
      actor_group: string | null
      actor_photo: string | null
      result: string | null
      votes_for: number | null
      votes_against: number | null
      votes_abstain: number | null
      chamber: string | null
      speaker_role: string | null
      order_in_debate: number | null
      session_type: string | null
      total_count: string
    }

    const results = rows as unknown as RawRow[]
    const total = Number(results.at(0)?.total_count ?? 0)

    // Batch-fetch tags for intervention results only (avoid N+1)
    const interventionIds = results
      .filter(r => r.type === 'intervention')
      .map(r => r.id)

    const tagMap = new Map<number, Array<{ name: string; slug: string }>>()
    if (interventionIds.length > 0) {
      const tagRows = await db
        .select({
          interventionId: interventionTags.interventionId,
          name: tags.name,
          slug: tags.slug,
        })
        .from(interventionTags)
        .innerJoin(tags, eq(interventionTags.tagId, tags.id))
        .where(inArray(interventionTags.interventionId, interventionIds))

      for (const row of tagRows) {
        if (!tagMap.has(row.interventionId)) {
          tagMap.set(row.interventionId, [])
        }
        tagMap.get(row.interventionId)!.push({ name: row.name, slug: row.slug })
      }
    }

    // Map rows to clean response format
    const data = results.map((row) => {
      if (row.type === 'intervention') {
        return {
          type: 'intervention' as const,
          id: row.id,
          rank: Number(row.rank),
          highlight: row.highlight.replace(/\ufffd/g, ''),
          speakerName: row.speaker_name,
          speakerRole: row.speaker_role,
          orderInDebate: row.order_in_debate,
          debate: {
            id: row.context_id,
            title: row.context_title,
            date: row.context_date,
            sessionType: row.session_type,
          },
          deputy: row.actor_id
            ? {
                id: row.actor_id,
                fullName: row.actor_name,
                group: row.actor_group,
                photoUrl: row.actor_photo,
              }
            : null,
          tags: tagMap.get(row.id) ?? [],
          chamber: row.chamber,
        }
      }
      else {
        return {
          type: 'scrutin' as const,
          id: row.id,
          rank: Number(row.rank),
          highlight: row.highlight.replace(/\ufffd/g, ''),
          title: row.context_title,
          date: row.context_date,
          result: row.result,
          votesFor: row.votes_for,
          votesAgainst: row.votes_against,
          votesAbstain: row.votes_abstain,
          chamber: row.chamber,
        }
      }
    })

    return paginatedResponse(data, total, page, limit)
  }
  catch (error) {
    if ((error as { statusCode?: number }).statusCode) {
      throw error
    }
    throw createError({ statusCode: 500, message: 'Failed to perform search' })
  }
})
