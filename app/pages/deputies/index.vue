<script setup lang="ts">
import { useIntersectionObserver } from '@vueuse/core'

// Known political groups for the 17th legislature filter
const GROUPS = [
  { value: 'RN', label: 'RN — Rassemblement national' },
  { value: 'EPR', label: 'EPR — Ensemble pour la République' },
  { value: 'LFI-NFP', label: 'LFI-NFP — La France insoumise' },
  { value: 'SOC', label: 'SOC — Socialistes' },
  { value: 'DR', label: 'DR — Droite républicaine' },
  { value: 'HOR', label: 'HOR — Horizons' },
  { value: 'EcoS', label: 'EcoS — Écologistes et Social' },
  { value: 'LIOT', label: 'LIOT — Libertés, Indépendants, Outre-mer et Territoires' },
  { value: 'GDR', label: 'GDR — Gauche démocrate et républicaine' },
  { value: 'UDR', label: 'UDR — Union des droites pour la République' },
  { value: 'NI', label: 'NI — Non-inscrits' },
]

// Reactive filters and pagination state
const page = ref(1)
const search = ref('')
const group = ref<string | null>(null)

// Accumulate all loaded deputies across pages
const allDeputies = ref<any[]>([])

// Sentinel element for IntersectionObserver infinite scroll
const sentinel = useTemplateRef('sentinel')

const { data, status } = await useFetch('/api/deputies', {
  query: { page, limit: 20, search, group },
  lazy: true,
  watch: [page, search, group],
})

// Reset list and page when filters change (avoids duplicates — see research pitfall 1)
watch([search, group], () => {
  allDeputies.value = []
  page.value = 1
})

// Append new page results; replace on page 1 (filter/search reset)
watch(
  data,
  (newData) => {
    if (!newData?.data) return
    if (page.value === 1) {
      allDeputies.value = newData.data
    }
    else {
      allDeputies.value.push(...newData.data)
    }
  },
  { immediate: true },
)

// Are there more pages to load?
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
</script>

<template>
  <div class="max-w-7xl mx-auto">
    <h1 class="text-2xl font-bold text-ink mb-6 font-heading">
      Députés de l'Assemblée nationale
    </h1>

    <!-- Search and group filter controls -->
    <div class="flex flex-col sm:flex-row gap-3 mb-6">
      <input
        v-model="search"
        type="search"
        placeholder="Rechercher un député..."
        class="flex-1 bg-parchment border border-stone-border rounded-lg px-4 py-2 text-sm text-ink placeholder:text-ink-muted/60 focus:outline-none focus:border-bronze/40 transition-colors duration-200"
      />
      <select
        v-model="group"
        class="bg-parchment border border-stone-border rounded-lg px-4 py-2 text-sm text-ink focus:outline-none focus:border-bronze/40 transition-colors duration-200"
      >
        <option :value="null">Tous les groupes</option>
        <option v-for="g in GROUPS" :key="g.value" :value="g.value">
          {{ g.label }}
        </option>
      </select>
    </div>

    <!-- Deputies grid -->
    <div
      v-if="allDeputies.length > 0"
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
    >
      <DeputyCard
        v-for="deputy in allDeputies"
        :key="deputy.id"
        v-bind="deputy"
      />
    </div>

    <!-- Empty state -->
    <p
      v-else-if="status !== 'pending'"
      class="text-ink-muted text-center py-12"
    >
      Aucun député trouvé
    </p>

    <!-- Loading spinner -->
    <div v-if="status === 'pending'" class="flex justify-center py-8">
      <LoadingSpinner />
    </div>

    <!-- All deputies loaded message -->
    <p
      v-if="!hasMore && allDeputies.length > 0"
      class="text-center text-sm text-ink-muted/60 py-6"
    >
      Tous les députés chargés
    </p>

    <!-- Infinite scroll sentinel -->
    <div ref="sentinel" class="h-1" aria-hidden="true" />
  </div>
</template>
