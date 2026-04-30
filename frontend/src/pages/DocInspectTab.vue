<template>
  <div class="inspect-tab" data-e2e="inspect-tab">
    <div class="coming-soon">
      <p class="coming-soon-title">{{ t('workspace.inspectComingSoon') }}</p>
      <p class="coming-soon-sub">{{ t('workspace.inspectComingSoonHint') }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from '../shared/i18n'

defineProps<{ docId: string }>()

const { t } = useI18n()
</script>

<style scoped>
.inspect-tab {
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
