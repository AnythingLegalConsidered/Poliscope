<script setup lang="ts">
import { watchDebounced, useIntersectionObserver } from '@vueuse/core'

useHead({
  title: computed(() => {
    const q = route.query.q as string | undefined
    return q ? `Recherche : ${q} - Poliscope` : 'Recherche - Poliscope'
  }),
})

const route = useRoute()
const router = useRouter()

// Initialize from URL params (read once — no two-way binding to avoid double-trigger loop)
const inputValue = ref((route.query.q as string) ?? '')
const q = ref((route.query.q as string) ?? '')
const activeTag = ref((route.query.tag as string) ?? '')
const deputyId = ref(route.query.deputyId ? Number(route.query.deputyId) : null)

// Debounce raw input -> q (300ms)
watchDebounced(inputValue, (val) => { q.value = val }, { debounce: 300 })

// Pagination and accumulator
const page = ref(1)
const allResults = ref<any[]>([])
const sentinel = useTemplateRef('sentinel')

// Fetch only when q is non-empty (guard against 400 on empty query)
const shouldFetch = computed(() => q.value.trim().length > 0)

const { data, status, refresh } = useFetch('/api/search', {
  query: computed(() => ({
    q: q.value,
    page: page.value,
    limit: 20,
    ...(activeTag.value ? { tag: activeTag.value } : {}),
    ...(deputyId.value ? { deputyId: deputyId.value } : {}),
  })),
  immediate: false,
  watch: false,
})

// Reset accumulator and sync URL on filter change
watch([q, activeTag, deputyId], () => {
  allResults.value = []
  page.value = 1
  router.replace({
    query: {
      ...(q.value ? { q: q.value } : {}),
      ...(activeTag.value ? { tag: activeTag.value } : {}),
      ...(deputyId.value ? { deputyId: String(deputyId.value) } : {}),
    },
  })
})

// Manual fetch trigger when shouldFetch or page changes
watch([shouldFetch, page], ([sf]) => {
  if (sf) {
    refresh()
  }
  else {
    allResults.value = []
  }
}, { immediate: true })

// Accumulate results
watch(data, (newData) => {
  if (!newData?.data) return
  if (page.value === 1) {
    allResults.value = newData.data
  }
  else {
    allResults.value.push(...newData.data)
  }
}, { immediate: true })

const hasMore = computed(() => {
  if (!data.value?.pagination) return false
  return page.value < data.value.pagination.totalPages
})

const total = computed(() => data.value?.pagination?.total ?? 0)

// Infinite scroll sentinel
useIntersectionObserver(
  sentinel,
  ([entry]) => {
    if (entry?.isIntersecting && status.value !== 'pending' && hasMore.value) {
      page.value++
    }
  },
  { rootMargin: '200px' },
)

function clearTagFilter() {
  activeTag.value = ''
}

function handleFilterTag(slug: string) {
  activeTag.value = slug
}
</script>

<template>
  <div class="max-w-3xl mx-auto">
    <!-- Large search input -->
    <div class="mb-6">
      <input
        v-model="inputValue"
        type="search"
        placeholder="Recherchez une citation, un sujet, un mot-clé..."
        class="w-full bg-parchment border border-stone-border rounded-xl px-5 py-3 text-base text-ink placeholder:text-ink-muted/60 focus:outline-none focus:border-bronze/40 transition-colors duration-200"
        autofocus
      />
    </div>

    <!-- Results header: count + active tag filter -->
    <div v-if="shouldFetch" class="flex items-center gap-3 mb-4 flex-wrap">
      <p v-if="status !== 'pending' || allResults.length > 0" class="text-sm text-ink-muted">
        <span v-if="allResults.length > 0">
          {{ total }} résultat{{ total > 1 ? 's' : '' }} pour &laquo;&nbsp;{{ q }}&nbsp;&raquo;
        </span>
      </p>

      <!-- Active tag pill with X -->
      <button
        v-if="activeTag"
        class="inline-flex items-center gap-1 text-xs bg-bronze/10 border border-bronze/30 text-bronze rounded-full px-3 py-1 hover:bg-bronze/20 transition-colors duration-200"
        @click="clearTagFilter"
      >
        {{ activeTag }}
        <span class="font-bold">×</span>
      </button>
    </div>

    <!-- Empty query placeholder -->
    <div
      v-if="!shouldFetch"
      class="flex flex-col items-center justify-center py-20 text-ink-muted/60"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="w-12 h-12 mb-4 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
      </svg>
      <p class="text-base text-center">
        Recherchez une citation, un sujet, un mot-clé...
      </p>
    </div>

    <!-- No results state -->
    <p
      v-else-if="status !== 'pending' && allResults.length === 0"
      class="text-center text-ink-muted py-12"
    >
      Aucun résultat pour &laquo;&nbsp;{{ q }}&nbsp;&raquo;
    </p>

    <!-- Results list -->
    <div v-if="allResults.length > 0" class="flex flex-col gap-4">
      <SearchResultCard
        v-for="result in allResults"
        :key="result.id"
        :speaker-name="result.speakerName"
        :speaker-role="result.speakerRole"
        :highlight="result.highlight"
        :debate="result.debate"
        :deputy="result.deputy"
        :tags="result.tags ?? []"
        @filter-tag="handleFilterTag"
      />
    </div>

    <!-- Loading spinner -->
    <div v-if="status === 'pending'" class="flex justify-center py-8">
      <LoadingSpinner />
    </div>

    <!-- All results loaded -->
    <p
      v-if="!hasMore && allResults.length > 0 && status !== 'pending'"
      class="text-center text-sm text-ink-muted/60 py-6"
    >
      Tous les résultats chargés
    </p>

    <!-- Infinite scroll sentinel -->
    <div ref="sentinel" class="h-1" aria-hidden="true" />
  </div>
</template>
