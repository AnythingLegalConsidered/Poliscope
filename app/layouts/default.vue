<template>
  <div class="min-h-screen bg-gray-50">
    <header class="bg-primary text-white py-4 px-6">
      <h1 class="text-xl font-bold">
        <NuxtLink to="/">Poliscope</NuxtLink>
      </h1>
    </header>
    <main class="container mx-auto px-4 py-8">
      <slot />
    </main>
  </div>
</template>
