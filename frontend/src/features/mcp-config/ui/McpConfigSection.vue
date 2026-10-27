<template>
  <div class="mcp-config" data-e2e="mcp-config-section">
    <div class="section-title">{{ t('settings.mcp.title') }}</div>

    <div v-if="store.loadError" class="config-error" data-e2e="mcp-config-load-error">
      {{ store.loadError }}
    </div>

    <template v-else-if="store.view && store.server">
      <div v-if="store.view.readOnly" class="readonly-banner" data-e2e="mcp-config-readonly">
        {{ t('settings.mcp.readOnly') }}
      </div>

      <div class="setting-group" data-e2e="mcp-config-status">
        <div class="setting-label">{{ t('settings.mcp.status') }}</div>
        <div class="diag-row">
          <span class="diag-dot" :class="{ on: store.server.enabled }" />
          {{
            store.server.enabled
              ? t('settings.mcp.statusOn', { path: store.server.path })
              : t('settings.mcp.statusOff')
          }}
        </div>
        <div v-if="store.server.enabled" class="warn-line">
          {{ t('settings.mcp.unauthenticated') }}
        </div>
        <div v-else class="hint">{{ t('settings.mcp.enableHint') }}</div>
      </div>

      <template v-if="store.server.enabled">
        <div class="setting-group">
          <div class="setting-label">{{ t('settings.mcp.url') }}</div>
          <div class="copy-row">
            <code class="code-line" data-e2e="mcp-config-url">{{ clientUrl }}</code>
            <button
              class="action-btn"
              data-e2e="mcp-config-copy-url"
              @click="copy('url', clientUrl)"
            >
              {{ copyLabel('url') }}
            </button>
          </div>
          <div v-if="!hostOk" class="config-error" data-e2e="mcp-config-host-warning">
            {{ t('settings.mcp.hostWarning', { host }) }}
          </div>
        </div>

        <div class="setting-group">
          <div class="setting-label">{{ t('settings.mcp.desktop') }}</div>
          <pre class="code-block" data-e2e="mcp-config-desktop-json">{{ desktopJson }}</pre>
          <div class="copy-row">
            <button
              class="action-btn"
              data-e2e="mcp-config-copy-desktop"
              @click="copy('desktop', desktopJson)"
            >
              {{ copyLabel('desktop') }}
            </button>
            <span class="hint">{{ t('settings.mcp.desktopHint') }}</span>
          </div>
        </div>

        <div class="setting-group">
          <div class="setting-label">{{ t('settings.mcp.code') }}</div>
          <div class="copy-row">
            <code class="code-line" data-e2e="mcp-config-code-cmd">{{ codeCmd }}</code>
            <button
              class="action-btn"
              data-e2e="mcp-config-copy-code"
              @click="copy('code', codeCmd)"
            >
              {{ copyLabel('code') }}
            </button>
          </div>
        </div>

        <div class="setting-group" data-e2e="mcp-config-tools">
          <div class="setting-label">{{ t('settings.mcp.published') }}</div>
          <div v-for="group in toolGroups" :key="group.key" class="tool-row">
            <span class="tool-kind">{{ t(group.label) }}</span>
            <span v-for="name in group.names" :key="name" class="tool-chip">{{ name }}</span>
          </div>
        </div>
      </template>

      <div class="subsection-title">{{ t('settings.mcp.live') }}</div>
      <div class="hint">{{ t('settings.mcp.liveHint') }}</div>

      <div class="setting-group">
        <label class="setting-label">
          {{ t('settings.mcp.maxRounds') }}
          <span
            v-if="store.view.sources.maxRounds === 'db'"
            class="source-badge"
            data-e2e="mcp-config-source-max-rounds"
            >db</span
          >
        </label>
        <input
          v-model.number="store.form.maxRounds"
          class="setting-input number-input"
          type="number"
          :min="MAX_ROUNDS_MIN"
          :max="MAX_ROUNDS_MAX"
          :disabled="store.view.readOnly"
          data-e2e="mcp-config-max-rounds"
        />
        <div class="hint">{{ t('settings.mcp.maxRoundsHint') }}</div>
      </div>

      <div class="setting-group">
        <label class="setting-label">
          {{ t('settings.mcp.maxReadTokens') }}
          <span
            v-if="store.view.sources.maxReadTokens === 'db'"
            class="source-badge"
            data-e2e="mcp-config-source-max-read-tokens"
            >db</span
          >
        </label>
        <input
          v-model.number="store.form.maxReadTokens"
          class="setting-input number-input"
          type="number"
          :min="READ_TOKENS_MIN"
          :max="READ_TOKENS_MAX"
          :disabled="store.view.readOnly"
          data-e2e="mcp-config-max-read-tokens"
        />
      </div>

      <div class="setting-group">
        <label class="setting-label">
          {{ t('settings.mcp.baseUrl') }}
          <span
            v-if="store.view.sources.studioBaseUrl === 'db'"
            class="source-badge"
            data-e2e="mcp-config-source-base-url"
            >db</span
          >
        </label>
        <input
          v-model="store.form.studioBaseUrl"
          class="setting-input"
          type="text"
          placeholder="http://localhost:3000"
          :disabled="store.view.readOnly"
          data-e2e="mcp-config-base-url"
          spellcheck="false"
        />
        <div class="hint">{{ t('settings.mcp.baseUrlHint') }}</div>
      </div>

      <div v-if="store.saveError" class="config-error" data-e2e="mcp-config-save-error">
        {{ store.saveError }}
      </div>

      <div class="actions-row">
        <button
          class="action-btn primary"
          :disabled="store.view.readOnly || store.saving || !store.dirty"
          data-e2e="mcp-config-save"
          @click="store.save()"
        >
          {{ store.saving ? t('settings.mcp.saving') : t('settings.mcp.save') }}
        </button>
        <button
          class="action-btn"
          :disabled="store.view.readOnly || store.saving"
          data-e2e="mcp-config-reset"
          @click="store.reset()"
        >
          {{ t('settings.mcp.reset') }}
        </button>
      </div>

      <div class="subsection-title">{{ t('settings.mcp.restartOnly') }}</div>
      <dl class="env-list" data-e2e="mcp-config-restart-only">
        <template v-for="row in restartOnly" :key="row.name">
          <dt>{{ row.name }}</dt>
          <dd>{{ row.value }}</dd>
        </template>
      </dl>
      <ol class="procedure">
        <li>{{ t('settings.mcp.restartStep1') }}</li>
        <li>{{ t('settings.mcp.restartStep2') }}</li>
        <li>{{ t('settings.mcp.restartStep3') }}</li>
      </ol>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useMcpConfigStore } from '../store'
