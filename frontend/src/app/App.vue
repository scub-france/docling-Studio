<template>
  <div class="app-layout">
    <header class="topbar">
      <button
        class="burger-btn"
        data-e2e="burger-btn"
        @click="sidebarOpen = !sidebarOpen"
        :title="sidebarOpen ? t('nav.collapse') : t('nav.expand')"
      >
        <svg viewBox="0 0 20 20" fill="currentColor" class="burger-icon">
          <path
            fill-rule="evenodd"
            d="M3 5a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 10a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM3 15a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z"
            clip-rule="evenodd"
          />
        </svg>
      </button>
      <div class="topbar-logo" data-e2e="topbar-logo">
        <img src="/logo.png" alt="Docling Studio" class="topbar-logo-icon" />
        <span class="topbar-logo-text">Docling Studio</span>
      </div>
      <div class="topbar-spacer" />
      <button class="new-analysis-btn" @click="newAnalysis">
        <svg viewBox="0 0 20 20" fill="currentColor" class="new-analysis-icon">
          <path
            d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
          />
        </svg>
        {{ t('topbar.newAnalysis') }}
      </button>
    </header>

    <div v-if="showDisclaimer" class="disclaimer-banner" role="alert">
      {{ t('disclaimer.banner').replace('{n}', String(flagStore.maxFileSizeMb || 50)) }}
      <button class="disclaimer-close" @click="dismissDisclaimer" aria-label="Close">
        &times;
      </button>
    </div>

    <div class="app-body">
      <AppSidebar :open="sidebarOpen" />
      <main class="main">
        <AppBreadcrumb :crumbs="breadcrumbStore.crumbs" />
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { RouterView, useRouter } from 'vue-router'
import { AppSidebar } from '../shared/ui/index'
import AppBreadcrumb from '../shared/breadcrumb/AppBreadcrumb.vue'
import { useBreadcrumbStore } from '../shared/breadcrumb/store'
import { useSettingsStore } from '../features/settings/store'
import { useDocumentStore } from '../features/document/store'
import { useFeatureFlag } from '../features/feature-flags'
import { useFeatureFlagStore } from '../features/feature-flags/store'
import { useI18n } from '../shared/i18n'

useSettingsStore()
const flagStore = useFeatureFlagStore()
const breadcrumbStore = useBreadcrumbStore()
const { t } = useI18n()
const router = useRouter()
const documentStore = useDocumentStore()

const sidebarOpen = ref(true)
const disclaimerEnabled = useFeatureFlag('disclaimer')
const disclaimerDismissed = ref(false)
const showDisclaimer = computed(() => disclaimerEnabled.value && !disclaimerDismissed.value)

function dismissDisclaimer() {
  disclaimerDismissed.value = true
}

function newAnalysis() {
  documentStore.selectedId = null
  router.push('/studio')
}
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@300;400;500&display=swap');

:root {
  /* Dark mode palette - MistralAI Studio inspired */
  --bg: #0a0a0b;
  --bg-surface: #111113;
  --bg-elevated: #1a1a1d;
  --bg-hover: #222226;

  --accent: #f97316;
  --accent-hover: #fb923c;
  --accent-muted: rgba(249, 115, 22, 0.15);

  --text: #ececef;
  --text-secondary: #a1a1aa;
  --text-muted: #63636e;

  --border: #27272a;
  --border-light: #3f3f46;

  --success: #22c55e;
  --error: #ef4444;
  --warning: #eab308;
  --info: #3b82f6;

  --radius: 8px;
  --radius-sm: 6px;
  --radius-lg: 12px;

  --sidebar-width: 240px;
  --topbar-height: 48px;
  --transition: 150ms ease;
}

html.light {
  --bg: #fafafa;
  --bg-surface: #ffffff;
  --bg-elevated: #f4f4f5;
  --bg-hover: #e4e4e7;

  --accent: #f97316;
  --accent-hover: #ea580c;
  --accent-muted: rgba(249, 115, 22, 0.1);

  --text: #18181b;
  --text-secondary: #52525b;
  --text-muted: #a1a1aa;

  --border: #e4e4e7;
  --border-light: #d4d4d8;

  --success: #16a34a;
  --error: #dc2626;
  --warning: #ca8a04;
  --info: #2563eb;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family:
    'Inter',
    -apple-system,
    BlinkMacSystemFont,
    sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.5;
  height: 100vh;
  overflow: hidden;
  -webkit-font-smoothing: antialiased;
}

.app-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.disclaimer-banner {
  background: #f59e0b;
  color: #1a1a1d;
  font-size: 13px;
  font-weight: 500;
  text-align: center;
  padding: 8px 40px 8px 16px;
  position: relative;
  flex-shrink: 0;
}

.disclaimer-close {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: #1a1a1d;
  font-size: 18px;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
  opacity: 0.7;
}

.disclaimer-close:hover {
  opacity: 1;
}

.topbar {
  height: var(--topbar-height);
  min-height: var(--topbar-height);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 16px;
}

.burger-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: 1px solid transparent;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all var(--transition);
  padding: 0;
}

.burger-btn:hover {
  background: var(--bg-hover);
  color: var(--text);
  border-color: var(--border);
}

.burger-icon {
  width: 18px;
  height: 18px;
}

.topbar-logo {
  display: flex;
  align-items: center;
  gap: 8px;
}

.topbar-logo-icon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  object-fit: contain;
}

.topbar-logo-text {
  font-weight: 600;
  font-size: 14px;
  color: var(--text);
}

.topbar-spacer {
  flex: 1;
}

.new-analysis-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 500;
  color: white;
  background: var(--accent);
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition);
  white-space: nowrap;
}

.new-analysis-btn:hover {
  background: var(--accent-hover);
}

.new-analysis-icon {
  width: 14px;
  height: 14px;
}

.app-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.main {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: var(--bg);
}

/* Scrollbar styling */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: var(--border-light);
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: var(--text-muted);
}
</style>
