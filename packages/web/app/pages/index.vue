<script setup lang="ts">
import { useIntersectionObserver } from '@vueuse/core'

// Reactive chamber filter — undefined means all chambers
const chamber = ref<string | undefined>(undefined)

// Dynamic page title based on active filter
const pageTitle = computed(() => {
  if (chamber.value === 'AN') return "Débats de l'Assemblée nationale"
  if (chamber.value === 'Senat') return 'Débats du Sénat'
  return 'Débats parlementaires'
})

useSeoMeta({
  title: 'Débats',
  description: 'Les derniers débats parlementaires',
  ogType: 'website',
})

// Reactive page number — useFetch re-fetches automatically when it changes
const page = ref(1)

// Accumulate all loaded debates across pages
const allDebates = ref<any[]>([])

// Sentinel element at bottom of list for IntersectionObserver
const sentinel = useTemplateRef('sentinel')

const { data, status } = await useFetch('/api/debates', {
  query: { page, limit: 20, chamber },
  lazy: true,
  watch: [page, chamber],
})

// Append new page results to allDebates
// { immediate: true } ensures SSR-hydrated initial data is captured
watch(
  data,
  (newData) => {
    if (newData?.data && newData.data.length > 0) {
      allDebates.value.push(...newData.data)
    }
  },
  { immediate: true },
)

// Computed: are there more pages to load?
const hasMore = computed(() => {
  if (!data.value?.pagination) return false
  return page.value < data.value.pagination.totalPages
})

// Infinite scroll: increment page when sentinel enters viewport
useIntersectionObserver(
  sentinel,
  ([entry]) => {
    if (entry?.isIntersecting && status.value !== 'pending' && hasMore.value) {
      page.value++
    }
  },
  { rootMargin: '200px' },
)

// Tab button classes
const activeClass = 'bg-bronze text-white rounded-full px-4 py-1.5 text-sm font-medium'
const inactiveClass = 'bg-marble-dark text-ink-muted rounded-full px-4 py-1.5 text-sm font-medium hover:bg-marble-dark/80'

// Select a chamber filter — reset pagination so infinite scroll restarts from page 1
function selectChamber(newVal: string | undefined) {
  page.value = 1
  allDebates.value = []
  chamber.value = newVal
}
</script>

<template>
  <div class="max-w-7xl mx-auto">
    <h1 class="text-2xl font-bold text-ink mb-4 font-heading">
      {{ pageTitle }}
    </h1>

    <!-- Chamber filter tabs -->
    <div class="flex gap-2 mb-6">
      <button
        :class="[!chamber ? activeClass : inactiveClass]"
        @click="selectChamber(undefined)"
      >
        Tous
      </button>
      <button
        :class="[chamber === 'AN' ? activeClass : inactiveClass]"
        @click="selectChamber('AN')"
      >
        Assemblée nationale
      </button>
      <button
        :class="[chamber === 'Senat' ? activeClass : inactiveClass]"
        @click="selectChamber('Senat')"
      >
        Sénat
      </button>
    </div>

    <!-- Debates grid -->
    <div
      v-if="allDebates.length > 0"
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
    >
      <DebateCard
        v-for="debate in allDebates"
        :key="debate.id"
        v-bind="debate"
        :chamber="debate.chamber"
      />
    </div>

    <!-- Empty state -->
    <p
      v-else-if="status !== 'pending'"
      class="text-ink-muted text-center py-12"
    >
      Aucun débat trouvé
    </p>

    <!-- Loading spinner -->
    <div v-if="status === 'pending'" class="flex justify-center py-8">
      <LoadingSpinner />
    </div>

    <!-- All debates loaded message -->
    <p
      v-if="!hasMore && allDebates.length > 0"
      class="text-center text-sm text-ink-muted/60 py-6"
    >
      Tous les débats chargés
    </p>

    <!-- Infinite scroll sentinel -->
    <div ref="sentinel" class="h-1" aria-hidden="true" />
  </div>
</template>
