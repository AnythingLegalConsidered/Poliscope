<template>
  <div class="min-h-screen flex items-center justify-center">
    <div class="text-center">
      <h1 class="text-4xl font-bold text-primary mb-4">{{ error?.statusCode || 500 }}</h1>
      <p class="text-gray-600 mb-6">{{ error?.message || 'Une erreur est survenue' }}</p>
      <button class="bg-primary text-white px-4 py-2 rounded" @click="handleError">
        Retour a l'accueil
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { NuxtError } from '#app'

const props = defineProps<{ error: NuxtError }>()

const handleError = () => clearError({ redirect: '/' })
</script>
