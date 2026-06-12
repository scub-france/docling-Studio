<template>
  <div
    class="turn"
    :class="{ selected }"
    data-e2e="ask-turn-card"
    role="button"
    tabindex="0"
    @click="emit('select', turn.id)"
    @keydown.enter.prevent="emit('select', turn.id)"
  >
    <div class="turn-q">{{ turn.question }}</div>
    <div v-if="turn.status === 'running'" class="turn-a turn-a-running">
      {{ readingPlaceholder }}
    </div>
    <div v-else-if="answer" class="turn-a" :class="{ clamp: !selected }">{{ answer }}</div>
    <div class="turn-meta">
      <span class="turn-dot" :class="turn.status" />
      <span class="turn-time">{{ turn.time }}</span>
      <span v-if="stats" class="turn-stats">{{ stats }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from '../../../shared/i18n'
import { fmtDur } from '../timeline.logic'
import type { ConversationTurn } from '../types'

const props = defineProps<{
  turn: ConversationTurn
  selected: boolean
}>()

const emit = defineEmits<{ select: [turnId: string] }>()

const { t } = useI18n()

const readingPlaceholder = computed(() => t('ask.readingPlaceholder'))
const answer = computed(() => props.turn.trace?.answer ?? props.turn.errorMessage ?? '')
const stats = computed(() => {
  const trace = props.turn.trace
  if (!trace || props.turn.status === 'running') return ''
  return t('ask.turnStats', {
    n: trace.steps.length,
    dur: fmtDur(trace.totalDurationMs),
    model: trace.modelId,
  })
})
</script>

<style scoped>
.turn {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 10px 12px;
  cursor: pointer;
  transition:
    border-color var(--transition),
    background var(--transition);
}

.turn:hover {
  border-color: var(--border);
  background: var(--bg-hover);
}

.turn.selected {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent);
  background: var(--accent-muted);
}

.turn-q {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text);
  line-height: 1.45;
}

.turn-a {
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.55;
  white-space: pre-wrap;
}

.turn-a.clamp {
  display: -webkit-box;
  -webkit-line-clamp: 4;
  line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.turn-a-running {
  font-style: italic;
  color: var(--text-muted);
}

.turn-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.turn-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.turn-dot.converged {
  background: var(--success);
}

.turn-dot.error {
  background: var(--error);
}

.turn-dot.running {
  background: var(--accent);
  animation: turn-pulse 1.1s ease-in-out infinite;
}

.turn-time {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10.5px;
  color: var(--text-muted);
}

.turn-stats {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10.5px;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

@keyframes turn-pulse {
  0%,
  100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.35;
    transform: scale(0.75);
  }
}

@media (prefers-reduced-motion: reduce) {
  .turn-dot.running {
    animation: none;
  }
}
</style>
