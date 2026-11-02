<template>
  <section class="acc-section">
    <h2 class="acc-heading">
      <button
        type="button"
        class="acc-toggle"
        :aria-expanded="open"
        :aria-controls="bodyId"
        :data-e2e="`settings-group-${id}-toggle`"
        @click="accordion?.toggle(id)"
      >
        <span class="acc-title">{{ title }}</span>
        <span v-if="!open && summary" class="acc-summary">{{ summary }}</span>
        <slot name="status" />
        <svg
          class="acc-chevron"
          :class="{ open }"
          aria-hidden="true"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="m9 18 6-6-6-6" />
        </svg>
      </button>
    </h2>
    <div v-show="open" :id="bodyId" class="acc-body" :data-e2e="`settings-group-${id}`">
      <slot />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, inject, onBeforeUnmount, onMounted } from 'vue'
import { ACCORDION_KEY } from './accordion'

/**
 * One foldable section of an accordion. Its open state comes from the
 * accordion its page provides; outside one it is simply always open.
 * The body stays in the page when folded, so a form keeps its edits.
 *
 * The header reads: title, then the one-line summary while folded, then
 * the `status` slot (a pill, shown either way), then the chevron.
 */
const props = defineProps<{
  /** Stable id: the key the fold is remembered under. */
  id: string
  title: string
  /** One line shown in the header while the section is folded. */
  summary?: string
}>()

const accordion = inject(ACCORDION_KEY, null)
const open = computed(() => accordion?.isOpen(props.id) ?? true)
const bodyId = computed(() => `acc-body-${props.id}`)

onMounted(() => accordion?.register(props.id))
onBeforeUnmount(() => accordion?.unregister(props.id))
</script>

<style scoped>
.acc-section {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.acc-heading {
  margin: 0;
}

.acc-toggle {
  width: 100%;
  height: 56px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 20px;
  background: transparent;
  border: none;
  color: var(--text);
  font: inherit;
  font-size: 15px;
  font-weight: 600;
  text-align: left;
  cursor: pointer;
}

.acc-toggle:hover {
  background: var(--bg-hover);
}

.acc-toggle:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: -2px;
}

.acc-title {
  flex: 1;
  min-width: 0;
}

.acc-summary {
  font-size: 13px;
  font-weight: 400;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.acc-chevron {
  flex-shrink: 0;
  color: var(--text-secondary);
  transition: transform var(--transition);
}

.acc-chevron.open {
  transform: rotate(90deg);
}

.acc-body {
  border-top: 1px solid var(--border);
}
</style>
