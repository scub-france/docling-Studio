<template>
  <div class="ask-tab" data-e2e="ask-tab">
    <div class="coming-soon">
      <p class="coming-soon-title">{{ t('workspace.askComingSoon') }}</p>
      <p class="coming-soon-sub">{{ t('workspace.askComingSoonHint') }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from '../shared/i18n'

defineProps<{ docId: string }>()

const { t } = useI18n()
</script>

<style scoped>
.ask-tab {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-muted);
}

.coming-soon {
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.coming-soon-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
}

.coming-soon-sub {
  font-size: 12px;
  color: var(--text-muted);
}
</style>
