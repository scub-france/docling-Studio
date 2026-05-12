<template>
  <div class="layers-bar" data-e2e="layers-bar">
    <span class="layers-label">LAYERS</span>
    <div class="layers-chips">
      <button
        v-for="entry in chipEntries"
        :key="entry.type"
        class="layer-chip"
        :class="{ dimmed: hiddenTypes.has(entry.type) }"
        :aria-pressed="!hiddenTypes.has(entry.type)"
        :data-e2e="`layer-chip-${entry.type}`"
        @click="toggle(entry.type)"
      >
        <span class="chip-dot" :style="{ background: entry.color }" />
        <span class="chip-type">{{ entry.type }}</span>
        <span class="chip-count">{{ entry.count }}</span>
      </button>
    </div>
    <label class="show-labels-toggle" data-e2e="show-labels-toggle">
      <input type="checkbox" :checked="showLabels" @change="onToggleLabels" />
      <span>{{ t('linked.showLabels') }}</span>
    </label>
  </div>
</template>

<script setup lang="ts">
/**
 * LAYERS chip row + "Show labels" toggle (#264).
 *
 * Externally controlled via v-model on `hiddenTypes` and `showLabels`.
 * Renders chips in `LAYER_ORDER`, then appends any extra types found on
 * the page (in insertion order) so the bar never silently swallows a new
 * element kind.
 */
import { computed } from 'vue'
import type { PageElement } from '../../../shared/types'
import { useI18n } from '../../../shared/i18n'
import { colorFor, LAYER_ORDER } from '../elementColors'

const props = defineProps<{
  elements: readonly PageElement[]
  hiddenTypes: ReadonlySet<string>
  showLabels: boolean
}>()

const emit = defineEmits<{
  'update:hiddenTypes': [next: Set<string>]
  'update:showLabels': [next: boolean]
}>()

const { t } = useI18n()

const chipEntries = computed(() => {
  const counts = new Map<string, number>()
  for (const t of LAYER_ORDER) counts.set(t, 0)
  for (const el of props.elements) {
    counts.set(el.type, (counts.get(el.type) ?? 0) + 1)
  }
  return Array.from(counts.entries()).map(([type, count]) => ({
    type,
    count,
    color: colorFor(type),
  }))
})

function toggle(type: string): void {
  const next = new Set(props.hiddenTypes)
  if (next.has(type)) next.delete(type)
  else next.add(type)
  emit('update:hiddenTypes', next)
}

function onToggleLabels(e: Event): void {
  emit('update:showLabels', (e.target as HTMLInputElement).checked)
}
</script>

<style scoped>
.layers-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 20px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border);
  flex-wrap: wrap;
}

.layers-label {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  letter-spacing: 0.08em;
  font-family: 'IBM Plex Mono', monospace;
}

.layers-chips {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.layer-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: 16px;
  font-size: 11px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: opacity var(--transition);
  font-family: 'IBM Plex Mono', monospace;
}

.layer-chip:hover {
  background: var(--bg-hover);
}

.layer-chip.dimmed {
  opacity: 0.35;
}

.chip-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.chip-count {
  color: var(--text-muted);
  font-size: 10px;
}

.show-labels-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
}
</style>
