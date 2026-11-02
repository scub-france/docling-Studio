<template>
  <div class="acc-row">
    <div class="acc-row-text">
      <slot name="label">
        <label v-if="labelFor" :for="labelFor" class="acc-row-label">{{ label }}</label>
        <span v-else-if="label" class="acc-row-label">{{ label }}</span>
      </slot>
      <span v-if="hint || $slots.hint" class="acc-row-hint">
        <slot name="hint">{{ hint }}</slot>
      </span>
    </div>
    <div v-if="$slots.default" class="acc-row-control">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * One line of a settings section: what it is on the left (a label and a
 * short hint), the control on the right. Wraps under the label when narrow.
 */
defineProps<{
  label?: string
  /** The id of the input the label names, so a click on it focuses the input. */
  labelFor?: string
  hint?: string
}>()
</script>

<style scoped>
.acc-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  min-height: 32px;
}

.acc-row:not(:first-child) {
  border-top: 1px solid var(--border);
}

.acc-row-text {
  flex: 1 1 260px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.acc-row-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
}

.acc-row-hint {
  font-size: 13px;
  color: var(--text-secondary);
}

.acc-row-control {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
</style>
