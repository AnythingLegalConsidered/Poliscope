<script setup lang="ts">
const props = defineProps<{
  id: number
  title: string
  date: string // ISO timestamp from API
  sessionType: string | null
  legislature: number
  chamber: string | null
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
    data-testid="debate-card"
    class="block bg-parchment rounded-xl border border-stone-border p-4 hover:border-bronze/40 transition-colors duration-200 cursor-pointer"
  >
    <h2 class="text-base font-semibold text-ink line-clamp-2 mb-2 font-heading">
      {{ title }}
    </h2>

    <p class="text-sm text-ink-muted mb-2">
      {{ formattedDate }}
    </p>

    <div class="flex items-center justify-between mt-auto">
      <div class="flex items-center gap-2">
        <!-- Chamber badge -->
        <span
          v-if="chamber === 'AN'"
          class="text-xs bg-bronze/10 text-bronze px-2 py-0.5 rounded-full font-medium"
        >
          AN
        </span>
        <span
          v-else-if="chamber === 'Senat'"
          class="text-xs bg-ink/10 text-ink px-2 py-0.5 rounded-full font-medium"
        >
          Sénat
        </span>

        <!-- Session type badge -->
        <span v-if="sessionType" class="text-xs text-ink-muted bg-marble-dark px-2 py-0.5 rounded-full uppercase tracking-wider">
          {{ sessionType }}
        </span>
      </div>

      <span class="text-xs text-ink-muted/60">
        {{ legislature }}e législature
      </span>
    </div>
  </NuxtLink>
</template>
