<template>
  <div class="settings-panel" data-e2e="settings-panel">
    <div class="settings-toolbar">
      <button
        type="button"
        class="toggle-all"
        data-e2e="settings-toggle-all"
        @click="accordion.toggleAll()"
      >
        <svg
          aria-hidden="true"
          width="15"
          height="15"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="m7 15 5 5 5-5" />
          <path d="m7 9 5-5 5 5" />
        </svg>
        {{ accordion.allClosed.value ? t('settings.expandAll') : t('settings.collapseAll') }}
      </button>
    </div>

    <AccordionSection id="general" :title="t('settings.general')" :summary="generalSummary">
      <AccordionRow :label="t('settings.theme')">
        <div class="segmented">
          <button
            type="button"
            :class="{ active: store.theme === 'dark' }"
            :aria-pressed="store.theme === 'dark'"
            @click="store.setTheme('dark')"
          >
            {{ t('settings.themeDark') }}
          </button>
          <button
            type="button"
            :class="{ active: store.theme === 'light' }"
            :aria-pressed="store.theme === 'light'"
            @click="store.setTheme('light')"
          >
            {{ t('settings.themeLight') }}
          </button>
        </div>
      </AccordionRow>
      <AccordionRow :label="t('settings.language')">
        <div class="segmented">
          <button
            type="button"
            :class="{ active: store.locale === 'fr' }"
            :aria-pressed="store.locale === 'fr'"
            data-e2e="lang-fr"
            @click="store.setLocale('fr')"
          >
            Français
          </button>
          <button
            type="button"
            :class="{ active: store.locale === 'en' }"
            :aria-pressed="store.locale === 'en'"
            data-e2e="lang-en"
            @click="store.setLocale('en')"
          >
            English
          </button>
        </div>
      </AccordionRow>
      <AccordionRow :label="t('settings.version')">
        <span class="mono-value">{{ version }}</span>
      </AccordionRow>
      <AccordionRow :label="t('settings.about')">
        <a
          href="https://dzone.com/articles/designing-docling-studio"
          target="_blank"
          rel="noopener noreferrer"
          class="about-link"
        >
          {{ t('settings.designArticle') }} ↗
        </a>
      </AccordionRow>
    </AccordionSection>

    <AccordionSection id="ask" :title="t('settings.ask.title')">
      <template #status>
        <span class="pill">{{
          askShown ? t('settings.ask.shown') : t('settings.ask.hidden')
        }}</span>
      </template>
      <!-- #317 — server-backed runtime config; the section loads itself.
           Hidden with Ask (ASK_MODE), so it is not where Ask gets turned on. -->
      <ReasoningConfigSection v-if="askShown" />
      <AccordionRow v-else :hint="t('settings.ask.hiddenHint')" data-e2e="settings-ask-hidden" />
    </AccordionSection>

    <!-- #364 — MCP server: its switch, connecting a client, live budgets,
         restart-only facts. Contributes its own sections. -->
    <McpConfigSection />
  </div>
</template>

<script setup lang="ts">
import { computed, provide } from 'vue'
import { useSettingsStore } from '../store'
import { useFeatureFlagStore } from '@/features/feature-flags'
import { ReasoningConfigSection } from '@/features/admin-config'
import { McpConfigSection } from '@/features/mcp-config'
import { ACCORDION_KEY, AccordionRow, AccordionSection, createAccordion } from '@/shared/ui'
import { STORAGE_KEYS } from '@/shared/storage/keys'
import { useI18n } from '../../../shared/i18n'

const store = useSettingsStore()
const featureStore = useFeatureFlagStore()
const version = computed(() => featureStore.appVersion)
const askShown = computed(() => featureStore.isEnabled('ask'))
const { t } = useI18n()

// Every section starts open but the environment table; what the viewer folds
// is remembered in this browser.
const accordion = createAccordion({
  storageKey: STORAGE_KEYS.settingsCollapsed,
  defaultClosed: ['mcp-advanced'],
})
provide(ACCORDION_KEY, accordion)

const generalSummary = computed(() =>
  [
    store.theme === 'dark' ? t('settings.themeDark') : t('settings.themeLight'),
    store.locale === 'fr' ? 'Français' : 'English',
    version.value,
  ].join(' · '),
)
</script>

<style scoped>
.settings-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 720px;
  margin: 0 auto;
}

.settings-toolbar {
  display: flex;
  justify-content: flex-end;
}

.toggle-all {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 36px;
  padding: 0 12px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  background: var(--bg-elevated);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.toggle-all:hover {
  color: var(--accent);
  border-color: var(--accent);
}

.segmented {
  display: inline-flex;
  gap: 2px;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 3px;
}

.segmented button {
  min-height: 30px;
  padding: 0 14px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  background: transparent;
  border: none;
  border-radius: calc(var(--radius-sm) - 2px);
  cursor: pointer;
  transition: all 200ms ease;
}

.segmented button:hover {
  background: var(--bg-hover);
}

.segmented button.active {
  background: var(--accent-muted);
  color: var(--accent);
  font-weight: 600;
}

.mono-value {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 13px;
  color: var(--text-secondary);
}

.about-link {
  font-size: 13px;
  color: var(--accent);
  text-decoration: none;
}

.about-link:hover {
  text-decoration: underline;
}

.pill {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  border: 1px solid var(--border-light);
  border-radius: 999px;
  padding: 2px 10px;
}
</style>
