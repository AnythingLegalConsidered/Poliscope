<script setup lang="ts">
import { useIntersectionObserver } from '@vueuse/core'

// Reactive filters
const chamber = ref<string | undefined>(undefined)
const result = ref<string | undefined>(undefined)

// Dynamic page title based on active chamber filter
const pageTitle = computed(() => {
  if (chamber.value === 'AN') return "Scrutins de l'Assemblée nationale"
  if (chamber.value === 'Senat') return 'Scrutins du Sénat'
  return 'Scrutins parlementaires'
})

useSeoMeta({
  title: 'Votes',
  description: 'Les scrutins parlementaires',
  ogType: 'website',
})

// Reactive page number — useFetch re-fetches automatically when it changes
const page = ref(1)

// Accumulate all loaded scrutins across pages
const allScrutins = ref<any[]>([])

// Sentinel element at bottom of list for IntersectionObserver
const sentinel = useTemplateRef('sentinel')

const { data, status } = await useFetch('/api/votes', {
  query: { page, limit: 20, chamber, result },
  lazy: true,
  watch: [page, chamber, result],
})

// Append new page results to allScrutins — reset on page 1 to handle filter changes without duplicates
watch(
  data,
  (newData) => {
    if (!newData?.data) return
    if (page.value === 1) {
      allScrutins.value = newData.data
    }
    else {
      allScrutins.value.push(...newData.data)
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
  allScrutins.value = []
  chamber.value = newVal
}

// Select a result filter — reset pagination
function selectResult(newVal: string | undefined) {
  page.value = 1
  allScrutins.value = []
  result.value = newVal
}
</script>

<template>
  <div class="max-w-7xl mx-auto">
    <h1 class="text-2xl font-bold text-ink mb-4 font-heading">
      {{ pageTitle }}
    </h1>

    <!-- Chamber filter tabs -->
    <div class="flex gap-2 mb-3 flex-wrap">
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

    <!-- Result filter tabs -->
    <div class="flex gap-2 mb-6 flex-wrap">
      <button
        :class="[!result ? activeClass : inactiveClass]"
        @click="selectResult(undefined)"
      >
        Tous
      </button>
      <button
        :class="[result === 'adopted' ? activeClass : inactiveClass]"
        @click="selectResult('adopted')"
      >
        Adopté
      </button>
      <button
        :class="[result === 'rejected' ? activeClass : inactiveClass]"
        @click="selectResult('rejected')"
      >
        Rejeté
      </button>
    </div>

    <!-- Scrutins grid -->
    <div
      v-if="allScrutins.length > 0"
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
    >
      <ScrutinCard
        v-for="scrutin in allScrutins"
        :key="scrutin.id"
        v-bind="scrutin"
      />
    </div>

    <!-- Empty state -->
    <p
      v-else-if="status !== 'pending'"
      class="text-ink-muted text-center py-12"
    >
      Aucun scrutin trouvé
    </p>

    <!-- Loading spinner -->
    <div v-if="status === 'pending'" class="flex justify-center py-8">
      <LoadingSpinner />
    </div>

    <!-- All scrutins loaded message -->
    <p
      v-if="!hasMore && allScrutins.length > 0"
      class="text-center text-sm text-ink-muted/60 py-6"
    >
      Tous les scrutins chargés
    </p>

    <!-- Infinite scroll sentinel -->
    <div ref="sentinel" class="h-1" aria-hidden="true" />
  </div>
</template>
