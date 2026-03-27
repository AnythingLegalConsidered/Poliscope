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
    class="block bg-white rounded-lg shadow-sm p-4 hover:shadow-md transition-shadow duration-200 cursor-pointer"
  >
    <h2 class="text-base font-semibold text-gray-900 line-clamp-2 mb-2">
      {{ title }}
    </h2>

    <p class="text-sm text-gray-600 mb-2">
      {{ formattedDate }}
    </p>

    <div class="flex items-center justify-between mt-auto">
      <span v-if="sessionType" class="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
        {{ sessionType }}
      </span>
      <span v-else class="flex-1" />

      <span class="text-xs text-gray-400">
        {{ legislature }}e legislature
      </span>
    </div>
  </NuxtLink>
</template>
