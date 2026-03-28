<script setup lang="ts">
interface Tag {
  name: string
  slug: string
}

interface Debate {
  id: number
  title: string
  date: string
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
  return new Date(props.debate.date).toLocaleDateString('fr-FR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    timeZone: 'Europe/Paris',
  })
})
</script>

<template>
  <div class="bg-parchment border border-stone-border rounded-lg p-4">
    <!-- Speaker info row -->
    <div class="flex items-start gap-3 mb-3">
      <!-- Avatar -->
      <NuxtLink v-if="deputy" :to="`/deputies/${deputy.id}`" class="flex-shrink-0">
        <img
          v-if="deputy.photoUrl"
          :src="deputy.photoUrl"
          :alt="displayName"
          class="w-10 h-10 rounded-full object-cover border border-stone-border"
        />
        <div
          v-else
          class="w-10 h-10 rounded-full bg-bronze flex items-center justify-center text-white text-sm font-bold"
        >
          {{ initials }}
        </div>
      </NuxtLink>
      <div v-else class="flex-shrink-0">
        <div class="w-10 h-10 rounded-full bg-bronze flex items-center justify-center text-white text-sm font-bold">
          {{ initials }}
        </div>
      </div>

      <!-- Speaker name + group + role -->
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 flex-wrap">
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

        <!-- Debate link -->
        <NuxtLink
          :to="`/debates/${debate.id}`"
          class="text-xs text-bronze hover:text-bronze-dark transition-colors duration-200 line-clamp-1"
        >
          {{ debate.title }}
        </NuxtLink>
        <span class="text-xs text-ink-muted">{{ formattedDate }}</span>
      </div>
    </div>

    <!-- Highlighted excerpt -->
    <!-- eslint-disable-next-line vue/no-v-html -->
    <p class="text-sm text-ink/85 leading-relaxed mb-3" v-html="highlight" />

    <!-- Tag pills -->
    <div v-if="tags && tags.length > 0" class="flex flex-wrap gap-1.5">
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
</template>
