<script setup lang="ts">
const props = defineProps<{
  position: 'for' | 'against' | 'abstain' | 'absent'
}>()

const label = computed(() => {
  const labels: Record<string, string> = {
    for: 'Pour',
    against: 'Contre',
    abstain: 'Abstention',
    absent: 'Absent',
  }
  return labels[props.position] ?? props.position
})

const colorClass = computed(() => {
  const classes: Record<string, string> = {
    for: 'bg-green-500/10 text-green-700',
    against: 'bg-red-500/10 text-red-700',
    abstain: 'bg-stone-200 text-ink-muted',
    absent: 'bg-marble-dark text-ink-muted/60',
  }
  return classes[props.position] ?? 'bg-stone-200 text-ink-muted'
})
</script>

<template>
  <span
    class="px-2 py-0.5 rounded-full text-xs font-medium"
    :class="colorClass"
  >
    {{ label }}
  </span>
</template>
