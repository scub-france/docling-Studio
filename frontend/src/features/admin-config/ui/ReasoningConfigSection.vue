<template>
  <div class="reasoning-config" data-e2e="reasoning-config-section">
    <div class="section-title">{{ t('settings.reasoning.title') }}</div>

    <div v-if="store.loadError" class="config-error" data-e2e="reasoning-config-load-error">
      {{ store.loadError }}
    </div>

    <template v-else-if="store.view">
      <div v-if="store.view.readOnly" class="readonly-banner" data-e2e="reasoning-config-readonly">
        {{ t('settings.reasoning.readOnly') }}
      </div>

      <div class="setting-group">
        <label class="setting-label">
          {{ t('settings.reasoning.enabled') }}
          <span v-if="store.view.sources.enabled === 'db'" class="source-badge">db</span>
        </label>
        <div class="setting-toggle">
          <button
            :class="{ active: store.form.enabled }"
            :disabled="store.view.readOnly"
            data-e2e="reasoning-config-enabled"
            @click="store.form.enabled = true"
          >
            {{ t('settings.reasoning.enabledOn') }}
          </button>
          <button
            :class="{ active: !store.form.enabled }"
            :disabled="store.view.readOnly"
            data-e2e="reasoning-config-disabled"
            @click="store.form.enabled = false"
          >
            {{ t('settings.reasoning.enabledOff') }}
          </button>
        </div>
      </div>

      <div class="setting-group">
        <label class="setting-label">
          {{ t('settings.reasoning.host') }}
          <span v-if="store.view.sources.ollamaHost === 'db'" class="source-badge">db</span>
        </label>
        <div class="host-row">
          <input
            v-model="store.form.ollamaHost"
            class="setting-input"
            type="text"
            :disabled="store.view.readOnly"
            data-e2e="reasoning-config-host"
            spellcheck="false"
          />
          <button
            class="action-btn"
            :disabled="store.view.readOnly || store.testing || !store.form.ollamaHost.trim()"
            data-e2e="reasoning-config-test"
            @click="store.testConnection()"
          >
            {{ store.testing ? t('settings.reasoning.testing') : t('settings.reasoning.test') }}
          </button>
        </div>
        <div
          v-if="store.testResult"
          class="test-result"
          :class="store.testResult.reachable ? 'ok' : 'fail'"
          data-e2e="reasoning-config-test-result"
        >
          <template v-if="store.testResult.reachable">
            {{ t('settings.reasoning.testOk', { n: store.testResult.models.length }) }}
          </template>
          <template v-else>
            {{ t('settings.reasoning.testFail') }}
            <span v-if="store.testResult.error" class="test-error">
              — {{ store.testResult.error }}</span
            >
          </template>
        </div>
      </div>

      <div class="setting-group">
        <label class="setting-label">
          {{ t('settings.reasoning.model') }}
          <span v-if="store.view.sources.modelId === 'db'" class="source-badge">db</span>
        </label>
        <select
          v-if="modelOptions.length"
          v-model="store.form.modelId"
          class="setting-input"
          :disabled="store.view.readOnly"
          data-e2e="reasoning-config-model"
        >
          <option v-for="model in modelOptions" :key="model" :value="model">{{ model }}</option>
        </select>
        <input
          v-else
          v-model="store.form.modelId"
          class="setting-input"
          type="text"
          :disabled="store.view.readOnly"
          data-e2e="reasoning-config-model"
          spellcheck="false"
        />
      </div>

      <div class="setting-group">
        <label class="setting-label">
          {{ t('settings.reasoning.maxIterations') }}
          <span v-if="store.view.sources.maxIterations === 'db'" class="source-badge">db</span>
        </label>
        <input
          v-model.number="store.form.maxIterations"
          class="setting-input iterations-input"
          type="number"
          :min="MAX_ITERATIONS_MIN"
          :max="MAX_ITERATIONS_MAX"
          :disabled="store.view.readOnly"
          data-e2e="reasoning-config-max-iterations"
        />
      </div>

      <div v-if="store.saveError" class="config-error" data-e2e="reasoning-config-save-error">
        {{ store.saveError }}
      </div>

      <div class="actions-row">
        <button
          class="action-btn primary"
          :disabled="store.view.readOnly || store.saving || !store.dirty"
          data-e2e="reasoning-config-save"
          @click="store.save()"
        >
          {{ store.saving ? t('settings.reasoning.saving') : t('settings.reasoning.save') }}
        </button>
        <button
          class="action-btn"
          :disabled="store.view.readOnly || store.saving"
          data-e2e="reasoning-config-reset"
          @click="store.reset()"
        >
          {{ t('settings.reasoning.reset') }}
        </button>
      </div>

      <div class="diagnostics" data-e2e="reasoning-config-diagnostics">
        <div class="setting-label">{{ t('settings.reasoning.diagnostics') }}</div>
        <div class="diag-row">
          <span class="diag-dot" :class="{ on: store.view.diagnostics.available }" />
          {{
            store.view.diagnostics.available
              ? t('settings.reasoning.available')
              : t('settings.reasoning.unavailable')
          }}
        </div>
        <div class="diag-line">
          {{ t('settings.reasoning.provider') }}: {{ store.view.providerType }}
        </div>
        <div class="diag-line provenance">{{ store.view.diagnostics.provenance }}</div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useAdminConfigStore } from '../store'
