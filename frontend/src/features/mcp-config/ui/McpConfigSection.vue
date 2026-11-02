<template>
  <AccordionSection id="mcp" :title="t('settings.mcp.title')" data-e2e="mcp-config-section">
    <template #status>
      <span v-if="state" class="state-badge" :class="state">
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
            <span class="row-label">{{ t('settings.mcp.title') }}</span>
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
              <svg v-bind="icon(14)">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
              {{ localOnly ? t('settings.mcp.localOnly') : t('settings.mcp.unauthenticated') }}
            </span>
            <span v-if="!hostOk" class="error-text" data-e2e="mcp-config-host-warning">
              {{ t('settings.mcp.hostWarning', { host }) }}
            </span>
          </template>
          <code class="url" data-e2e="mcp-config-url">{{ clientUrl }}</code>
          <button
            type="button"
            class="icon-btn"
            :aria-label="t('settings.mcp.copyUrl')"
            :title="copyLabel('url')"
            data-e2e="mcp-config-copy-url"
            @click="copy('url', clientUrl)"
          >
            <svg v-if="copied === 'url'" v-bind="icon(15)"><path d="M20 6 9 17l-5-5" /></svg>
            <svg v-else v-bind="icon(15)">
              <rect x="9" y="9" width="13" height="13" rx="2" />
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
            </svg>
          </button>
        </AccordionRow>

        <details class="sub">
          <summary class="sub-summary">
            <span class="row-label">{{ t('settings.mcp.connectDesktop') }}</span>
            <svg class="sub-chevron" v-bind="icon(16)"><path d="m9 18 6-6-6-6" /></svg>
          </summary>
          <div class="sub-body">
            <p class="step">
              1. {{ t('settings.mcp.desktopStep') }} <code>claude_desktop_config.json</code>
            </p>
            <div class="code-wrap">
              <button
                type="button"
                class="copy-btn"
                data-e2e="mcp-config-copy-desktop"
                @click="copy('desktop', desktopJson)"
              >
                {{ copyLabel('desktop') }}
              </button>
              <pre class="code-block" data-e2e="mcp-config-desktop-json">{{ desktopJson }}</pre>
            </div>
            <p class="step">2. {{ t('settings.mcp.desktopHint') }}</p>
          </div>
        </details>

        <details class="sub">
          <summary class="sub-summary">
            <span class="row-label">{{ t('settings.mcp.connectCode') }}</span>
            <svg class="sub-chevron" v-bind="icon(16)"><path d="m9 18 6-6-6-6" /></svg>
          </summary>
          <div class="sub-body">
            <p class="step">{{ t('settings.mcp.codeStep') }}</p>
            <div class="code-wrap">
              <button
                type="button"
                class="copy-btn"
                data-e2e="mcp-config-copy-code"
                @click="copy('code', codeCmd)"
              >
                {{ copyLabel('code') }}
              </button>
              <pre class="code-block" data-e2e="mcp-config-code-cmd">{{ codeCmd }}</pre>
            </div>
          </div>
        </details>

        <details class="sub">
          <summary class="sub-summary">
            <span class="row-label">{{ t('settings.mcp.published') }}</span>
            <span class="sub-meta">
              {{ publishedSummary }}
              <svg class="sub-chevron" v-bind="icon(16)"><path d="m9 18 6-6-6-6" /></svg>
            </span>
          </summary>
          <div class="sub-body" data-e2e="mcp-config-tools">
            <div v-for="group in toolGroups" :key="group.key" class="tool-row">
              <span class="tool-kind">{{ t(group.label) }}</span>
              <span v-for="name in group.names" :key="name" class="tool-chip">{{ name }}</span>
            </div>
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
      <template #hint>{{ budgetHint('maxRounds', t('settings.mcp.maxRoundsShort')) }}</template>
      <div class="stepper">
        <button
          type="button"
          :aria-label="t('settings.mcp.fewerRounds')"
          :disabled="store.view.readOnly"
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
          :disabled="store.view.readOnly"
          @click="store.stepRounds(1)"
        >
          +
        </button>
      </div>
      <button
        v-if="differs('maxRounds')"
        type="button"
        class="icon-btn revert"
        :aria-label="t('settings.mcp.revert')"
        :title="t('settings.mcp.revert')"
        :disabled="store.view.readOnly"
        data-e2e="mcp-config-revert-max-rounds"
        @click="store.revert('maxRounds')"
      >
        <svg v-bind="icon(15)">
          <path d="M3 12a9 9 0 1 0 3-6.7" />
          <path d="M3 4v5h5" />
        </svg>
      </button>
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
        {{ budgetHint('maxReadTokens', t('settings.mcp.maxReadTokensHint')) }}
      </template>
      <span class="unit-input">
        <input
          id="mcp-max-read-tokens"
          v-model.number="store.form.maxReadTokens"
          type="number"
          :min="READ_TOKENS_MIN"
          :max="READ_TOKENS_MAX"
          :disabled="store.view.readOnly"
          data-e2e="mcp-config-max-read-tokens"
        />
        <span class="unit">{{ t('settings.mcp.tokensUnit') }}</span>
      </span>
      <button
        v-if="differs('maxReadTokens')"
        type="button"
        class="icon-btn revert"
        :aria-label="t('settings.mcp.revert')"
        :title="t('settings.mcp.revert')"
        :disabled="store.view.readOnly"
        data-e2e="mcp-config-revert-max-read-tokens"
        @click="store.revert('maxReadTokens')"
      >
        <svg v-bind="icon(15)">
          <path d="M3 12a9 9 0 1 0 3-6.7" />
          <path d="M3 4v5h5" />
        </svg>
      </button>
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
      <template #hint>{{ budgetHint('studioBaseUrl', t('settings.mcp.baseUrlHint')) }}</template>
      <input
        id="mcp-base-url"
        v-model="store.form.studioBaseUrl"
        class="text-input"
        type="text"
        :disabled="store.view.readOnly"
        data-e2e="mcp-config-base-url"
        spellcheck="false"
      />
      <button
        v-if="differs('studioBaseUrl')"
        type="button"
        class="icon-btn revert"
        :aria-label="t('settings.mcp.revert')"
        :title="t('settings.mcp.revert')"
        :disabled="store.view.readOnly"
        data-e2e="mcp-config-revert-base-url"
        @click="store.revert('studioBaseUrl')"
      >
        <svg v-bind="icon(15)">
          <path d="M3 12a9 9 0 1 0 3-6.7" />
          <path d="M3 4v5h5" />
        </svg>
      </button>
    </AccordionRow>

    <div v-if="store.saveError" class="notice error" data-e2e="mcp-config-save-error">
      {{ store.saveError }}
    </div>

    <div class="budget-footer">
      <span class="footer-note">
        {{ t('settings.mcp.liveHint') }} {{ t('settings.mcp.maxRoundsHint') }}
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

  <AccordionSection v-if="store.server" id="mcp-advanced" :title="t('settings.mcp.advanced')">
    <template #status>
      <span class="header-note">
        {{ t('settings.mcp.advancedSummary', { n: restartOnly.length }) }}
      </span>
    </template>
    <div class="advanced-body">
      <div class="env-wrap">
        <table class="env-table" data-e2e="mcp-config-restart-only">
          <tbody>
            <tr v-for="row in restartOnly" :key="row.name">
              <td class="mono">{{ row.name }}</td>
              <td class="mono">{{ row.value }}</td>
              <td class="effect">{{ row.effect }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <ol class="procedure">
        <li>{{ t('settings.mcp.restartStep1') }}</li>
        <li>{{ t('settings.mcp.restartStep2') }}</li>
        <li>{{ t('settings.mcp.restartStep3') }}</li>
      </ol>
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

/** Only loopback hosts are allowed: the server is out of reach of other machines. */
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

/** The row's hint, plus the environment's value while the field departs from it. */
function budgetHint(field: McpBudgetField, hint: string): string {
  const defaults = store.view?.defaults
  if (!defaults || !differs(field)) return hint
  const value = defaults[field] === '' ? t('settings.mcp.envNone') : String(defaults[field])
  return `${hint} · ${t('settings.mcp.envValue', { value })}`
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
.notice {
  margin: 12px 16px 0;
  font-size: 13px;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  color: var(--text-secondary);
}

.notice.error,
.error-text {
  color: var(--error);
}

.error-text {
  font-size: 13px;
}

.state-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.state-badge .dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--text-secondary);
}

