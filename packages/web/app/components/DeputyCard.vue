<script setup lang="ts">
const props = defineProps<{
  id: number
  fullName: string
  group: string | null
  photoUrl: string | null
  constituency: string | null
}>()

// Initials fallback from fullName (first letter of each word, max 2)
const initials = computed(() => {
  return props.fullName
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? '')
    .join('')
})

// Track photo load errors to show initials fallback
const imageError = ref(false)
</script>

<template>
  <NuxtLink
    :to="`/deputies/${id}`"
    data-testid="deputy-card"
    class="flex items-center gap-3 bg-parchment rounded-xl border border-stone-border p-4 hover:border-bronze/40 transition-colors duration-200"
  >
    <!-- Photo or initials fallback -->
    <div class="flex-shrink-0">
      <img
        v-if="photoUrl && !imageError"
        :src="photoUrl"
        :alt="fullName"
        class="w-12 h-12 rounded-full object-cover border border-stone-border"
        @error="imageError = true"
      />
      <div
        v-else
        class="w-12 h-12 rounded-full bg-bronze flex items-center justify-center text-white text-sm font-bold"
      >
        {{ initials }}
      </div>
    </div>

    <!-- Name, constituency, group badge -->
    <div class="flex-1 min-w-0">
      <p class="font-semibold text-ink text-sm truncate">{{ fullName }}</p>
      <p v-if="constituency" class="text-xs text-ink-muted truncate">{{ constituency }}</p>
      <GroupBadge v-if="group" :group="group" class="mt-1" />
    </div>
  </NuxtLink>
</template>
