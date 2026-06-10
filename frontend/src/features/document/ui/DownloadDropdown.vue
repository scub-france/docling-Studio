<template>
  <div class="download-dropdown" ref="dropdownRef">
    <button
      type="button"
      :class="['download-btn', buttonClass]"
      title="Download"
      data-e2e="download-btn"
      @click="toggle"
    >
      ↓ Download
    </button>
    <div v-if="open" class="dropdown-menu" :class="`dropdown-menu--${direction}`">
      <a :href="getExportUrl(docId, 'pdf')" class="dropdown-item" download>
        PDF Document
      </a>
      <a :href="getExportUrl(docId, 'md')" class="dropdown-item" download>
        Markdown
      </a>
      <a
        href="#"
        class="dropdown-item"
        @click.prevent="downloadFormat('json')"
      >
        Docling JSON
      </a>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { getExportUrl } from '../api'

const props = withDefaults(defineProps<{
  docId: string
  buttonClass?: string
  direction?: 'up' | 'down'
}>(), {
  direction: 'down'
})

const open = ref(false)
const dropdownRef = ref<HTMLElement | null>(null)

function toggle() {
  open.value = !open.value
}

function close() {
  open.value = false
}

async function downloadFormat(format: 'pdf' | 'md' | 'json') {
  try {
    const url = getExportUrl(props.docId, format)
    const response = await fetch(url)
    
    if (!response.ok) {
      if (response.status === 404 && format === 'json') {
        window.alert('Docling JSON is not available. Please reparse the document.')
      } else {
        window.alert(`Failed to download ${format} format.`)
      }
      return
    }

    // Trigger download programmatic
    const blob = await response.blob()
    const downloadUrl = window.URL.createObjectURL(blob)
    
    // Read filename from Content-Disposition header if available
    let filename = `${props.docId}.${format}`
    const disposition = response.headers.get('content-disposition')
    if (disposition && disposition.indexOf('attachment') !== -1) {
      const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/
      const matches = filenameRegex.exec(disposition)
      if (matches != null && matches[1]) { 
        filename = matches[1].replace(/['"]/g, '')
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
    window.alert(`An error occurred while downloading the ${format} format.`)
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
  padding: 6px 12px;
  font-size: 12px;
  color: var(--text);
  text-decoration: none;
  transition: background var(--transition);
  display: block;
}

.dropdown-item:hover {
  background: var(--bg-hover);
  color: var(--accent);
}
</style>