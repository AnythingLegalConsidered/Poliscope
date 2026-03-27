// Political group acronym to color and label mappings
// Colors sourced from standard French political palette
const GROUP_MAP: Record<string, { color: string; label: string }> = {
  LFI: { color: '#cc2443', label: 'La France insoumise' },
  GDR: { color: '#c9462c', label: 'Gauche démocrate et républicaine' },
  SOC: { color: '#ff8080', label: 'Socialistes et apparentés' },
  ECO: { color: '#00c000', label: 'Écologistes' },
  LIOT: { color: '#ffcc00', label: 'Libertés, Indépendants, Outre-mer et Territoires' },
  MODEM: { color: '#ff9900', label: 'Démocrates' },
  REN: { color: '#ffb800', label: 'Renaissance' },
  HOR: { color: '#0099cc', label: 'Horizons' },
  LR: { color: '#0066cc', label: 'Les Républicains' },
  RN: { color: '#0d378a', label: 'Rassemblement national' },
  NI: { color: '#aaaaaa', label: 'Non-inscrits' },
}

/**
 * Returns the hex color for a given political group acronym.
 * Falls back to gray (#6b7280) for null or unknown groups.
 */
export function getGroupColor(group: string | null): string {
  if (!group) return '#6b7280'
  return GROUP_MAP[group]?.color ?? '#6b7280'
}

/**
 * Returns the full label for a given political group acronym.
 * Falls back to the raw string, or "Non-inscrit" for null.
 */
export function getGroupLabel(group: string | null): string {
  if (!group) return 'Non-inscrit'
  return GROUP_MAP[group]?.label ?? group
}
