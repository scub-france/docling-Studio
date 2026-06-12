<template>
  <div class="convo" data-e2e="ask-panel">
    <div class="convo-list" data-e2e="ask-turn-list">
      <TraceEmptyState
        v-if="turns.length === 0"
        badge="2"
        :title="t('ask.emptyTitle')"
        :subtitle="t('ask.emptySub')"
      />
      <TurnCard
        v-for="turn in turns"
        :key="turn.id"
        :turn="turn"
        :selected="turn.id === selectedTurnId"
        @select="(id) => emit('select-turn', id)"
      />
    </div>
    <Composer :doc-loaded="docLoaded" :running="running" @run="(q, m) => emit('run', q, m)" />
  </div>
</template>

<script setup lang="ts">
import { useI18n } from '../../../shared/i18n'
import type { ConversationTurn } from '../types'
import Composer from './Composer.vue'
import TraceEmptyState from './TraceEmptyState.vue'
import TurnCard from './TurnCard.vue'

defineProps<{
  turns: ConversationTurn[]
  selectedTurnId: string | null
  docLoaded: boolean
  running: boolean
}>()

const emit = defineEmits<{
  'select-turn': [turnId: string]
  run: [query: string, model: string | undefined]
}>()

const { t } = useI18n()
</script>

<style scoped>
.convo {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.convo-list {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
}
</style>
