<script setup lang="ts">
import DOMPurify from 'isomorphic-dompurify'

interface Tag {
  id: number
  name: string
  slug: string
}

interface Deputy {
  fullName: string | null
  group: string | null
  photoUrl: string | null
}

const props = defineProps<{
  speakerName: string
  speakerRole: string | null
  content: string
  orderInDebate: number
  deputy: Deputy | null
  tags: Tag[]
  deputyId?: number | null
}>()

const displayName = computed(() => props.deputy?.fullName ?? props.speakerName ?? '')

const hasHtml = computed(() => /<table[\s>]/i.test(props.content))

const sanitizedContent = computed(() => {
  if (!hasHtml.value) return ''
  return DOMPurify.sanitize(props.content, {
    ALLOWED_TAGS: ['table', 'thead', 'tbody', 'tr', 'th', 'td', 'br', 'p'],
    ALLOWED_ATTR: ['class'],
  })
})

const initials = computed(() => {
  return displayName.value
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? '')
    .join('')
})
</script>

<template>
  <div data-testid="intervention-card" class="flex gap-3 py-4 border-b border-stone-border/50">
    <!-- Avatar column -->
    <component
      :is="deputyId ? resolveComponent('NuxtLink') : 'div'"
      :to="deputyId ? `/deputies/${deputyId}` : undefined"
      class="flex-shrink-0"
    >
      <img
        v-if="deputy?.photoUrl"
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
    </component>

    <!-- Content column -->
    <div class="flex-1 min-w-0">
      <!-- Header line -->
      <div class="flex items-center gap-2 flex-wrap mb-1">
        <NuxtLink
          v-if="deputyId"
          :to="`/deputies/${deputyId}`"
          class="font-semibold text-sm text-ink hover:text-bronze transition-colors duration-200"
        >
          {{ displayName }}
        </NuxtLink>
        <span v-else class="font-semibold text-sm text-ink">{{ displayName }}</span>
        <GroupBadge v-if="deputy?.group" :group="deputy.group" />
        <span v-if="speakerRole" class="text-xs text-ink-muted">{{ speakerRole }}</span>
      </div>

      <!-- Intervention content -->
      <div v-if="hasHtml" class="text-sm text-ink/85 leading-relaxed intervention-html" v-html="sanitizedContent" />
      <p v-else class="text-sm text-ink/85 leading-relaxed whitespace-pre-wrap">{{ content }}</p>
    </div>
  </div>
</template>
