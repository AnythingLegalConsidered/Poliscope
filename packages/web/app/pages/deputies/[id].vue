<script setup lang="ts">
definePageMeta({
  validate: (route) => {
    return /^\d+$/.test(String(route.params.id))
  },
})

const route = useRoute()
const page = ref(1)

const { data, status, error } = await useFetch(`/api/deputies/${route.params.id}`, {
  query: { page },
  watch: [page],
})

useSeoMeta({
  title: () => data.value?.deputy?.fullName ?? 'Député',
  description: () => `Activité parlementaire de ${data.value?.deputy?.fullName ?? 'ce député'}`,
  ogTitle: () => data.value?.deputy?.fullName ?? 'Député',
  ogType: 'profile',
  twitterCard: 'summary',
})

// Accumulate all loaded interventions across pages
const allInterventions = ref<any[]>([])

// Append new page results to allInterventions
watch(
  data,
  (newData) => {
    if (newData?.interventions?.data && newData.interventions.data.length > 0) {
      allInterventions.value.push(...newData.interventions.data)
    }
  },
  { immediate: true },
)

// Tag filter — reset when page changes
const activeTag = ref<string | null>(null)
watch(page, () => {
  activeTag.value = null
})

const filteredInterventions = computed(() => {
  if (!activeTag.value) return allInterventions.value
  return allInterventions.value.filter(i => i.tags.some((t: { slug: string }) => t.slug === activeTag.value))
})

const hasMore = computed(() => {
  if (!data.value?.interventions?.pagination) return false
  return page.value < data.value.interventions.pagination.totalPages
})

const formatDate = (dateStr: string | null | undefined) => {
  if (!dateStr) return ''
  return new Intl.DateTimeFormat('fr-FR', {
    dateStyle: 'long',
    timeZone: 'Europe/Paris',
  }).format(new Date(dateStr))
}

// Limit tag pills to top 10
const displayedTags = computed(() => {
  const stats = data.value?.tagStats ?? []
  return stats.slice(0, 10)
})
</script>

