<script setup lang="ts">
const props = defineProps<{
  group: string | null
}>()

const color = computed(() => getGroupColor(props.group))
const label = computed(() => getGroupLabel(props.group))
</script>

<template>
  <span
    v-if="group"
    class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold text-white"
    :style="{ backgroundColor: color }"
    :title="label"
  >
    {{ group }}
  </span>
</template>
