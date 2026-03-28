<script setup lang="ts">
interface Tag {
  name: string
  slug: string
}

interface Debate {
  id: number
  title: string
  date: string
  sessionType: string | null
}

interface Deputy {
  id: number
  fullName: string | null
  group: string | null
  photoUrl: string | null
}

const props = defineProps<{
  speakerName: string
  speakerRole: string | null
  highlight: string
  debate: Debate
  deputy: Deputy | null
  tags?: Tag[]
  orderInDebate?: number
}>()

const emit = defineEmits<{
  'filter-tag': [slug: string]
}>()

const displayName = computed(() => props.deputy?.fullName ?? props.speakerName ?? '')

const initials = computed(() => {
  return displayName.value
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? '')
    .join('')
})

const formattedDate = computed(() => {
  if (!props.debate.date) return ''
  return new Intl.DateTimeFormat('fr-FR', {
    dateStyle: 'long',
    timeZone: 'Europe/Paris',
  }).format(new Date(props.debate.date))
})
</script>

<template>
  <div data-testid="search-result-card" class="bg-parchment border border-stone-border rounded-lg overflow-hidden">
    <!-- Debate header -->
    <div class="px-4 pt-3 pb-2">
      <div class="flex items-start justify-between gap-3">
        <NuxtLink
          :to="`/debates/${debate.id}`"
          class="text-sm font-semibold font-heading text-ink hover:text-bronze transition-colors duration-200 line-clamp-2"
        >
          {{ debate.title }}
        </NuxtLink>
        <span class="text-xs text-ink-muted whitespace-nowrap flex-shrink-0">{{ formattedDate }}</span>
      </div>
      <div class="flex items-center gap-2 mt-1">
        <span
          v-if="debate.sessionType"
          class="text-xs text-ink-muted bg-marble-dark px-2 py-0.5 rounded-full uppercase tracking-wider"
        >
          {{ debate.sessionType }}
        </span>
        <span v-if="orderInDebate" class="text-xs text-ink-muted">
          Intervention {{ orderInDebate }}
        </span>
      </div>
    </div>

    <!-- Separator -->
    <div class="border-t border-stone-border mx-4" />

    <!-- Speaker + content -->
    <div class="px-4 pt-3 pb-3">
      <!-- Speaker info row -->
      <div class="flex items-center gap-2.5 mb-2.5">
        <!-- Avatar -->
        <NuxtLink v-if="deputy" :to="`/deputies/${deputy.id}`" class="flex-shrink-0">
          <img
            v-if="deputy.photoUrl"
            :src="deputy.photoUrl"
            :alt="displayName"
            class="w-8 h-8 rounded-full object-cover border border-stone-border"
          />
          <div
            v-else
            class="w-8 h-8 rounded-full bg-bronze flex items-center justify-center text-white text-xs font-bold"
          >
            {{ initials }}
          </div>
        </NuxtLink>
        <div v-else class="flex-shrink-0">
          <div class="w-8 h-8 rounded-full bg-bronze flex items-center justify-center text-white text-xs font-bold">
            {{ initials }}
          </div>
        </div>

        <!-- Name + group + role -->
        <div class="flex items-center gap-2 flex-wrap min-w-0">
          <NuxtLink
            v-if="deputy"
            :to="`/deputies/${deputy.id}`"
            class="font-semibold text-sm font-heading text-ink hover:text-bronze transition-colors duration-200"
          >
            {{ displayName }}
          </NuxtLink>
          <span v-else class="font-semibold text-sm font-heading text-ink">{{ displayName }}</span>
          <GroupBadge v-if="deputy?.group" :group="deputy.group" />
          <span v-if="speakerRole" class="text-xs text-ink-muted">{{ speakerRole }}</span>
        </div>
      </div>

      <!-- Highlighted excerpt -->
      <!-- eslint-disable-next-line vue/no-v-html -->
      <p class="text-sm text-ink/85 leading-relaxed mb-3 pl-[42px]" v-html="highlight" />

      <!-- Tag pills -->
      <div v-if="tags && tags.length > 0" class="flex flex-wrap gap-1.5 pl-[42px]">
        <button
          v-for="tag in tags"
          :key="tag.slug"
          class="text-xs bg-marble border border-stone-border rounded-full px-2 py-0.5 hover:border-bronze/40 transition-colors duration-200 text-ink-muted"
          @click="emit('filter-tag', tag.slug)"
        >
          {{ tag.name }}
        </button>
      </div>
    </div>
  </div>
</template>
