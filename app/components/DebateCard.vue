<script setup lang="ts">
const props = defineProps<{
  id: number
  title: string
  date: string // ISO timestamp from API
  sessionType: string | null
  legislature: number
}>()

// Computed formatted date — explicit locale + timezone to avoid SSR/client hydration mismatch
const formattedDate = computed(() => {
  return new Intl.DateTimeFormat('fr-FR', {
    dateStyle: 'long',
    timeZone: 'Europe/Paris',
  }).format(new Date(props.date))
})
</script>

<template>
  <NuxtLink
    :to="'/debates/' + id"
    class="block bg-parchment rounded-xl border border-stone-border p-4 hover:border-bronze/40 transition-colors duration-200 cursor-pointer"
  >
    <h2 class="text-base font-semibold text-ink line-clamp-2 mb-2 font-heading">
      {{ title }}
    </h2>

    <p class="text-sm text-ink-muted mb-2">
      {{ formattedDate }}
    </p>

    <div class="flex items-center justify-between mt-auto">
      <span v-if="sessionType" class="text-xs text-ink-muted bg-marble-dark px-2 py-0.5 rounded-full uppercase tracking-wider">
        {{ sessionType }}
      </span>
      <span v-else class="flex-1" />

      <span class="text-xs text-ink-muted/60">
        {{ legislature }}e législature
      </span>
    </div>
  </NuxtLink>
</template>
