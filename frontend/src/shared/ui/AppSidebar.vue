<template>
  <aside class="sidebar" data-e2e="sidebar" :class="{ open }">
    <nav class="sidebar-nav">
      <RouterLink
        v-for="item in items"
        :key="item.key"
        :to="item.to"
        class="nav-item"
        :class="{ active: isActive(item), 'nav-item--primary': item.primary }"
        :data-e2e="`nav-${item.key}`"
      >
        <component :is="item.icon" class="nav-icon" />
        <span class="nav-label">{{ t(item.labelKey) }}</span>
      </RouterLink>
    </nav>

    <div class="sidebar-footer">
      <div
        v-if="ingestionEnabled && ingestionStore.available"
        class="opensearch-status"
        :title="
          ingestionStore.opensearchConnected
            ? t('ingestion.opensearchConnected')
            : t('ingestion.opensearchDisconnected')
        "
      >
        <span
          class="status-dot"
          :class="ingestionStore.opensearchConnected ? 'connected' : 'disconnected'"
        />
        <span class="status-label">OpenSearch</span>
      </div>
      <a
        class="github-badge"
        href="https://github.com/scub-france/Docling-Studio"
        target="_blank"
        rel="noopener"
      >
        <img
          src="https://img.shields.io/github/stars/scub-france/Docling-Studio?style=social"
          alt="GitHub Stars"
          height="20"
        />
      </a>
      <span class="version">v{{ version }}</span>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed, h, onMounted, onBeforeUnmount, type Component } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import type { RouteLocationRaw } from 'vue-router'

import { useFeatureFlagStore } from '../../features/feature-flags/store'
import { useIngestionStore } from '../../features/ingestion/store'
import { useI18n } from '../i18n'
import { ROUTES } from '../routing/names'
import { matchesActive } from './navActive'

const featureStore = useFeatureFlagStore()
const ingestionStore = useIngestionStore()
const ingestionEnabled = computed(() => featureStore.isEnabled('ingestion'))
const version = computed(() => featureStore.appVersion)
const route = useRoute()
const { t } = useI18n()

defineProps({
  open: { type: Boolean, default: false },
})

// Inline SVG icon components — keeping them here avoids dragging in an
// icon lib and keeps the visual weight close to the previous sidebar.
const HomeIcon: Component = () =>
  h('svg', { viewBox: '0 0 20 20', fill: 'currentColor' }, [
    h('path', {
      d: 'M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z',
    }),
  ])

const DocsIcon: Component = () =>
  h('svg', { viewBox: '0 0 20 20', fill: 'currentColor' }, [
    h('path', {
      'fill-rule': 'evenodd',
      'clip-rule': 'evenodd',
      d: 'M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z',
    }),
  ])

const StoresIcon: Component = () =>
  h('svg', { viewBox: '0 0 20 20', fill: 'currentColor' }, [
    h('path', {
      'fill-rule': 'evenodd',
      'clip-rule': 'evenodd',
      d: 'M4 3a1 1 0 011-1h10a1 1 0 011 1v3a1 1 0 01-.293.707l-1.414 1.414a1 1 0 010 1.414l1.414 1.414A1 1 0 0116 11.5V14a1 1 0 01-1 1H5a1 1 0 01-1-1v-2.5a1 1 0 01.293-.707L5.707 9.5 4.293 8.086A1 1 0 014 7.379V3zm2 1v2.879l1.414 1.414a1 1 0 010 1.414L6 11.121V13h8v-1.879l-1.414-1.414a1 1 0 010-1.414L14 6.879V4H6z',
    }),
  ])

const RunsIcon: Component = () =>
  h('svg', { viewBox: '0 0 20 20', fill: 'currentColor' }, [
    h('path', {
      'fill-rule': 'evenodd',
      'clip-rule': 'evenodd',
      d: 'M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z',
    }),
  ])

const SettingsIcon: Component = () =>
  h('svg', { viewBox: '0 0 20 20', fill: 'currentColor' }, [
    h('path', {
      'fill-rule': 'evenodd',
      'clip-rule': 'evenodd',
      d: 'M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z',
    }),
  ])

type NavItem = {
  key: string
  to: RouteLocationRaw
  labelKey: string
  icon: Component
  primary?: boolean
  matchPrefixes: readonly string[]
}

const items: NavItem[] = [
  {
    key: 'home',
    to: { name: ROUTES.HOME },
    labelKey: 'nav.home',
    icon: HomeIcon,
    matchPrefixes: ['/'],
  },
  {
    key: 'docs',
    to: { name: ROUTES.DOCS_LIBRARY },
    labelKey: 'nav.docs',
    icon: DocsIcon,
    primary: true,
    matchPrefixes: ['/docs'],
  },
  {
    key: 'stores',
    to: { name: ROUTES.STORES_LIST },
    labelKey: 'nav.stores',
    icon: StoresIcon,
    matchPrefixes: ['/index'],
  },
  {
    key: 'runs',
    to: { name: ROUTES.RUNS },
    labelKey: 'nav.runs',
    icon: RunsIcon,
    matchPrefixes: ['/runs'],
  },
  {
    key: 'settings',
    to: { name: ROUTES.SETTINGS },
    labelKey: 'nav.settings',
    icon: SettingsIcon,
    matchPrefixes: ['/settings'],
  },
]

function isActive(item: NavItem): boolean {
  return matchesActive(route.path, item.matchPrefixes)
}

onMounted(() => {
  if (ingestionEnabled.value) {
    ingestionStore.checkAvailability()
    ingestionStore.startPolling(30_000)
  }
})

onBeforeUnmount(() => {
  ingestionStore.stopPolling()
})
</script>

<style scoped>
.sidebar {
  background: var(--bg-surface);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  width: 0;
  min-width: 0;
  transition:
    width 250ms ease,
    min-width 250ms ease;
}

.sidebar.open {
  width: var(--sidebar-width);
  min-width: var(--sidebar-width);
}

.sidebar-nav {
  flex: 1;
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow: hidden;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: all var(--transition);
  white-space: nowrap;
  overflow: hidden;
}

.nav-item:hover {
  background: var(--bg-hover);
  color: var(--text);
}

.nav-item.active {
  background: var(--accent-muted);
  color: var(--accent);
}

.nav-item--primary .nav-label {
  font-weight: 600;
}

.nav-item--primary:not(.active) {
  color: var(--text);
}

.nav-icon {
  width: 18px;
  height: 18px;
  min-width: 18px;
  flex-shrink: 0;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid var(--border);
  white-space: nowrap;
  overflow: hidden;
}

.github-badge {
  display: block;
  margin-bottom: 8px;
  opacity: 0.7;
  transition: opacity var(--transition);
}

.github-badge:hover {
  opacity: 1;
}

.version {
  font-size: 12px;
  color: var(--text-muted);
  font-family: 'IBM Plex Mono', monospace;
}

.opensearch-status {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
  cursor: default;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot.connected {
  background: var(--success, #22c55e);
  box-shadow: 0 0 4px var(--success, #22c55e);
}

.status-dot.disconnected {
  background: var(--error, #ef4444);
  box-shadow: 0 0 4px var(--error, #ef4444);
}

.status-label {
  font-size: 11px;
  color: var(--text-muted);
  font-family: 'IBM Plex Mono', monospace;
}
</style>
