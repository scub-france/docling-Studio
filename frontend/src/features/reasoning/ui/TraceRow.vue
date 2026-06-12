<template>
  <div
    class="trace-row"
    :class="{ active, explored }"
    data-e2e="trace-row"
    role="button"
    tabindex="0"
    @click="emit('select', step.id)"
    @keydown.enter.prevent="emit('select', step.id)"
    @keydown.space.prevent="emit('select', step.id)"
  >
    <span class="cell-badge">
      <span class="kind-badge" :style="{ color: colors.fg, background: colors.bg }">
        {{ step.kind }}
      </span>
    </span>
    <span class="cell-title">
      <span class="title-text" :title="step.title">{{ step.title }}</span>
      <span class="chips">
        <span v-if="step.kind === 'read' && answered" class="chip chip-answered">{{
          answeredLabel
        }}</span>
        <span v-else-if="step.kind === 'read'" class="chip chip-explored">{{ exploredLabel }}</span>
        <span v-if="step.citations.length > 0" class="chip chip-ref">{{ step.citations[0] }}</span>
      </span>
    </span>
    <span class="cell-track">
      <span
        class="bar"
        :style="{ left: `${left}%`, width: `max(${width}%, 3px)`, background: colors.fg }"
      />
    </span>
    <span class="cell-meta">{{ meta }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { kindColor } from '../kindColors'
import { fmtDur } from '../timeline.logic'
import type { ReasoningStep } from '../types'

const props = defineProps<{
  step: ReasoningStep
  left: number
  width: number
  hasTiming: boolean
  active: boolean
  answeredLabel: string
  exploredLabel: string
}>()

const emit = defineEmits<{ select: [stepId: string] }>()

const colors = computed(() => kindColor(props.step.kind))
const answered = computed(() => props.step.payload?.canAnswer === true)
const explored = computed(() => props.step.kind === 'read' && !answered.value)

const meta = computed(() => {
  const parts: string[] = []
  if (props.hasTiming) parts.push(fmtDur(props.step.durationMs))
  if (props.step.tokenCount > 0) parts.push(`${props.step.tokenCount} tok`)
  return parts.join(' · ')
})
</script>

<style scoped>
.trace-row {
  display: grid;
  grid-template-columns: 84px minmax(220px, 1.45fr) minmax(220px, 1fr) 104px;
  gap: 12px;
  align-items: center;
  padding: 0 16px;
  min-height: 34px;
  border-top: 1px solid var(--border-light);
  cursor: pointer;
  transition: opacity var(--transition);
}

.trace-row:hover {
  background: var(--bg-hover);
}

.trace-row.active {
  background: var(--accent-muted);
}

.trace-row.explored {
  opacity: 0.62;
}

.trace-row.explored:hover,
.trace-row.explored.active {
  opacity: 1;
}

.cell-badge {
  display: flex;
}

.kind-badge {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 9.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-radius: 5px;
  padding: 2px 6px;
}

.cell-title {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.title-text {
  font-size: 12px;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chips {
  display: flex;
  gap: 5px;
  flex-shrink: 0;
}

.chip {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 9.5px;
  font-weight: 600;
  border-radius: 999px;
  padding: 1px 6px;
  white-space: nowrap;
}

.chip-answered {
  background: color-mix(in srgb, var(--success) 18%, transparent);
  color: var(--success);
}

.chip-explored {
  background: var(--bg-elevated);
  color: var(--text-muted);
}

.chip-ref {
  background: var(--bg);
  border: 1px solid var(--border);
  color: var(--text-secondary);
  border-radius: 5px;
}

.cell-track {
  position: relative;
  height: 8px;
  background: linear-gradient(
    to right,
    var(--border-light) 1px,
    transparent 1px 25%,
    var(--border-light) 25% calc(25% + 1px),
    transparent calc(25% + 1px) 50%,
    var(--border-light) 50% calc(50% + 1px),
    transparent calc(50% + 1px) 75%,
    var(--border-light) 75% calc(75% + 1px),
    transparent calc(75% + 1px)
  );
  border-radius: 4px;
}

.bar {
  position: absolute;
  top: 0;
  height: 8px;
  border-radius: 4px;
  min-width: 3px;
}

.cell-meta {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10.5px;
  color: var(--text-muted);
  text-align: right;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
