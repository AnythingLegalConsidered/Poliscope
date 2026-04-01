<template>
  <div class="min-h-screen bg-marble">
    <header class="sticky top-0 z-50 bg-marble/95 backdrop-blur-sm border-b border-stone-border">
      <div class="container mx-auto px-4 py-3 flex items-center justify-between">
        <NuxtLink to="/" class="text-xl font-bold text-ink font-heading tracking-wide hover:text-bronze transition-colors duration-200">
          Poliscope
        </NuxtLink>
        <div class="flex items-center gap-6">
          <form @submit.prevent="submitSearch" class="hidden sm:block">
            <input
              v-model="headerSearch"
              type="search"
              placeholder="Rechercher..."
              class="w-48 bg-parchment border border-stone-border rounded-lg px-3 py-1.5 text-sm text-ink placeholder-ink-muted focus:outline-none focus:border-bronze/40 transition-colors duration-200"
            />
          </form>
          <nav class="flex items-center gap-6 text-sm text-ink-muted">
            <NuxtLink to="/" active-class="text-bronze" class="hover:text-bronze transition-colors duration-200">Débats</NuxtLink>
            <NuxtLink to="/votes" active-class="text-bronze" class="hover:text-bronze transition-colors duration-200">Votes</NuxtLink>
            <NuxtLink to="/deputies" active-class="text-bronze" class="hover:text-bronze transition-colors duration-200">Parlementaires</NuxtLink>
            <NuxtLink to="/search" active-class="text-bronze" class="hover:text-bronze transition-colors duration-200">Recherche</NuxtLink>
          </nav>
        </div>
      </div>
    </header>
    <main class="container mx-auto px-4 py-8">
      <slot />
    </main>
    <footer class="border-t border-stone-border py-4 text-center text-sm text-ink-muted">
      <NuxtLink to="/about" class="hover:text-bronze transition-colors duration-200">À propos</NuxtLink>
      <span class="mx-3 opacity-40">·</span>
      <NuxtLink to="/legal" class="hover:text-bronze transition-colors duration-200">Mentions légales</NuxtLink>
    </footer>
  </div>
</template>

<script setup lang="ts">
const headerSearch = ref('')

function submitSearch() {
  if (!headerSearch.value.trim()) return
  const query = headerSearch.value.trim()
  headerSearch.value = ''
  navigateTo({ path: '/search', query: { q: query } })
}
</script>