.state-badge.on {
  color: var(--success);
}

.state-badge.on .dot {
  background: var(--success);
}

.state-badge.off .dot {
  background: var(--error);
}

.header-note {
  font-size: 13px;
  font-weight: 400;
  color: var(--text-secondary);
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
  color: var(--text);
}

.changed-badge {
  font-size: 11px;
  font-weight: 600;
  color: var(--accent);
  background: var(--accent-muted);
  border-radius: 999px;
  padding: 1px 8px;
}

.switch {
  width: 48px;
  height: 28px;
  padding: 3px;
  display: flex;
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

.switch:focus-visible,
.icon-btn:focus-visible,
.btn:focus-visible,
.copy-btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.knob {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #ffffff;
}

.with-icon {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.with-icon.warn {
  color: var(--warning);
}

.url {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 13px;
  color: var(--text);
  word-break: break-all;
}

.icon-btn {
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--text);
  background: var(--bg-elevated);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.icon-btn:hover:not(:disabled) {
  color: var(--accent);
  border-color: var(--accent);
}

.icon-btn.revert {
  color: var(--accent);
  background: transparent;
}

.icon-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.sub {
  border-top: 1px solid var(--border);
}

.sub-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  cursor: pointer;
  list-style: none;
}

.sub-summary::-webkit-details-marker {
  display: none;
}

.sub-summary:hover {
  background: var(--bg-hover);
}

.sub-meta {
  display: inline-flex;
  align-items: center;
  gap: 10px;
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
  padding: 0 16px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.step {
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary);
}

.step code {
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12px;
  color: var(--text);
}

.code-wrap {
  position: relative;
}

.code-block {
  margin: 0;
  padding: 14px 96px 14px 14px;
  overflow-x: auto;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 12.5px;
  line-height: 1.55;
  color: var(--text);
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  user-select: all;
}

.copy-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  min-height: 32px;
  padding: 0 12px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text);
  background: var(--bg-elevated);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.copy-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
}

