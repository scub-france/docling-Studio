<template>
  <AccordionSection id="mcp" :title="t('settings.mcp.title')" data-e2e="mcp-config-section">
    <template #status>
      <span v-if="state" class="pill" :class="state">
        <span class="dot" aria-hidden="true" />{{ stateLabel }}
      </span>
    </template>

    <div v-if="store.loadError" class="notice error" data-e2e="mcp-config-load-error">
      {{ store.loadError }}
    </div>

    <template v-else-if="store.view && store.server">
      <div v-if="store.view.readOnly" class="notice" data-e2e="mcp-config-readonly">
        {{ t('settings.mcp.readOnly') }}
      </div>

      <AccordionRow data-e2e="mcp-config-status">
        <template #label>
          <span class="label-line">
            <span class="row-label">{{ t('settings.mcp.serverOn') }}</span>
            <span
              v-if="store.view.sources.enabled === 'db'"
              class="changed-badge"
              data-e2e="mcp-config-source-enabled"
              >{{ t('settings.mcp.modified') }}</span
            >
          </span>
        </template>
        <template #hint>
          <span data-e2e="mcp-config-state">{{ statusHint }}</span>
          <span v-if="store.switchError" class="error-text" data-e2e="mcp-config-switch-error">
            {{ store.switchError }}
          </span>
        </template>
        <button
          v-if="store.server.enabled"
          type="button"
          role="switch"
          class="switch"
          :class="{ on: store.view.enabled }"
          :aria-checked="store.view.enabled"
          :aria-label="t('settings.mcp.title')"
          :disabled="store.view.readOnly || store.saving"
          data-e2e="mcp-config-switch"
          @click="store.setEnabled(!store.view.enabled)"
        >
          <span class="knob" aria-hidden="true" />
        </button>
      </AccordionRow>

      <template v-if="store.server.enabled">
        <AccordionRow :label="t('settings.mcp.address')">
          <template #hint>
            <span class="with-icon" :class="{ warn: !localOnly }">
              <svg v-bind="icon(13)">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
              {{ localOnly ? t('settings.mcp.localOnly') : t('settings.mcp.unauthenticated') }}
            </span>
            <span v-if="!hostOk" class="error-text" data-e2e="mcp-config-host-warning">
              {{ t('settings.mcp.hostWarning', { host }) }}
            </span>
          </template>
          <div class="input-group">
            <code class="url" data-e2e="mcp-config-url">{{ clientUrl }}</code>
            <button
              type="button"
              class="group-btn"
              data-e2e="mcp-config-copy-url"
              @click="copy('url', clientUrl)"
            >
              <svg v-bind="icon(14)">
                <rect x="9" y="9" width="13" height="13" rx="2" />
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
              </svg>
              {{ copyLabel('url') }}
            </button>
          </div>
        </AccordionRow>

        <details class="sub">
          <summary class="sub-summary">
            <span class="sub-label">{{ t('settings.mcp.connectDesktop') }}</span>
            <svg class="sub-chevron" v-bind="icon(16)"><path d="m9 18 6-6-6-6" /></svg>
          </summary>
          <div class="sub-body">
            <p class="step">1. {{ t('settings.mcp.desktopStep') }}</p>
            <div class="code-box">
              <div class="code-bar">
                <span class="code-name">claude_desktop_config.json</span>
                <button
                  type="button"
                  class="bar-btn"
                  data-e2e="mcp-config-copy-desktop"
                  @click="copy('desktop', desktopJson)"
                >
                  {{ copyLabel('desktop') }}
                </button>
              </div>
              <pre class="code-block" data-e2e="mcp-config-desktop-json">{{ desktopJson }}</pre>
            </div>
            <p class="step">2. {{ t('settings.mcp.desktopHint') }}</p>
          </div>
        </details>

        <details class="sub">
          <summary class="sub-summary">
            <span class="sub-label">{{ t('settings.mcp.connectCode') }}</span>
            <svg class="sub-chevron" v-bind="icon(16)"><path d="m9 18 6-6-6-6" /></svg>
          </summary>
          <div class="sub-body">
            <p class="step">{{ t('settings.mcp.codeStep') }}</p>
            <div class="code-box">
              <div class="code-bar">
                <span class="code-name">{{ t('settings.mcp.terminal') }}</span>
                <button
                  type="button"
                  class="bar-btn"
                  data-e2e="mcp-config-copy-code"
                  @click="copy('code', codeCmd)"
                >
                  {{ copyLabel('code') }}
                </button>
              </div>
              <pre class="code-block" data-e2e="mcp-config-code-cmd">{{ codeCmd }}</pre>
            </div>
          </div>
        </details>

        <details class="sub">
          <summary class="sub-summary">
            <span class="sub-label">{{ t('settings.mcp.published') }}</span>
            <span class="sub-meta">{{ publishedSummary }}</span>
            <svg class="sub-chevron" v-bind="icon(16)"><path d="m9 18 6-6-6-6" /></svg>
          </summary>
          <div class="sub-body tool-grid" data-e2e="mcp-config-tools">
            <template v-for="group in toolGroups" :key="group.key">
              <span class="tool-kind">{{ t(group.label) }}</span>
              <span class="tool-chips">
                <span v-for="name in group.names" :key="name" class="tool-chip">{{ name }}</span>
              </span>
            </template>
          </div>
        </details>
      </template>
    </template>
  </AccordionSection>

  <AccordionSection
    v-if="store.view"
    id="mcp-budgets"
    :title="t('settings.mcp.budgets')"
    :summary="budgetsSummary"
  >
    <AccordionRow>
      <template #label>
        <span class="label-line">
          <label for="mcp-max-rounds" class="row-label">{{ t('settings.mcp.maxRounds') }}</label>
          <span
            v-if="store.view.sources.maxRounds === 'db'"
            class="changed-badge"
            data-e2e="mcp-config-source-max-rounds"
            >{{ t('settings.mcp.modified') }}</span
          >
        </span>
      </template>
      <template #hint>
        {{ t('settings.mcp.maxRoundsShort') }}
        <template v-if="store.view.sources.maxRounds === 'db'">
          {{ t('settings.mcp.maxRoundsHint') }}
        </template>
        <template v-if="differs('maxRounds')">
          {{ envNote('maxRounds') }} ·
          <button
            type="button"
            class="link-btn"
            :disabled="store.view.readOnly"
            data-e2e="mcp-config-revert-max-rounds"
            @click="store.revert('maxRounds')"
          >
            {{ t('settings.mcp.revertLink') }}
          </button>
        </template>
      </template>
      <div class="stepper">
        <button
          type="button"
          :aria-label="t('settings.mcp.fewerRounds')"
          :disabled="store.view.readOnly || store.form.maxRounds <= MAX_ROUNDS_MIN"
          @click="store.stepRounds(-1)"
        >
          −
        </button>
        <input
          id="mcp-max-rounds"
          v-model.number="store.form.maxRounds"
          type="number"
          :min="MAX_ROUNDS_MIN"
          :max="MAX_ROUNDS_MAX"
          :disabled="store.view.readOnly"
          data-e2e="mcp-config-max-rounds"
        />
        <button
          type="button"
          :aria-label="t('settings.mcp.moreRounds')"
          :disabled="store.view.readOnly || store.form.maxRounds >= MAX_ROUNDS_MAX"
          @click="store.stepRounds(1)"
        >
          +
        </button>
      </div>
    </AccordionRow>

    <AccordionRow>
      <template #label>
        <span class="label-line">
          <label for="mcp-max-read-tokens" class="row-label">{{
            t('settings.mcp.maxReadTokens')
          }}</label>
          <span
            v-if="store.view.sources.maxReadTokens === 'db'"
            class="changed-badge"
            data-e2e="mcp-config-source-max-read-tokens"
            >{{ t('settings.mcp.modified') }}</span
          >
        </span>
      </template>
      <template #hint>
        {{ t('settings.mcp.maxReadTokensHint') }}
        <template v-if="differs('maxReadTokens')">
          {{ envNote('maxReadTokens') }} ·
          <button
            type="button"
            class="link-btn"
            :disabled="store.view.readOnly"
            data-e2e="mcp-config-revert-max-read-tokens"
            @click="store.revert('maxReadTokens')"
          >
            {{ t('settings.mcp.revertLink') }}
          </button>
        </template>
      </template>
      <span class="unit-input">
        <input
          id="mcp-max-read-tokens"
          v-model.number="store.form.maxReadTokens"
          type="number"
          :min="READ_TOKENS_MIN"
          :max="READ_TOKENS_MAX"
          step="100"
          :disabled="store.view.readOnly"
          data-e2e="mcp-config-max-read-tokens"
        />
        <span class="unit">{{ t('settings.mcp.tokensUnit') }}</span>
      </span>
    </AccordionRow>

    <AccordionRow>
      <template #label>
        <span class="label-line">
          <label for="mcp-base-url" class="row-label">{{ t('settings.mcp.baseUrl') }}</label>
          <span
            v-if="store.view.sources.studioBaseUrl === 'db'"
            class="changed-badge"
            data-e2e="mcp-config-source-base-url"
            >{{ t('settings.mcp.modified') }}</span
          >
        </span>
      </template>
      <template #hint>
        {{ t('settings.mcp.baseUrlHint') }}
        <template v-if="differs('studioBaseUrl')">
          {{ envNote('studioBaseUrl') }} ·
          <button
            type="button"
            class="link-btn"
            :disabled="store.view.readOnly"
            data-e2e="mcp-config-revert-base-url"
            @click="store.revert('studioBaseUrl')"
          >
            {{ t('settings.mcp.revertLink') }}
          </button>
        </template>
      </template>
      <input
        id="mcp-base-url"
        v-model="store.form.studioBaseUrl"
        class="text-input"
        type="text"
        :disabled="store.view.readOnly"
        data-e2e="mcp-config-base-url"
        spellcheck="false"
      />
    </AccordionRow>

    <div v-if="store.saveError" class="notice error" data-e2e="mcp-config-save-error">
      {{ store.saveError }}
    </div>

    <div class="budget-footer">
      <span class="footer-note" :class="{ dirty: store.dirty }">
        {{ store.dirty ? t('settings.mcp.unsaved') : t('settings.mcp.liveHint') }}
      </span>
      <div class="footer-actions">
        <button
          type="button"
          class="btn"
          :title="t('settings.mcp.resetHint')"
          :disabled="store.view.readOnly || store.saving"
          data-e2e="mcp-config-reset"
          @click="store.reset()"
        >
          {{ t('settings.mcp.reset') }}
        </button>
        <button
          type="button"
          class="btn primary"
          :disabled="store.view.readOnly || store.saving || !store.dirty"
          data-e2e="mcp-config-save"
          @click="store.save()"
        >
          {{ store.saving ? t('settings.mcp.saving') : t('settings.mcp.save') }}
        </button>
      </div>
    </div>
  </AccordionSection>

  <AccordionSection
    v-if="store.server"
    id="mcp-advanced"
    :title="t('settings.mcp.advanced')"
    :summary="t('settings.mcp.advancedSummary', { n: restartOnly.length })"
  >
    <div class="advanced-body">
      <div class="env-wrap">
        <table class="env-table" data-e2e="mcp-config-restart-only">
          <thead>
            <tr>
              <th scope="col">{{ t('settings.mcp.envVariable') }}</th>
              <th scope="col">{{ t('settings.mcp.envValueColumn') }}</th>
              <th scope="col">{{ t('settings.mcp.envRole') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in restartOnly" :key="row.name">
              <td class="mono">{{ row.name }}</td>
              <td class="mono">{{ row.value }}</td>
              <td class="effect">{{ row.effect }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="procedure">{{ t('settings.mcp.restartHow') }}</p>
    </div>
  </AccordionSection>
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
import {
  MAX_ROUNDS_MAX,
  MAX_ROUNDS_MIN,
  READ_TOKENS_MAX,
  READ_TOKENS_MIN,
  type McpBudgetField,
} from '../types'
import { AccordionRow, AccordionSection } from '@/shared/ui'
import { useI18n } from '../../../shared/i18n'

/**
 * The MCP part of the settings accordion (#364): three sections — the server
 * (its switch, its address, connecting a client, what it publishes), the
 * live read budgets, and the restart-only environment.
 */
const store = useMcpConfigStore()
const { t } = useI18n()

/** Attributes of a decorative stroke icon of `size` px. */
function icon(size: number) {
  return {
    'aria-hidden': true,
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    'stroke-width': 2,
    'stroke-linecap': 'round' as const,
    'stroke-linejoin': 'round' as const,
  }
}

const host = window.location.host
const clientUrl = computed(() =>
  store.server ? mcpClientUrl(window.location.origin, store.server.path) : '',
)
const hostOk = computed(() => !store.server || hostAllowed(host, store.server.allowedHosts))
const desktopJson = computed(() => claudeDesktopConfig(clientUrl.value))
const codeCmd = computed(() => claudeCodeCommand(clientUrl.value))

/** Only loopback hosts are allowed. A browser guard (DNS rebinding), not network isolation:
 * a client that reaches the port can still send an allowed Host header. */
const localOnly = computed(() =>
  (store.server?.allowedHosts ?? []).every((allowed) =>
    /^(127\.0\.0\.1|localhost|\[::1\])(:|$)/.test(allowed),
  ),
)

/** The server's state in one word: on, turned off here, or not mounted at all. */
const state = computed<'on' | 'off' | 'unmounted' | null>(() => {
  if (!store.server || !store.view) return null
  if (!store.server.enabled) return 'unmounted'
  return store.view.enabled ? 'on' : 'off'
})
const stateLabel = computed(() => {
  if (state.value === 'on') return t('settings.mcp.badgeOn')
  if (state.value === 'off') return t('settings.mcp.badgeOff')
  return t('settings.mcp.badgeUnmounted')
})
const statusHint = computed(() => {
  if (state.value === 'on') return t('settings.mcp.serverHint')
  if (state.value === 'off') return t('settings.mcp.offHint')
  return t('settings.mcp.enableHint')
})

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

const publishedSummary = computed(() => {
  const groups = groupTools(store.server?.tools ?? [])
  return t('settings.mcp.publishedSummary', {
    tools: groups.loop.length,
    cards: groups.cards.length,
    prompts: store.server?.prompts.length ?? 0,
  })
})

const budgetsSummary = computed(() =>
  store.view
    ? t('settings.mcp.budgetsSummary', {
        rounds: store.view.maxRounds,
        tokens: store.view.maxReadTokens,
      })
    : '',
)

function formValue(field: McpBudgetField): string | number {
  return field === 'studioBaseUrl' ? store.form.studioBaseUrl.trim() : store.form[field]
}

/** The form holds something other than the environment's value. */
function differs(field: McpBudgetField): boolean {
  const defaults = store.view?.defaults
  return defaults !== undefined && formValue(field) !== defaults[field]
}

/** "Environment: 4000", the value a field returns to. */
function envNote(field: McpBudgetField): string {
  const value = store.view?.defaults[field]
  const shown = value === '' || value === undefined ? t('settings.mcp.envNone') : String(value)
  return t('settings.mcp.envValue', { value: shown })
}

const restartOnly = computed(() => {
  const server = store.server
  if (!server) return []
  return [
    { name: 'MCP_ENABLED', value: String(server.enabled), effect: t('settings.mcp.envEnabled') },
    {
      name: 'MCP_ALLOWED_HOSTS',
      value: server.allowedHosts.join(', '),
      effect: t('settings.mcp.envHosts'),
    },
    {
      name: 'MCP_APPS_ENABLED',
      value: String(server.appsEnabled),
      effect: t('settings.mcp.envApps'),
    },
    {
      name: 'MCP_CITATION_CARD',
      value: String(server.citationCard),
      effect: t('settings.mcp.envCitation'),
    },
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
/* One grid for every row: controls 36 px high, 8 px corners, right-aligned. */

.notice {
  margin: 12px 20px 0;
  font-size: 13px;
  padding: 8px 12px;
  border-radius: var(--radius);
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  color: var(--text-secondary);
}

.notice.error,
.error-text {
  color: var(--error);
}

.notice.error {
  margin-bottom: 12px;
}

.pill {
  height: 22px;
  box-sizing: border-box;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 10px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 999px;
  color: var(--text-secondary);
  background: var(--bg-elevated);
  border: 1px solid var(--border-light);
}

.pill .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.pill.on {
  color: var(--success);
  background: color-mix(in srgb, var(--success) 14%, transparent);
  border-color: transparent;
}

.pill.off {
  color: var(--error);
  background: color-mix(in srgb, var(--error) 14%, transparent);
  border-color: transparent;
}

.label-line {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.row-label {
  font-size: 14px;
  font-weight: 500;
  line-height: 20px;
  color: var(--text);
}

.changed-badge {
  height: 18px;
  box-sizing: border-box;
  display: inline-flex;
  align-items: center;
  padding: 0 8px;
  font-size: 11px;
  font-weight: 600;
  color: var(--accent);
  background: var(--accent-muted);
  border-radius: 999px;
}

.link-btn {
  padding: 0;
  border: none;
  background: none;
  color: var(--accent);
  font: inherit;
  font-weight: 500;
  cursor: pointer;
}

.link-btn:hover:not(:disabled) {
  text-decoration: underline;
}

.link-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.switch {
  width: 44px;
  height: 24px;
  box-sizing: border-box;
  padding: 3px;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  border: none;
  border-radius: 999px;
  background: var(--border-light);
  cursor: pointer;
  transition: background var(--transition);
}

.switch.on {
  justify-content: flex-end;
  background: var(--accent);
}

.switch:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.knob {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #ffffff;
}

.switch:focus-visible,
.group-btn:focus-visible,
.bar-btn:focus-visible,
.btn:focus-visible,
.link-btn:focus-visible,
.stepper button:focus-visible,
.sub-summary:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.with-icon {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.with-icon.warn {
  color: var(--warning);
}

.input-group {
  height: 36px;
  box-sizing: border-box;
  display: inline-flex;
  align-items: stretch;
  max-width: 100%;
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  overflow: hidden;
}

.url {
  display: flex;
  align-items: center;
  min-width: 0;
  padding: 0 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 13px;
  color: var(--text);
  background: var(--bg);
}

.group-btn {
  flex: none;
  width: 96px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: none;
  border-left: 1px solid var(--border-light);
  background: var(--bg-elevated);
  color: var(--text);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}

.group-btn:hover {
  color: var(--accent);
}

.sub {
  border-top: 1px solid var(--border);
}

.sub-summary {
  min-height: 60px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 20px;
  cursor: pointer;
  list-style: none;
}

.sub-summary::-webkit-details-marker {
  display: none;
}

.sub-summary:hover {
  background: var(--bg-hover);
}

.sub-label {
  flex: 1;
  min-width: 0;
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
}

.sub-meta {
  font-size: 13px;
  color: var(--text-secondary);
}

.sub-chevron {
  flex-shrink: 0;
  color: var(--text-secondary);
  transition: transform var(--transition);
}

.sub[open] .sub-chevron {
  transform: rotate(90deg);
}

.sub-body {
  padding: 0 20px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.step {
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary);
}

.code-box {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}

.code-bar {
  height: 40px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 0 6px 0 14px;
  background: var(--bg-elevated);
  border-bottom: 1px solid var(--border);
}

.code-name {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  color: var(--text-secondary);
}

.bar-btn {
  width: 84px;
  height: 28px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text);
  background: var(--bg);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.bar-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
}

.code-block {
  margin: 0;
  padding: 14px;
  overflow-x: auto;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--text);
  background: var(--bg);
  user-select: all;
}

.tool-grid {
  display: grid;
  grid-template-columns: 140px minmax(0, 1fr);
  gap: 10px 16px;
  align-items: center;
}

.tool-kind {
  font-size: 13px;
  color: var(--text-secondary);
}

.tool-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tool-chip {
  height: 26px;
  box-sizing: border-box;
  display: inline-flex;
  align-items: center;
  padding: 0 8px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  color: var(--text);
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
}

.stepper {
  width: 140px;
  height: 36px;
  box-sizing: border-box;
  display: flex;
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  overflow: hidden;
}

.stepper button {
  width: 36px;
  flex: none;
  border: none;
  background: var(--bg-elevated);
  color: var(--text);
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
}

.stepper button:hover:not(:disabled) {
  color: var(--accent);
}

.stepper button:disabled {
  cursor: not-allowed;
  opacity: 0.35;
}

.stepper input {
  flex: 1;
  min-width: 0;
  border: none;
  border-left: 1px solid var(--border-light);
  border-right: 1px solid var(--border-light);
  background: var(--bg);
  color: var(--text);
  text-align: center;
  font:
    14px 'IBM Plex Mono',
    monospace;
}

.unit-input {
  width: 140px;
  height: 36px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  background: var(--bg);
  overflow: hidden;
}

.unit-input input {
  flex: 1;
  min-width: 0;
  height: 100%;
  border: none;
  background: transparent;
  color: var(--text);
  text-align: right;
  font:
    14px 'IBM Plex Mono',
    monospace;
  padding: 0 8px;
}

.unit {
  padding-right: 12px;
  font-size: 13px;
  color: var(--text-secondary);
}

.text-input {
  width: 260px;
  max-width: 100%;
  height: 36px;
  box-sizing: border-box;
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  background: var(--bg);
  color: var(--text);
  font:
    13px 'IBM Plex Mono',
    monospace;
  padding: 0 12px;
}

/* No spinner arrows: the stepper and the unit say what the number is. */
input[type='number']::-webkit-inner-spin-button,
input[type='number']::-webkit-outer-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

input[type='number'] {
  -moz-appearance: textfield;
  appearance: textfield;
}

.stepper input:focus-visible,
.unit-input:focus-within,
.text-input:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: -2px;
}

.stepper input:disabled,
.unit-input input:disabled,
.text-input:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.budget-footer {
  min-height: 60px;
  box-sizing: border-box;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px 24px;
  padding: 12px 20px;
  border-top: 1px solid var(--border);
  background: var(--bg-elevated);
}

.footer-note {
  flex: 1 1 260px;
  font-size: 13px;
  color: var(--text-secondary);
}

.footer-note.dirty {
  color: var(--accent);
}

.footer-actions {
  display: flex;
  gap: 8px;
}

.btn {
  height: 36px;
  padding: 0 14px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text);
  background: transparent;
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  cursor: pointer;
}

.btn:hover:not(:disabled) {
  border-color: var(--accent);
  color: var(--accent);
}

.btn.primary {
  padding: 0 18px;
  font-weight: 600;
  color: #0a0a0b;
  background: var(--accent);
  border-color: var(--accent);
}

.btn.primary:hover:not(:disabled) {
  color: #0a0a0b;
  background: var(--accent-hover);
}

.btn:disabled {
  cursor: not-allowed;
  opacity: 0.4;
}

.advanced-body {
  padding: 4px 20px 16px;
}

.env-wrap {
  overflow-x: auto;
}

.env-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.env-table th {
  height: 40px;
  padding: 0 16px;
  text-align: left;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border);
}

.env-table td {
  height: 44px;
  padding: 0 16px;
  border-bottom: 1px solid var(--border);
}

.env-table th:first-child,
.env-table td:first-child {
  padding-left: 0;
}

.env-table tr:last-child td {
  border-bottom: none;
}

.mono {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12.5px;
  color: var(--text);
}

.effect {
  color: var(--text-secondary);
}

.procedure {
  margin: 12px 0 0;
  font-size: 13px;
  color: var(--text-secondary);
}
</style>
