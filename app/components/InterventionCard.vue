<script setup lang="ts">
interface Tag {
  id: number
  name: string
  slug: string
}

interface Deputy {
  fullName: string
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
}>()

const displayName = computed(() => props.deputy?.fullName ?? props.speakerName)

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
  <div class="flex gap-3 py-4 border-b border-gray-100">
    <!-- Avatar column -->
    <div class="flex-shrink-0">
      <img
        v-if="deputy?.photoUrl"
        :src="deputy.photoUrl"
        :alt="displayName"
        class="w-10 h-10 rounded-full object-cover"
      />
      <div
        v-else
        class="w-10 h-10 rounded-full bg-primary flex items-center justify-center text-white text-sm font-bold"
      >
        {{ initials }}
      </div>
    </div>

    <!-- Content column -->
    <div class="flex-1 min-w-0">
      <!-- Header line -->
      <div class="flex items-center gap-2 flex-wrap mb-1">
        <span class="font-semibold text-sm">{{ displayName }}</span>
        <GroupBadge v-if="deputy?.group" :group="deputy.group" />
        <span v-if="speakerRole" class="text-xs text-gray-500">{{ speakerRole }}</span>
      </div>

      <!-- Intervention content -->
      <p class="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">{{ content }}</p>
    </div>
  </div>
</template>
