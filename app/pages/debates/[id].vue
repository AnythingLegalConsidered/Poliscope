<script setup lang="ts">
definePageMeta({
  validate: (route) => {
    return /^\d+$/.test(String(route.params.id))
  },
})

const route = useRoute()
const { data, status, error } = await useFetch(`/api/debates/${route.params.id}`)

useHead({
  title: computed(() => (data.value?.debate?.title ?? 'Debat') + ' — Poliscope'),
})

const formattedDate = computed(() => {
  const date = data.value?.debate?.date
  if (!date) return ''
  return new Intl.DateTimeFormat('fr-FR', {
    dateStyle: 'long',
    timeZone: 'Europe/Paris',
  }).format(new Date(date))
})
</script>

<template>
  <div class="max-w-2xl mx-auto">
    <!-- Loading state -->
    <LoadingSpinner v-if="status === 'pending'" />

    <!-- Error state -->
    <div v-else-if="error" class="py-8 text-center">
      <p v-if="error.statusCode === 404" class="text-ink-muted">Débat introuvable.</p>
      <p v-else class="text-ink-muted">Une erreur est survenue. Veuillez réessayer.</p>
    </div>

    <!-- Debate content -->
    <div v-else-if="data">
      <!-- Page header -->
      <div class="pb-4 mb-4 border-b border-stone-border">
        <NuxtLink to="/" class="text-bronze hover:text-bronze-dark text-sm transition-colors duration-200">
          &larr; Retour aux débats
        </NuxtLink>

        <h1 class="text-xl font-bold text-ink mt-2 font-heading">
          {{ data.debate?.title }}
        </h1>

        <div class="mt-1 text-sm text-ink-muted">
          <span>{{ formattedDate }}</span>
          <span v-if="data.debate?.sessionType"> · {{ data.debate.sessionType }}</span>
        </div>

        <p v-if="data.debate?.presidingOfficer" class="mt-1 text-sm text-ink-muted">
          Présidence : {{ data.debate.presidingOfficer }}
        </p>

        <p class="mt-1 text-sm text-ink-muted">
          {{ data.interventions?.length ?? 0 }} interventions
        </p>
      </div>

      <!-- Thread body -->
      <div v-if="data.interventions && data.interventions.length > 0">
        <InterventionCard
          v-for="intervention in data.interventions"
          :key="intervention.id"
          v-bind="intervention"
        />
      </div>

      <!-- Empty state -->
      <div v-else class="py-8 text-center text-ink-muted text-sm">
        Aucune intervention
      </div>
    </div>
  </div>
</template>
