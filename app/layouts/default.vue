<template>
  <div class="min-h-screen bg-marble">
    <header class="sticky top-0 z-50 bg-marble/95 backdrop-blur-sm border-b border-stone-border">
      <div class="container mx-auto px-4 py-3 flex items-center justify-between">
        <NuxtLink to="/" class="text-xl font-bold text-ink font-heading tracking-wide hover:text-bronze transition-colors duration-200">
          Poliscope
        </NuxtLink>
        <nav class="flex items-center gap-6 text-sm text-ink-muted">
          <NuxtLink to="/" class="hover:text-bronze transition-colors duration-200">Débats</NuxtLink>
        </nav>
      </div>
    </header>
    <main class="container mx-auto px-4 py-8">
      <slot />
    </main>
  </div>
</template>