import { MAX_ITERATIONS_MAX, MAX_ITERATIONS_MIN } from '../types'
import { useI18n } from '../../../shared/i18n'

const store = useAdminConfigStore()
const { t } = useI18n()

// Installed models drive a select after a successful probe; the current value
// stays selectable even when the host doesn't list it (so opening the select
// can never silently change a saved config).
const modelOptions = computed<string[]>(() => {
  if (!store.testResult?.reachable || !store.testResult.models.length) return []
  const models = store.testResult.models
  return models.includes(store.form.modelId) ? models : [store.form.modelId, ...models]
})

onMounted(() => {
  void store.load()
})
</script>

<style scoped>
.reasoning-config {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-top: 24px;
  border-top: 1px solid var(--border);
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.setting-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.setting-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.source-badge {
  font-size: 10px;
  font-weight: 600;
  text-transform: none;
  letter-spacing: 0;
  color: var(--accent);
  background: var(--accent-muted);
  border-radius: var(--radius-sm);
  padding: 1px 6px;
  font-family: 'IBM Plex Mono', monospace;
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

.setting-toggle button:hover:not(:disabled) {
  color: var(--text-secondary);
  background: var(--bg-hover);
}

.setting-toggle button.active {
  background: var(--accent-muted);
  color: var(--accent);
  font-weight: 600;
}

.setting-toggle button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.setting-input {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
  color: var(--text);
  font-size: 13px;
  font-family: 'IBM Plex Mono', monospace;
  width: 100%;
}

.setting-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.iterations-input {
  width: 100px;
}

.host-row {
  display: flex;
  gap: 8px;
  align-items: stretch;
}

.action-btn {
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  white-space: nowrap;
  transition: all 200ms ease;
}

.action-btn:hover:not(:disabled) {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--accent-muted);
}

.action-btn.primary {
  color: var(--accent);
  border-color: var(--accent);
}

.action-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.actions-row {
  display: flex;
  gap: 8px;
}

.test-result {
  font-size: 12px;
}

.test-result.ok {
  color: var(--success, #4ade80);
}

.test-result.fail {
  color: var(--danger, #f87171);
}

.test-error {
  color: var(--text-muted);
  font-family: 'IBM Plex Mono', monospace;
}

.readonly-banner,
.config-error {
  font-size: 12px;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  color: var(--text-secondary);
}

.config-error {
  color: var(--danger, #f87171);
}

.diagnostics {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.diag-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--text);
}

.diag-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--danger, #f87171);
  flex-shrink: 0;
}

.diag-dot.on {
  background: var(--success, #4ade80);
}

.diag-line {
  font-size: 12px;
  color: var(--text-muted);
}

.provenance {
  font-family: 'IBM Plex Mono', monospace;
  word-break: break-all;
}
</style>
