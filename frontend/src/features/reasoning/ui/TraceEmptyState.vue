<template>
  <div class="empty" :data-e2e="dataE2e">
    <div class="empty-badge">{{ badge }}</div>
    <div class="empty-title">{{ title }}</div>
    <div v-if="subtitle" class="empty-sub">{{ subtitle }}</div>
    <div v-if="onboarding" class="empty-steps">
      <span :class="{ done: docLoaded }">
        <b>1</b> {{ stepLoad }}<template v-if="docLoaded"> ✓</template>
      </span>
      <span class="empty-arrow">→</span>
      <span><b>2</b> {{ stepAsk }}</span>
      <span class="empty-arrow">→</span>
      <span class="current"><b>3</b> {{ stepInspect }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Numbered-badge onboarding panel — shared by the trace timeline (badge "3" +
 * the ①②③ onboarding strip) and the Ask conversation (badge "2" + a sub-line).
 * Purely presentational; the parent owns the i18n strings.
 */
withDefaults(
  defineProps<{
    badge: string
    title: string
    subtitle?: string
    onboarding?: boolean
    docLoaded?: boolean
    stepLoad?: string
    stepAsk?: string
    stepInspect?: string
    dataE2e?: string
  }>(),
  { onboarding: false, docLoaded: false },
)
</script>

<style scoped>
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  flex: 1;
  padding: 24px 16px;
  text-align: center;
}

.empty-badge {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--accent-muted);
  color: var(--accent-hover);
  font-weight: 700;
  font-size: 14px;
}

.empty-title {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text);
  max-width: 320px;
}

.empty-sub {
  font-size: 11.5px;
  color: var(--text-muted);
  line-height: 1.5;
  max-width: 340px;
}

.empty-steps {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
  margin-top: 4px;
  font-size: 11px;
  color: var(--text-muted);
}

.empty-steps b {
  color: var(--text-secondary);
}

.empty-steps .done {
  color: var(--success);
}

.empty-steps .done b {
  color: var(--success);
}

.empty-steps .current,
.empty-steps .current b {
  color: var(--accent);
  font-weight: 600;
}

.empty-arrow {
  color: var(--text-muted);
  opacity: 0.6;
}
</style>
