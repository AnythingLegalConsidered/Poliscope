<script setup lang="ts">
import { useIntersectionObserver } from '@vueuse/core'

// Reactive page number — useFetch re-fetches automatically when it changes
const page = ref(1)

// Accumulate all loaded debates across pages
const allDebates = ref<any[]>([])

// Sentinel element at bottom of list for IntersectionObserver
const sentinel = useTemplateRef('sentinel')

const { data, status } = await useFetch('/api/debates', {
  query: { page, limit: 20 },
  lazy: true,
  watch: [page],
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
    if (entry.isIntersecting && status.value !== 'pending' && hasMore.value) {
      page.value++
    }
  },
  { rootMargin: '200px' },
)
</script>

<template>
  <div class="max-w-7xl mx-auto px-4 py-8">
    <h1 class="text-2xl font-bold text-primary mb-6">
      Debats de l'Assemblee nationale
    </h1>

    <!-- Debates grid -->
    <div
      v-if="allDebates.length > 0"
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
    >
      <DebateCard
        v-for="debate in allDebates"
        :key="debate.id"
        v-bind="debate"
      />
    </div>

    <!-- Empty state -->
    <p
      v-else-if="status !== 'pending'"
      class="text-gray-500 text-center py-12"
    >
      Aucun debat trouve
    </p>

    <!-- Loading spinner -->
    <div v-if="status === 'pending'" class="flex justify-center py-8">
      <LoadingSpinner />
    </div>

    <!-- All debates loaded message -->
    <p
      v-if="!hasMore && allDebates.length > 0"
      class="text-center text-sm text-gray-400 py-6"
    >
      Tous les debats charges
    </p>

    <!-- Infinite scroll sentinel -->
    <div ref="sentinel" class="h-1" aria-hidden="true" />
  </div>
</template>
