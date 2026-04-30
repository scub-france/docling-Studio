<template>
  <div v-if="storeLinks.length > 0" class="stale-strip" data-e2e="stale-strip">
    <div class="stale-strip__stores">
      <div v-for="link in storeLinks" :key="link.store" class="store-row">
        <span class="store-name">{{ link.store }}</span>
        <StatusBadge :state="link.state" compact />
        <span v-if="link.pushedAt" class="store-date">
          {{ t('chunks.stale.pushedAt', { date: formatRelativeTime(link.pushedAt, locale) }) }}
        </span>
        <button
          v-if="link.state === 'Stale'"
          class="btn-reingest"
          :disabled="reingestingStores.has(link.store)"
          @click="reingest(link.store)"
        >
          {{ t('chunks.stale.reingest') }}
        </button>
      </div>
    </div>
    <button
      v-if="staleCount > 1"
      class="btn-reingest-all"
      :disabled="reingestingStores.size > 0"
      @click="reingestAll"
    >
      {{ t('chunks.stale.reingestAll') }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { DocStoreLink } from '../../../shared/types'
import { pushChunksToStore } from '../api'
import StatusBadge from '../../document/ui/StatusBadge.vue'
import { useI18n } from '../../../shared/i18n'
import { formatRelativeTime } from '../../../shared/format'
import { appLocale } from '../../../shared/appConfig'

const props = defineProps<{
  docId: string
  storeLinks: DocStoreLink[]
}>()

const { t } = useI18n()
const locale = appLocale

const reingestingStores = ref<Set<string>>(new Set())

const staleCount = computed(() => props.storeLinks.filter((l) => l.state === 'Stale').length)

async function reingest(store: string): Promise<void> {
  const next = new Set(reingestingStores.value)
  next.add(store)
  reingestingStores.value = next
  try {
    await pushChunksToStore(props.docId, store)
  } catch {
    // silent — user can retry
  } finally {
    const after = new Set(reingestingStores.value)
    after.delete(store)
    reingestingStores.value = after
  }
}

async function reingestAll(): Promise<void> {
  const stale = props.storeLinks.filter((l) => l.state === 'Stale').map((l) => l.store)
  await Promise.all(stale.map(reingest))
}
</script>

<style scoped>
.stale-strip {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 16px;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border);
  flex-wrap: wrap;
  flex-shrink: 0;
}

.stale-strip__stores {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  flex: 1;
}

.store-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 2px 8px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 12px;
}

.store-name {
  font-weight: 500;
  color: var(--text-secondary);
}

.store-date {
  color: var(--text-muted);
  font-size: 11px;
}

.btn-reingest,
.btn-reingest-all {
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 500;
  background: var(--warning-bg, rgba(234, 179, 8, 0.1));
  color: var(--warning, #ca8a04);
  border: 1px solid var(--warning, #ca8a04);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: opacity var(--transition);
  white-space: nowrap;
}

.btn-reingest:disabled,
.btn-reingest-all:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-reingest:hover:not(:disabled),
.btn-reingest-all:hover:not(:disabled) {
  opacity: 0.8;
}

.btn-reingest-all {
  flex-shrink: 0;
  padding: 4px 10px;
  font-size: 12px;
}
</style>
