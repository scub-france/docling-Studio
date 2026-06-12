<template>
  <section class="tracepanel" data-e2e="trace-panel">
    <div class="trace-head">
      <span class="trace-head-title">{{ t('trace.title') }}</span>
      <span v-if="trace" class="trace-model-chip" data-e2e="trace-model-chip">{{
        trace.modelId
      }}</span>
      <span v-if="running" class="trace-running">
        <span class="pulse-dot" />
        {{ t('trace.running') }}
      </span>
      <div class="spacer" />
      <span v-if="trace && !running" class="trace-head-stats" data-e2e="trace-stats">
        {{ t('trace.stats', { n: steps.length, dur: fmtDur(trace.totalDurationMs) }) }}
      </span>
    </div>

    <TraceEmptyState
      v-if="!trace"
      badge="3"
      :title="t('trace.emptyTitle')"
      onboarding
      :doc-loaded="docLoaded"
      :step-load="t('trace.stepLoad')"
      :step-ask="t('trace.stepAsk')"
      :step-inspect="t('trace.stepInspect')"
      data-e2e="trace-empty"
    />

    <template v-else-if="steps.length > 0">
      <div class="trace-axis">
        <span class="axis-spacer" />
        <div class="axis-track">
          <span
            v-for="(tick, i) in ticks"
            :key="i"
            class="axis-tick"
            :style="{ left: timed ? `${i * 25}%` : '0' }"
            >{{ tick }}</span
          >
        </div>
        <span class="axis-spacer-right" />
      </div>

      <div class="trace-rows">
        <TraceRow
          v-for="bar in bars"
          :key="bar.step.id"
          :step="bar.step"
          :left="bar.left"
          :width="bar.width"
          :has-timing="timed"
          :active="bar.step.id === selectedStepId"
          :answered-label="t('trace.answered')"
          :explored-label="t('trace.explored')"
          @select="(id) => emit('select-step', id)"
        />
      </div>

      <div v-if="!timed" class="trace-footnote" data-e2e="trace-footnote">
        ⓘ {{ t('trace.footnote') }}
      </div>
    </template>

    <div v-else-if="running" class="trace-warming">
      <span class="pulse-dot" />
      {{ t('trace.warming') }}
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from '../../../shared/i18n'
import { axisTicks, computeBars, fmtDur, hasTiming } from '../timeline.logic'
import type { ReasoningTrace } from '../types'
import TraceEmptyState from './TraceEmptyState.vue'
import TraceRow from './TraceRow.vue'

const props = defineProps<{
  trace: ReasoningTrace | null
  running: boolean
  selectedStepId: string | null
  docLoaded: boolean
}>()

const emit = defineEmits<{ 'select-step': [stepId: string] }>()

const { t } = useI18n()

const steps = computed(() => props.trace?.steps ?? [])
const timed = computed(() => hasTiming(steps.value))
const bars = computed(() => computeBars(steps.value))
const ticks = computed(() => (timed.value ? axisTicks(steps.value) : [t('trace.axisStepOrder')]))
</script>

<style scoped>
.tracepanel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--bg-surface);
  border-top: 1px solid var(--border);
  overflow: hidden;
}

.trace-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px 8px;
  flex-shrink: 0;
}

.trace-head-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
}

.trace-model-chip {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 10.5px;
  background: var(--bg-elevated);
  border-radius: 5px;
  padding: 1px 6px;
  color: var(--text-secondary);
}

.trace-running {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11.5px;
  color: var(--accent);
}

.spacer {
  flex: 1;
}

.trace-head-stats {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 11.5px;
  color: var(--text-muted);
}

.trace-axis {
  display: grid;
  grid-template-columns: 84px minmax(220px, 1.45fr) minmax(220px, 1fr) 104px;
  gap: 12px;
  padding: 0 16px 2px;
  flex-shrink: 0;
}

.axis-track {
  grid-column: 3;
  position: relative;
  height: 12px;
}

.axis-tick {
  position: absolute;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 9.5px;
  color: var(--text-muted);
  transform: translateX(-50%);
}

.axis-tick:first-child {
  transform: none;
}

.axis-tick:last-child {
  transform: translateX(-100%);
}

.trace-rows {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.trace-footnote {
  flex-shrink: 0;
  padding: 6px 16px 8px;
  font-size: 10.5px;
  color: var(--text-muted);
}

.trace-warming {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px;
  font-size: 12px;
  color: var(--text-muted);
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--accent);
  animation: trace-pulse 1.1s ease-in-out infinite;
}

@keyframes trace-pulse {
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
  .pulse-dot {
    animation: none;
  }
}
</style>
