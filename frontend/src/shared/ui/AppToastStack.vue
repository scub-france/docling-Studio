<template>
  <div v-if="toastStore.items.length" class="toast-stack" aria-live="polite" aria-atomic="true">
    <div
      v-for="toast in toastStore.items"
      :key="toast.id"
      class="toast-item"
      :class="`toast-${toast.level}`"
      role="alert"
    >
      <div class="toast-copy">
        <div class="toast-message">{{ toast.message }}</div>
        <pre v-if="toast.detail" class="toast-detail">{{ toast.detail }}</pre>
      </div>
      <button
        type="button"
        class="toast-dismiss"
        :aria-label="t('toast.dismiss')"
        @click="toastStore.dismiss(toast.id)"
      >
        ×
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from '../i18n'
import { useToastStore } from '../toast/store'

const toastStore = useToastStore()
const { t } = useI18n()
</script>

<style scoped>
.toast-stack {
  position: fixed;
  top: calc(var(--topbar-height) + 12px);
  right: 16px;
  z-index: 90;
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: min(360px, calc(100vw - 32px));
}

.toast-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 14px;
  border-radius: var(--radius);
  border: 1px solid var(--border-light);
  background: var(--bg-elevated);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.28);
}

.toast-warning {
  border-color: rgba(234, 179, 8, 0.45);
}

.toast-error {
  border-color: rgba(239, 68, 68, 0.45);
}

.toast-success {
  border-color: rgba(34, 197, 94, 0.45);
}

.toast-info {
  border-color: rgba(59, 130, 246, 0.45);
}

.toast-copy {
  flex: 1;
  min-width: 0;
}

.toast-message {
  font-size: 13px;
  line-height: 1.4;
  color: var(--text);
}

.toast-detail {
  margin-top: 8px;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  background: rgba(0, 0, 0, 0.2);
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 1.45;
  white-space: pre-wrap;
  word-break: break-word;
}

.toast-dismiss {
  background: transparent;
  border: 0;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
  padding: 0;
}

.toast-dismiss:hover {
  color: var(--text);
}
</style>
