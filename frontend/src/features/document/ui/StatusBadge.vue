<template>
  <span
    class="status-badge"
    :class="[`status-badge--${state}`, { 'status-badge--compact': compact }]"
    :title="tooltip"
    :aria-label="label"
  >
    <span aria-hidden="true" class="status-symbol">{{ symbol }}</span>
    <span v-if="!compact" class="status-text">{{ label }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import { useI18n } from '../../../shared/i18n'
import type { DocumentLifecycleState } from '../../../shared/types'

const props = withDefaults(
  defineProps<{
    state: DocumentLifecycleState
    compact?: boolean
  }>(),
  { compact: false },
)

const { t } = useI18n()

const SYMBOLS: Record<DocumentLifecycleState, string> = {
  Uploaded: '○',
  Parsed: '◐',
  Chunked: '◑',
  Ingested: '●',
  Stale: '⚠',
  Failed: '✗',
}

const symbol = computed(() => SYMBOLS[props.state] ?? '?')
const label = computed(() => t(`status.${props.state}`))
const tooltip = computed(() => t(`status.tooltip.${props.state}`))
</script>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 999px;
  white-space: nowrap;
  cursor: default;
}

.status-badge--Uploaded {
  background: rgba(99, 102, 241, 0.12);
  color: #818cf8;
}
.status-badge--Parsed {
  background: rgba(59, 130, 246, 0.12);
  color: var(--info);
}
.status-badge--Chunked {
  background: rgba(249, 115, 22, 0.12);
  color: var(--accent);
}
.status-badge--Ingested {
  background: rgba(34, 197, 94, 0.12);
  color: var(--success);
}
.status-badge--Stale {
  background: rgba(234, 179, 8, 0.12);
  color: var(--warning);
}
.status-badge--Failed {
  background: rgba(239, 68, 68, 0.12);
  color: var(--error);
}

.status-badge--compact {
  padding: 0;
  background: transparent;
  gap: 0;
}

.status-symbol {
  font-size: 1em;
  line-height: 1;
}
</style>
