<script setup lang="ts">
useSeoMeta({
  title: 'À propos',
  description: 'Poliscope est un outil indépendant de transparence parlementaire qui agrège les données publiques de l\'Assemblée nationale.',
})
</script>

<template>
  <div class="max-w-2xl mx-auto">
    <h1 class="text-2xl font-bold text-ink font-heading mb-6">
      À propos de Poliscope
    </h1>

    <div class="space-y-5 text-ink-muted leading-relaxed">
      <p>
        Poliscope est un outil indépendant dédié à la transparence parlementaire. Il permet
        d'explorer les débats et l'activité des députés de l'Assemblée nationale française.
      </p>

      <p>
        L'application agrège des données publiques issues des archives de l'Assemblée nationale :
        compte-rendus intégraux des séances (CRI), interventions des députés, composition des
        groupes politiques et informations biographiques.
      </p>

      <p>
        Les données parlementaires sont mises à disposition par la
        <strong class="text-ink">Direction de l'information légale et administrative (DILA)</strong>
        sous licence ouverte. Poliscope n'est pas affilié à l'Assemblée nationale ni à aucun
        parti politique.
      </p>

      <p>
        Le projet est non partisan. Son unique objectif est de rendre l'information parlementaire
        plus accessible et consultable par tous les citoyens.
      </p>

      <p>
        Le code source de Poliscope est ouvert et disponible librement.
      </p>
    </div>
  </div>
</template>