import {
  claudeCodeCommand,
  claudeDesktopConfig,
  groupTools,
  hostAllowed,
  mcpClientUrl,
} from '../client'
import { MAX_ROUNDS_MAX, MAX_ROUNDS_MIN, READ_TOKENS_MAX, READ_TOKENS_MIN } from '../types'
import { useI18n } from '../../../shared/i18n'

const store = useMcpConfigStore()
const { t } = useI18n()

const host = window.location.host
const clientUrl = computed(() =>
  store.server ? mcpClientUrl(window.location.origin, store.server.path) : '',
)
const hostOk = computed(() => !store.server || hostAllowed(host, store.server.allowedHosts))
const desktopJson = computed(() => claudeDesktopConfig(clientUrl.value))
const codeCmd = computed(() => claudeCodeCommand(clientUrl.value))

const toolGroups = computed(() => {
  const groups = groupTools(store.server?.tools ?? [])
  return [
    { key: 'loop', label: 'settings.mcp.tools', names: groups.loop.map((tool) => tool.name) },
    { key: 'cards', label: 'settings.mcp.cards', names: groups.cards.map((tool) => tool.name) },
    {
      key: 'cardOnly',
      label: 'settings.mcp.cardOnly',
      names: groups.cardOnly.map((tool) => tool.name),
    },
    { key: 'prompts', label: 'settings.mcp.prompts', names: store.server?.prompts ?? [] },
  ].filter((group) => group.names.length > 0)
})

const restartOnly = computed(() => {
  const server = store.server
  if (!server) return []
  return [
    { name: 'MCP_ENABLED', value: String(server.enabled) },
    { name: 'MCP_ALLOWED_HOSTS', value: server.allowedHosts.join(',') },
    { name: 'MCP_APPS_ENABLED', value: String(server.appsEnabled) },
    { name: 'MCP_CITATION_CARD', value: String(server.citationCard) },
  ]
})

// The clipboard API exists only in a secure context (https or localhost);
// elsewhere the text stays selectable and the button does nothing.
const copied = ref<string | null>(null)

async function copy(key: string, text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text)
    copied.value = key
    setTimeout(() => {
      if (copied.value === key) copied.value = null
    }, 1500)
  } catch {
    copied.value = null
  }
}

function copyLabel(key: string): string {
  return copied.value === key ? t('settings.mcp.copied') : t('settings.mcp.copy')
}

onMounted(() => {
  void store.load()
})
</script>

<style scoped>
.mcp-config {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-top: 24px;
  border-top: 1px solid var(--border);
}

.section-title,
.subsection-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.subsection-title {
  font-size: 12px;
  margin-top: 8px;
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

.number-input {
  width: 120px;
}

.copy-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.code-line,
.code-block {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  color: var(--text);
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  user-select: all;
}

.code-line {
  flex: 1;
  overflow-x: auto;
  white-space: nowrap;
}

.code-block {
  margin: 0;
  overflow-x: auto;
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

.hint {
  font-size: 12px;
  color: var(--text-muted);
}

.warn-line {
  font-size: 12px;
  color: var(--warning, #fbbf24);
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

.tool-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.tool-kind {
  color: var(--text-muted);
  min-width: 140px;
}

.tool-chip {
  font-family: 'IBM Plex Mono', monospace;
  color: var(--text);
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 2px 8px;
}

.env-list {
  display: grid;
  grid-template-columns: max-content 1fr;
  gap: 4px 16px;
  margin: 0;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
}

.env-list dt {
  color: var(--text-secondary);
}

.env-list dd {
  margin: 0;
  color: var(--text);
  word-break: break-all;
}

.procedure {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  color: var(--text-muted);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
</style>
