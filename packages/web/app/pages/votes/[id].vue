<script setup lang="ts">
import { useIntersectionObserver } from '@vueuse/core'

// Reject non-numeric IDs — returns 404 instead of 500
definePageMeta({
  validate: (route) => /^\d+$/.test(String(route.params.id)),
})

const route = useRoute()
const position = ref<string | null>(null)
const page = ref(1)
const allVotes = ref<any[]>([])
const sentinel = useTemplateRef('sentinel')

const { data, status, error } = await useFetch(`/api/votes/${route.params.id}`, {
  query: { page, limit: 50, position },
  watch: [page, position],
})

useSeoMeta({
  title: () => data.value?.scrutin?.title ?? 'Scrutin',
  description: () => `Résultats du scrutin : ${data.value?.scrutin?.title ?? ''}`,
})

// Reset votes accumulator when position filter changes
watch(position, () => {
  allVotes.value = []
  page.value = 1
})

// Append new vote results to allVotes — reset on page 1 (handles filter change)
watch(
  data,
  (newData) => {
    if (!newData?.votes?.data) return
    if (page.value === 1) {
      allVotes.value = newData.votes.data
    }
    else {
      allVotes.value.push(...newData.votes.data)
    }
  },
  { immediate: true },
)

// Computed: are there more vote pages to load?
const hasMore = computed(() => {
  if (!data.value?.votes?.pagination) return false
  return page.value < data.value.votes.pagination.totalPages
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

// Formatted date — explicit locale + timezone to avoid SSR/client hydration mismatch
const formattedDate = computed(() => {
  const dateStr = data.value?.scrutin?.date
  if (!dateStr) return ''
  return new Intl.DateTimeFormat('fr-FR', {
    dateStyle: 'long',
    timeZone: 'Europe/Paris',
  }).format(new Date(dateStr))
})

// Check if result bar can be shown
const hasVoteCounts = computed(() => {
  const s = data.value?.scrutin
  return s && s.votesFor !== null && s.votesAgainst !== null && s.votesAbstain !== null
})

// Tab button classes
const activeClass = 'bg-bronze text-white rounded-full px-4 py-1.5 text-sm font-medium'
const inactiveClass = 'bg-marble-dark text-ink-muted rounded-full px-4 py-1.5 text-sm font-medium hover:bg-marble-dark/80'

// Select a position filter
function selectPosition(newVal: string | null) {
  allVotes.value = []
  page.value = 1
  position.value = newVal
}

// Build actor initials fallback
function getInitials(fullName: string | null): string {
  if (!fullName) return '?'
  return fullName
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map(w => w[0]?.toUpperCase() ?? '')
    .join('')
}
</script>

<template>
  <div class="max-w-3xl mx-auto">
    <!-- Initial loading state -->
    <LoadingSpinner v-if="status === 'pending' && !data" />

    <!-- Error state -->
    <div v-else-if="error" class="py-8 text-center">
      <p v-if="error.statusCode === 404" class="text-ink-muted">
        Scrutin introuvable.
      </p>
      <p v-else class="text-ink-muted">
        Une erreur est survenue.
      </p>
    </div>

    <!-- Scrutin content -->
    <div v-else-if="data">
      <!-- Back link -->
      <NuxtLink
        to="/votes"
        class="text-bronze hover:text-bronze-dark text-sm transition-colors duration-200"
      >
        &larr; Retour aux scrutins
      </NuxtLink>

      <!-- Scrutin header -->
      <div class="pb-4 mb-4 border-b border-stone-border mt-4">
        <h1 class="text-xl font-bold text-ink font-heading mb-2">
          {{ data.scrutin.title }}
        </h1>

        <p class="text-sm text-ink-muted mb-3">
          {{ formattedDate }}
        </p>

        <!-- Chamber + result badges -->
        <div class="flex items-center gap-2 flex-wrap mb-3">
          <span
            v-if="data.scrutin.chamber === 'AN'"
            class="text-xs bg-bronze/10 text-bronze px-2 py-0.5 rounded-full font-medium"
          >
            AN
          </span>
          <span
            v-else-if="data.scrutin.chamber === 'Senat'"
            class="text-xs bg-ink/10 text-ink px-2 py-0.5 rounded-full font-medium"
          >
            Sénat
          </span>

          <span
            v-if="data.scrutin.result === 'adopted'"
            class="text-xs bg-green-500/10 text-green-700 px-2 py-0.5 rounded-full font-medium"
          >
            Adopté
          </span>
          <span
            v-else-if="data.scrutin.result === 'rejected'"
            class="text-xs bg-red-500/10 text-red-700 px-2 py-0.5 rounded-full font-medium"
          >
            Rejeté
          </span>
        </div>

        <!-- Result bar -->
        <div v-if="hasVoteCounts" class="mb-3">
          <ScrutinResultBar
            :votes-for="data.scrutin.votesFor"
            :votes-against="data.scrutin.votesAgainst"
            :votes-abstain="data.scrutin.votesAbstain"
          />
        </div>

        <!-- Official source link -->
        <a
          v-if="data.scrutin.sourceUrl"
          :href="data.scrutin.sourceUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="text-xs text-bronze hover:text-bronze-dark transition-colors duration-200"
        >
          Source officielle &rarr;
        </a>
      </div>

      <!-- Votes section -->
      <div>
        <h2 class="text-base font-semibold text-ink mb-3 font-heading">
          Votes des parlementaires
        </h2>

        <!-- Position filter pills -->
        <div class="flex gap-2 mb-4 flex-wrap">
          <button
            :class="[!position ? activeClass : inactiveClass]"
            @click="selectPosition(null)"
          >
            Tous
          </button>
          <button
            :class="[position === 'for' ? activeClass : inactiveClass]"
            @click="selectPosition('for')"
          >
            Pour
          </button>
          <button
            :class="[position === 'against' ? activeClass : inactiveClass]"
            @click="selectPosition('against')"
          >
            Contre
          </button>
          <button
            :class="[position === 'abstain' ? activeClass : inactiveClass]"
            @click="selectPosition('abstain')"
          >
            Abstention
          </button>
          <button
            :class="[position === 'absent' ? activeClass : inactiveClass]"
            @click="selectPosition('absent')"
          >
            Absent
          </button>
        </div>

        <!-- Votes list -->
        <div v-if="allVotes.length > 0">
          <div
            v-for="vote in allVotes"
            :key="vote.id"
            class="flex items-center gap-3 py-2 border-b border-stone-border/50"
          >
            <!-- Actor avatar -->
            <div class="flex-shrink-0">
              <img
                v-if="vote.actorPhotoUrl"
                :src="vote.actorPhotoUrl"
                :alt="vote.actorFullName"
                class="w-8 h-8 rounded-full object-cover border border-stone-border"
                @error="(e) => { (e.target as HTMLImageElement).style.display = 'none'; (e.target as HTMLImageElement).nextElementSibling?.removeAttribute('style') }"
              />
              <div
                :style="vote.actorPhotoUrl ? 'display:none' : ''"
                class="w-8 h-8 rounded-full bg-bronze/20 flex items-center justify-center text-bronze text-xs font-bold"
              >
                {{ getInitials(vote.actorFullName) }}
              </div>
            </div>

            <!-- Actor name + group -->
            <div class="flex-1 min-w-0 flex items-center gap-2 flex-wrap">
              <NuxtLink
                :to="`/deputies/${vote.actorId}`"
                class="text-sm text-bronze hover:text-bronze-dark transition-colors duration-200 font-medium truncate"
              >
                {{ vote.actorFullName ?? 'Inconnu' }}
              </NuxtLink>
              <GroupBadge v-if="vote.actorGroup" :group="vote.actorGroup" />
            </div>

            <!-- Vote position badge -->
            <div class="flex-shrink-0">
              <VotePositionBadge :position="vote.position" />
            </div>
          </div>
        </div>

        <!-- Empty state -->
        <p
          v-else-if="status !== 'pending'"
          class="text-ink-muted text-center py-8 text-sm"
        >
          Aucun vote trouvé
        </p>

        <!-- Loading more spinner -->
        <div v-if="status === 'pending' && data" class="flex justify-center py-6">
          <LoadingSpinner />
        </div>

        <!-- All votes loaded message -->
        <p
          v-if="!hasMore && allVotes.length > 0"
          class="text-center text-sm text-ink-muted/60 py-6"
        >
          Tous les votes chargés
        </p>

        <!-- Infinite scroll sentinel -->
        <div ref="sentinel" class="h-1" aria-hidden="true" />
      </div>
    </div>
  </div>
</template>
