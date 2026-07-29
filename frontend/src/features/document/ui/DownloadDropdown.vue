<template>
  <div class="download-dropdown" ref="dropdownRef">
    <button
      ref="buttonRef"
      type="button"
      :class="['download-btn', buttonClass, { 'download-btn--icon': iconOnly }]"
      :title="t('docs.download')"
      :aria-expanded="open ? 'true' : 'false'"
      aria-haspopup="menu"
      :aria-controls="menuId"
      data-e2e="download-btn"
      @click="toggle"
      @keydown.down.prevent="openAndFocus(0)"
      @keydown.up.prevent="openAndFocus(downloadOptions.length - 1)"
      @keydown.enter.prevent="toggle"
      @keydown.esc.prevent="close"
    >
      <svg v-if="iconOnly" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 3v12m0 0 4-4m-4 4-4-4M5 19h14" />
      </svg>
      <span v-else>{{ t('docs.download') }}</span>
    </button>
    <div
      v-if="open"
      :id="menuId"
      class="dropdown-menu"
      :class="`dropdown-menu--${direction}`"
      role="menu"
      :aria-label="t('docs.download')"
      @keydown.esc.prevent="closeAndFocusTrigger"
      @keydown.down.prevent="focusNextItem"
      @keydown.up.prevent="focusPreviousItem"
      @keydown.home.prevent="focusItem(0)"
      @keydown.end.prevent="focusItem(downloadOptions.length - 1)"
    >
      <button
        v-for="(option, index) in downloadOptions"
        :key="option.format"
        :ref="(el) => setMenuItemRef(el, index)"
        type="button"
        class="dropdown-item"
        role="menuitem"
        @click="downloadFormat(option.format)"
      >
        {{ t(option.labelKey) }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref } from 'vue'
import type { ComponentPublicInstance } from 'vue'

import { useI18n } from '../../../shared/i18n'
import { getExportUrl } from '../api'

type ExportFormat = 'pdf' | 'md' | 'json'

const props = withDefaults(
  defineProps<{
    docId: string
    buttonClass?: string
    iconOnly?: boolean
    pdfOnly?: boolean
    direction?: 'up' | 'down'
  }>(),
  {
    direction: 'down',
  },
)

const { t } = useI18n()
const open = ref(false)
const dropdownRef = ref<HTMLElement | null>(null)
const buttonRef = ref<HTMLButtonElement | null>(null)
const itemRefs = ref<Array<HTMLButtonElement | null>>([])
const menuId = `download-menu-${props.docId}`

const allDownloadOptions: Array<{ format: ExportFormat; labelKey: string }> = [
  { format: 'pdf', labelKey: 'docs.downloadPdf' },
  { format: 'md', labelKey: 'docs.downloadMarkdown' },
  { format: 'json', labelKey: 'docs.downloadJson' },
]
const downloadOptions = props.pdfOnly ? allDownloadOptions.slice(0, 1) : allDownloadOptions

function toggle() {
  if (open.value) {
    close()
    return
  }
  void openAndFocus(0)
}

function close() {
  open.value = false
}

function closeAndFocusTrigger() {
  close()
  buttonRef.value?.focus()
}

function setMenuItemRef(el: Element | ComponentPublicInstance | null, index: number) {
  itemRefs.value[index] = el instanceof HTMLButtonElement ? el : null
}

async function openAndFocus(index: number) {
  open.value = true
  await nextTick()
  focusItem(index)
}

function focusItem(index: number) {
  itemRefs.value[index]?.focus()
}

function focusNextItem() {
  const index = itemRefs.value.findIndex((item) => item === document.activeElement)
  focusItem((index + 1 + downloadOptions.length) % downloadOptions.length)
}

function focusPreviousItem() {
  const index = itemRefs.value.findIndex((item) => item === document.activeElement)
  focusItem((index - 1 + downloadOptions.length) % downloadOptions.length)
}

async function downloadFormat(format: ExportFormat) {
  try {
    const url = getExportUrl(props.docId, format)
    const response = await fetch(url)

    if (!response.ok) {
      if (response.status === 404 && format === 'json') {
        window.alert(t('docs.downloadJsonUnavailable'))
      } else {
        window.alert(t('docs.downloadFailed', { format: t(formatLabelKey(format)) }))
      }
      close()
      return
    }

    const blob = await response.blob()
    const downloadUrl = window.URL.createObjectURL(blob)

    let filename = `${props.docId}.${format}`
    const disposition = response.headers.get('content-disposition')
    if (disposition?.includes('attachment')) {
      const utf8FilenameRegex = /filename\*=utf-8''([^;\n]+)/i
      const utf8Match = utf8FilenameRegex.exec(disposition)
      if (utf8Match?.[1]) {
        filename = decodeURIComponent(utf8Match[1])
      } else {
        const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/
        const matches = filenameRegex.exec(disposition)
        if (matches?.[1]) {
          filename = matches[1].replace(/['"]/g, '')
        }
      }
    }

    const a = document.createElement('a')
    a.style.display = 'none'
    a.href = downloadUrl
    a.download = filename
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(downloadUrl)
    document.body.removeChild(a)
    close()
  } catch (err) {
    console.error('Download error:', err)
    window.alert(t('docs.downloadUnexpectedError', { format: t(formatLabelKey(format)) }))
    close()
  }
}

function formatLabelKey(format: ExportFormat): string {
  switch (format) {
    case 'pdf':
      return 'docs.downloadPdf'
    case 'md':
      return 'docs.downloadMarkdown'
    case 'json':
      return 'docs.downloadJson'
  }
}

function onClickOutside(event: MouseEvent) {
  if (dropdownRef.value && !dropdownRef.value.contains(event.target as Node)) {
    close()
  }
}

onMounted(() => {
  document.addEventListener('click', onClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', onClickOutside)
})
</script>

<style scoped>
.download-dropdown {
  position: relative;
  display: inline-block;
}

.download-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  font-size: 12px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition);
}

.download-btn--icon {
  width: 32px;
  height: 32px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  background: transparent;
  color: var(--text-muted);
}
.download-btn--icon:hover {
  color: var(--accent);
  background: transparent;
}
.download-btn--icon svg {
  width: 17px;
  height: 17px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.download-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
}

.dropdown-menu {
  position: absolute;
  right: 0;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  min-width: 140px;
  z-index: 50;
  display: flex;
  flex-direction: column;
  padding: 4px 0;
}

.dropdown-menu--down {
  top: 100%;
  margin-top: 4px;
}

.dropdown-menu--up {
  bottom: 100%;
  margin-bottom: 4px;
}

.dropdown-item {
  width: 100%;
  padding: 6px 12px;
  font-size: 12px;
  text-align: left;
  color: var(--text);
  background: transparent;
  border: 0;
  transition: background var(--transition);
  display: block;
  cursor: pointer;
}

.dropdown-item:hover,
.dropdown-item:focus-visible {
  background: var(--bg-hover);
  color: var(--accent);
  outline: none;
}
</style>