.tool-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.tool-kind {
  color: var(--text-secondary);
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

.stepper {
  display: inline-flex;
  align-items: stretch;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.stepper button {
  width: 40px;
  height: 38px;
  border: none;
  background: var(--bg-elevated);
  color: var(--text);
  font-size: 16px;
  cursor: pointer;
}

.stepper button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.stepper input {
  width: 56px;
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
  display: inline-flex;
  align-items: center;
  height: 38px;
  box-sizing: border-box;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  background: var(--bg);
  padding-right: 12px;
}

.unit-input input {
  width: 80px;
  height: 36px;
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
  font-size: 13px;
  color: var(--text-secondary);
}

.text-input {
  width: 240px;
  max-width: 100%;
  height: 38px;
  box-sizing: border-box;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  background: var(--bg);
  color: var(--text);
  font:
    13px 'IBM Plex Mono',
    monospace;
  padding: 0 12px;
}

.stepper input:disabled,
.unit-input input:disabled,
.text-input:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.budget-footer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  border-top: 1px solid var(--border);
  background: var(--bg-elevated);
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
}

.footer-note {
  flex: 1 1 280px;
  font-size: 12.5px;
  color: var(--text-secondary);
}

.footer-actions {
  display: flex;
  gap: 8px;
}

.btn {
  min-height: 38px;
  padding: 0 14px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  background: transparent;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.btn.primary {
  padding: 0 18px;
  font-weight: 600;
  color: #0a0a0b;
  background: var(--accent);
  border-color: var(--accent);
}

.btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.advanced-body {
  padding: 4px 16px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.env-wrap {
  overflow-x: auto;
}

.env-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.env-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
}

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
  word-break: break-all;
}

.effect {
  color: var(--text-secondary);
}

.procedure {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
  color: var(--text-secondary);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
</style>
