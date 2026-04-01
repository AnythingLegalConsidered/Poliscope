<script setup lang="ts">
const props = defineProps<{
  votesFor: number
  votesAgainst: number
  votesAbstain: number
}>()

const total = computed(() => (props.votesFor ?? 0) + (props.votesAgainst ?? 0) + (props.votesAbstain ?? 0))

const pctFor = computed(() => total.value > 0 ? Number((props.votesFor / total.value * 100).toFixed(1)) : 0)
const pctAgainst = computed(() => total.value > 0 ? Number((props.votesAgainst / total.value * 100).toFixed(1)) : 0)
const pctAbstain = computed(() => total.value > 0 ? Number((props.votesAbstain / total.value * 100).toFixed(1)) : 0)
</script>

<template>
  <div>
    <!-- Segmented bar: for / against / abstain -->
    <div class="flex h-2 rounded-full overflow-hidden gap-0.5">
      <div
        :style="{ width: pctFor + '%' }"
        class="bg-green-500 rounded-full"
      />
      <div
        :style="{ width: pctAgainst + '%' }"
        class="bg-red-400 rounded-full"
      />
      <div
        :style="{ width: pctAbstain + '%' }"
        class="bg-stone-400 rounded-full"
      />
    </div>

    <!-- Labels -->
    <p class="text-xs text-ink-muted mt-1">
      {{ votesFor }} pour · {{ votesAgainst }} contre · {{ votesAbstain }} abstentions
    </p>
  </div>
</template>