<template>
  <div class="max-w-2xl mx-auto">
    <!-- Loading state (initial) -->
    <LoadingSpinner v-if="status === 'pending' && !data" />

    <!-- Error state -->
    <div v-else-if="error" class="py-8 text-center">
      <p v-if="error.statusCode === 404" class="text-ink-muted">Député introuvable.</p>
      <p v-else class="text-ink-muted">Une erreur est survenue. Veuillez réessayer.</p>
    </div>

    <!-- Deputy content -->
    <div v-else-if="data">
      <!-- Back link -->
      <NuxtLink to="/deputies" class="text-bronze hover:text-bronze-dark text-sm transition-colors duration-200">
        &larr; Retour aux parlementaires
      </NuxtLink>

      <!-- Deputy header -->
      <div class="pb-4 mb-4 border-b border-stone-border mt-4">
        <div class="flex items-center gap-4">
          <!-- Avatar -->
          <div class="flex-shrink-0">
            <img
              v-if="data.deputy?.photoUrl"
              :src="data.deputy.photoUrl"
              :alt="data.deputy?.fullName"
              class="w-20 h-20 rounded-full object-cover border border-stone-border"
              @error="(e) => { (e.target as HTMLImageElement).style.display = 'none'; (e.target as HTMLImageElement).nextElementSibling?.removeAttribute('style') }"
            />
            <div
              :style="data.deputy?.photoUrl ? 'display:none' : ''"
              class="w-20 h-20 rounded-full bg-bronze flex items-center justify-center text-white text-xl font-bold"
            >
              {{ data.deputy?.fullName?.split(' ').filter(Boolean).slice(0, 2).map((w: string) => w[0]?.toUpperCase() ?? '').join('') }}
            </div>
          </div>

          <!-- Info -->
          <div class="flex-1 min-w-0">
            <h1 class="text-xl font-bold text-ink font-heading">
              {{ data.deputy?.fullName }}
            </h1>
            <div class="flex items-center gap-2 mt-1 flex-wrap">
              <GroupBadge v-if="data.deputy?.group" :group="data.deputy.group" />
              <span
                v-if="data.deputy?.chamber === 'AN'"
                class="text-xs bg-bronze/10 text-bronze px-2 py-0.5 rounded-full font-medium"
              >
                AN
              </span>
              <span
                v-else-if="data.deputy?.chamber === 'Senat'"
                class="text-xs bg-ink/10 text-ink px-2 py-0.5 rounded-full font-medium"
              >
                Sénat
              </span>
              <span v-if="data.deputy?.constituency" class="text-sm text-ink-muted">
                {{ data.deputy.constituency }}
              </span>
            </div>
            <p class="mt-1 text-sm text-ink-muted">
              {{ data.interventions?.pagination?.total ?? 0 }} interventions
            </p>
          </div>
        </div>
      </div>

      <!-- Tag stats -->
      <div v-if="displayedTags.length > 0" class="mb-6">
        <div class="flex flex-wrap gap-2">
          <button
            v-for="tag in displayedTags"
            :key="tag.slug"
            class="px-2 py-0.5 rounded-full text-xs bg-marble-dark border border-stone-border hover:border-bronze/40 transition-colors"
            :class="activeTag === tag.slug ? 'border-bronze text-bronze' : 'text-ink'"
            @click="activeTag = activeTag === tag.slug ? null : tag.slug"
          >
            {{ tag.name }}
            <span class="text-ink-muted ml-1">{{ tag.count }}</span>
          </button>
        </div>
      </div>

      <!-- Vote stats -->
      <div v-if="data.voteStats?.length > 0" class="mb-6">
        <h2 class="text-sm font-semibold text-ink mb-2">Votes</h2>
        <div class="flex flex-wrap gap-2">
          <span
            v-for="stat in data.voteStats"
            :key="stat.position"
            class="px-3 py-1 rounded-full text-xs font-medium"
            :class="{
              'bg-green-100 text-green-800': stat.position === 'for',
              'bg-red-100 text-red-800': stat.position === 'against',
              'bg-gray-100 text-gray-600': stat.position === 'abstain',
              'bg-stone-100 text-stone-500': stat.position === 'absent',
            }"
          >
            {{ { for: 'Pour', against: 'Contre', abstain: 'Abstention', absent: 'Absent' }[stat.position] || stat.position }}
            <span class="ml-1 font-semibold">{{ stat.count }}</span>
          </span>
        </div>
      </div>

      <!-- Interventions list -->
      <div v-if="filteredInterventions.length > 0">
        <div
          v-for="intervention in filteredInterventions"
          :key="intervention.id"
        >
          <!-- Debate context -->
          <div class="text-xs text-ink-muted mt-4 mb-1">
            <NuxtLink
              :to="`/debates/${intervention.debateId}`"
              class="text-bronze hover:text-bronze-dark transition-colors duration-200"
            >
              {{ intervention.debate?.title ?? 'Débat' }}
            </NuxtLink>
            <span v-if="intervention.debate?.date"> · {{ formatDate(intervention.debate.date) }}</span>
          </div>
          <InterventionCard v-bind="intervention" />
        </div>
      </div>

      <!-- Empty state when filtered -->
      <div v-else-if="activeTag" class="py-8 text-center text-ink-muted text-sm">
        Aucune intervention pour ce filtre.
      </div>

      <!-- Empty state no interventions -->
      <div v-else class="py-8 text-center text-ink-muted text-sm">
        Aucune intervention
      </div>

      <!-- Loading more spinner -->
      <div v-if="status === 'pending' && data" class="flex justify-center py-6">
        <LoadingSpinner />
      </div>

      <!-- Pagination -->
      <div class="flex justify-center py-6">
        <button
          v-if="hasMore"
          class="bg-parchment border border-stone-border rounded-xl px-4 py-2 text-sm text-ink hover:border-bronze/40 transition-colors"
          :disabled="status === 'pending'"
          @click="page++"
        >
          Charger plus
        </button>
        <p
          v-else-if="allInterventions.length > 0"
          class="text-center text-sm text-ink-muted/60"
        >
          Toutes les interventions chargées
        </p>
      </div>
    </div>
  </div>
</template>
