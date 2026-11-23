<template>
  <div class="coming-soon">
    <div class="coming-soon__card">
      <div class="coming-soon__badge">0.6.0</div>
      <h1 class="coming-soon__title">{{ title }}</h1>
      <p class="coming-soon__subtitle">{{ subtitle }}</p>
      <p v-if="hint" class="coming-soon__hint">{{ hint }}</p>
      <RouterLink :to="{ name: ROUTES.HOME }" class="coming-soon__back">
        {{ t('comingSoon.backHome') }}
      </RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from '../i18n'

import { ROUTES } from '../routing/names'

defineProps<{
  /** Page title shown as `<h1>`. Typically the i18n-resolved page name. */
  title: string
  /** One-sentence description of what the page will do once shipped. */
  subtitle: string
  /** Optional secondary hint (e.g. issue link, ETA). */
  hint?: string
}>()

const { t } = useI18n()
</script>

<style scoped>
.coming-soon {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 48px);
  padding: 2rem;
}

.coming-soon__card {
  max-width: 28rem;
  text-align: center;
  padding: 2.5rem 2rem;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.coming-soon__badge {
  display: inline-block;
  margin-bottom: 1rem;
  padding: 0.25rem 0.6rem;
  background: var(--accent-muted);
  color: var(--accent);
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.coming-soon__title {
  margin: 0 0 0.5rem;
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--text);
}

.coming-soon__subtitle {
  margin: 0 0 1rem;
  font-size: 1rem;
  color: var(--text-secondary);
  line-height: 1.5;
}

.coming-soon__hint {
  margin: 0 0 1.5rem;
  font-size: 0.875rem;
  color: var(--text-muted);
}

.coming-soon__back {
  display: inline-block;
  padding: 0.5rem 1rem;
  background: transparent;
  color: var(--accent);
  border: 1px solid var(--accent);
  border-radius: 6px;
  font-size: 0.875rem;
  text-decoration: none;
  transition:
    background-color 0.15s,
    color 0.15s;
}

.coming-soon__back:hover {
  background: var(--accent);
  color: var(--on-accent);
}
</style>
