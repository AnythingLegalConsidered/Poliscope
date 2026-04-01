<script setup lang="ts">
import { useIntersectionObserver } from '@vueuse/core'

const chamber = ref<string | undefined>(undefined)
const result = ref<string | undefined>(undefined)
const page = ref(1)
const allScrutins = ref<any[]>([])
const sentinel = useTemplateRef('sentinel')

const pageTitle = computed(() => {
  if (chamber.value === 'AN') return "Scrutins de l'Assemblée nationale"
  if (chamber.value === 'Senat') return 'Scrutins du Sénat'
  return 'Scrutins parlementaires'
})

useSeoMeta({
  title: 'Votes',
  description: 'Les scrutins parlementaires',
})

const { data, status } = await useFetch('/api/votes', {
  query: { page, limit: 20, chamber, result },
  lazy: true,
  watch: [page, chamber, result],
})

// Reset list and page when filters change (avoids duplicates)
watch([chamber, result], () => {
  allScrutins.value = []
  page.value = 1
})

// Append new page results; replace on page 1 (filter/search reset)
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

function selectChamber(val: string | undefined) {
  page.value = 1
  allScrutins.value = []
  chamber.value = val
}

function selectResult(val: string | undefined) {
  page.value = 1
  allScrutins.value = []
  result.value = val
}
</script>

<template>
  <div class="max-w-7xl mx-auto">
    <h1 class="text-2xl font-bold text-ink mb-4 font-heading">
      {{ pageTitle }}
    </h1>

    <!-- Chamber filter pills -->
    <div class="flex gap-2 mb-4">
      <button :class="[!chamber ? activeClass : inactiveClass]" @click="selectChamber(undefined)">
        Tous
      </button>
      <button :class="[chamber === 'AN' ? activeClass : inactiveClass]" @click="selectChamber('AN')">
        Assemblée nationale
      </button>
      <button :class="[chamber === 'Senat' ? activeClass : inactiveClass]" @click="selectChamber('Senat')">
        Sénat
      </button>
    </div>

    <!-- Result filter pills -->
    <div class="flex gap-2 mb-6">
      <button :class="[!result ? activeClass : inactiveClass]" @click="selectResult(undefined)">
        Tous
      </button>
      <button :class="[result === 'adopted' ? activeClass : inactiveClass]" @click="selectResult('adopted')">
        Adopté
      </button>
      <button :class="[result === 'rejected' ? activeClass : inactiveClass]" @click="selectResult('rejected')">
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
