<template>
  <div class="settings-panel" data-e2e="settings-panel">
    <div class="setting-group">
      <label class="setting-label">{{ t('settings.theme') }}</label>
      <div class="setting-toggle">
        <button :class="{ active: store.theme === 'dark' }" @click="store.setTheme('dark')">
          {{ t('settings.themeDark') }}
        </button>
        <button :class="{ active: store.theme === 'light' }" @click="store.setTheme('light')">
          {{ t('settings.themeLight') }}
        </button>
      </div>
    </div>

    <div class="setting-group">
      <label class="setting-label">{{ t('settings.language') }}</label>
      <div class="setting-toggle">
        <button
          :class="{ active: store.locale === 'fr' }"
          data-e2e="lang-fr"
          @click="store.setLocale('fr')"
        >
          FR
        </button>
        <button
          :class="{ active: store.locale === 'en' }"
          data-e2e="lang-en"
          @click="store.setLocale('en')"
        >
          EN
        </button>
      </div>
    </div>

    <div class="setting-group">
      <label class="setting-label">{{ t('settings.version') }}</label>
      <span class="setting-value">{{ version }}</span>
    </div>

    <div class="setting-group">
      <label class="setting-label">{{ t('settings.about') }}</label>
      <a
        href="https://dzone.com/articles/designing-docling-studio"
        target="_blank"
        rel="noopener noreferrer"
        class="about-link"
      >
        <svg viewBox="0 0 20 20" fill="currentColor" class="about-link-icon">
          <path
            d="M9 4.804A7.968 7.968 0 005.5 4c-1.255 0-2.443.29-3.5.804v10A7.969 7.969 0 015.5 14c1.669 0 3.218.51 4.5 1.385A7.962 7.962 0 0114.5 14c1.255 0 2.443.29 3.5.804v-10A7.968 7.968 0 0014.5 4c-1.255 0-2.443.29-3.5.804V12a1 1 0 11-2 0V4.804z"
          />
        </svg>
        {{ t('settings.designArticle') }}
        <svg viewBox="0 0 20 20" fill="currentColor" class="about-link-external">
          <path
            d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z"
          />
          <path
            d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z"
          />
        </svg>
      </a>
    </div>

    <!-- #317 — server-backed runtime config; the section loads itself. -->
    <ReasoningConfigSection />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useSettingsStore } from '../store'
import { useFeatureFlagStore } from '../../feature-flags/store'
import ReasoningConfigSection from '../../admin-config/ui/ReasoningConfigSection.vue'
import { useI18n } from '../../../shared/i18n'

const store = useSettingsStore()
const featureStore = useFeatureFlagStore()
const version = computed(() => featureStore.appVersion)
const { t } = useI18n()
</script>

<style scoped>
.settings-panel {
  display: flex;
  flex-direction: column;
  gap: 24px;
  max-width: 320px;
}

.setting-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.setting-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.setting-toggle {
  display: inline-flex;
  gap: 2px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 3px;
  width: fit-content;
}

.setting-toggle button {
  padding: 6px 16px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-muted);
  background: transparent;
  border: none;
  border-radius: calc(var(--radius-sm) - 2px);
  cursor: pointer;
  transition: all 200ms ease;
}

.setting-toggle button:hover {
  color: var(--text-secondary);
  background: var(--bg-hover);
}

.setting-toggle button.active {
  background: var(--accent-muted);
  color: var(--accent);
  font-weight: 600;
}

.setting-input {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
  color: var(--text);
  font-size: 13px;
  font-family: 'IBM Plex Mono', monospace;
}

.setting-value {
  font-size: 14px;
  color: var(--text);
  font-family: 'IBM Plex Mono', monospace;
}

.about-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  text-decoration: none;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg-elevated);
  transition: all var(--transition);
  width: fit-content;
}
.about-link:hover {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--accent-muted);
}
.about-link-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}
.about-link-external {
  width: 12px;
  height: 12px;
  flex-shrink: 0;
  opacity: 0.4;
}
</style>
