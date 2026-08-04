<template>
  <!-- eslint-disable-next-line vue/no-v-html -- sanitized by DOMPurify -->
  <div class="markdown-viewer" v-html="rendered" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { useI18n } from '../../../shared/i18n'

const props = defineProps({ content: String })
const { t } = useI18n()

const rendered = computed(() => {
  if (!props.content) return `<p class="empty">${t('results.noMarkdown')}</p>`
  // marked emits bare `<table>` blocks. Wrap each one in a scroll
  // container so wide tables scroll horizontally inside narrow panels
  // instead of squashing or overflowing the layout. Wrapping happens
  // before sanitize so DOMPurify still validates the final markup.
  const html = (marked.parse(props.content) as string)
    .replace(/<table>/g, '<div class="md-table"><table>')
    .replace(/<\/table>/g, '</table></div>')
  return DOMPurify.sanitize(html)
})
</script>

<style scoped>
.markdown-viewer {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text);
}

.markdown-viewer :deep(h1),
.markdown-viewer :deep(h2),
.markdown-viewer :deep(h3) {
  color: var(--text);
  margin: 24px 0 12px;
  font-weight: 600;
}

.markdown-viewer :deep(h1) {
  font-size: 24px;
}
.markdown-viewer :deep(h2) {
  font-size: 20px;
}
.markdown-viewer :deep(h3) {
  font-size: 16px;
}

.markdown-viewer :deep(p) {
  margin: 8px 0;
}

.markdown-viewer :deep(code) {
  background: var(--bg-elevated);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'IBM Plex Mono', monospace;
  font-size: 13px;
}

.markdown-viewer :deep(pre) {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 16px;
  overflow-x: auto;
  margin: 12px 0;
}

.markdown-viewer :deep(pre code) {
  background: none;
  padding: 0;
}

/* Tables — card-framed, horizontally scrollable, zebra rows. The
   `.md-table` wrapper is injected around every `<table>` in `rendered`. */
.markdown-viewer :deep(.md-table) {
  margin: 14px 0;
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg-surface);
}

.markdown-viewer :deep(table) {
  border-collapse: collapse;
  width: 100%;
  font-size: 12px;
  line-height: 1.45;
}

.markdown-viewer :deep(thead th) {
  background: var(--bg-elevated);
  color: var(--text-secondary);
  font-weight: 600;
  font-size: 10px;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  text-align: left;
  white-space: nowrap;
  padding: 9px 14px;
  border-bottom: 1px solid var(--border-light);
}

.markdown-viewer :deep(tbody td) {
  padding: 8px 14px;
  text-align: left;
  vertical-align: top;
  color: var(--text);
  border-bottom: 1px solid var(--border);
}

.markdown-viewer :deep(tbody td:first-child) {
  font-weight: 500;
}

.markdown-viewer :deep(tbody tr:nth-child(even)) {
  background: var(--bg-elevated);
}

.markdown-viewer :deep(tbody tr:hover) {
  background: var(--bg-hover);
}

.markdown-viewer :deep(tbody tr:last-child td) {
  border-bottom: none;
}

.markdown-viewer :deep(img) {
  max-width: 100%;
  border-radius: var(--radius-sm);
}

.markdown-viewer :deep(.empty) {
  color: var(--text-muted);
  text-align: center;
  padding: 40px;
}
</style>
