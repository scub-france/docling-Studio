<template>
  <nav v-if="crumbs.length > 0" class="breadcrumb" :aria-label="t('breadcrumb.aria')">
    <ol class="breadcrumb__list">
      <li
        v-for="(crumb, index) in crumbs"
        :key="`${index}-${crumb.label}`"
        class="breadcrumb__item"
      >
        <RouterLink
          v-if="crumb.kind === 'link'"
          :to="crumb.to"
          class="breadcrumb__link"
          :title="crumb.label"
        >
          {{ crumb.label }}
        </RouterLink>
        <span v-else class="breadcrumb__leaf" aria-current="page" :title="crumb.label">
          {{ crumb.label }}
        </span>
        <span v-if="index < crumbs.length - 1" class="breadcrumb__sep" aria-hidden="true"> › </span>
      </li>
    </ol>
  </nav>
</template>

<script setup lang="ts">
import { useI18n } from '../i18n'

import type { Crumb } from './types'

defineProps<{ crumbs: Crumb[] }>()

const { t } = useI18n()
</script>

<style scoped>
.breadcrumb {
  display: flex;
  align-items: center;
  min-height: 32px;
  padding: 0 1rem;
  font-size: 0.875rem;
  color: var(--color-text-muted, #9ca3af);
  border-bottom: 1px solid var(--color-border, #1a1a1d);
  background: var(--color-surface, #111113);
}

.breadcrumb__list {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
  padding: 0;
  list-style: none;
  overflow: hidden;
}

.breadcrumb__item {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.breadcrumb__link {
  color: var(--color-text-muted, #9ca3af);
  text-decoration: none;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 16rem;
  transition: color 0.15s;
}

.breadcrumb__link:hover {
  color: var(--color-text, #f3f4f6);
  text-decoration: underline;
}

.breadcrumb__leaf {
  color: var(--color-text, #f3f4f6);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 16rem;
  font-weight: 500;
}

.breadcrumb__sep {
  color: var(--color-text-muted, #6b7280);
  user-select: none;
}
</style>
