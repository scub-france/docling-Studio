<template>
  <ComingSoonShell
    :title="t('comingSoon.title')"
    :subtitle="t('comingSoon.subtitle.docWorkspace')"
    :hint="hint"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'

import { useCrumbs } from '../shared/breadcrumb/store'
import { truncate } from '../shared/breadcrumb/text'
import type { Crumb } from '../shared/breadcrumb/types'
import { useI18n } from '../shared/i18n'
import { type DocMode } from '../shared/routing/modes'
import { ROUTES } from '../shared/routing/names'
import ComingSoonShell from '../shared/ui/ComingSoonShell.vue'

/**
 * Doc workspace placeholder. Receives the doc id (from `:id` path param)
 * and the resolved mode (from `?mode=` query param, parsed by the
 * router via `parseMode`). The full workspace is built by #216 (E4)
 * on top of #218-#224 (E5 chunks editor).
 */
const props = defineProps<{ id: string; mode: DocMode }>()

const { t } = useI18n()

const hint = computed(() => t('comingSoon.hint.docWorkspace', { id: props.id, mode: props.mode }))

// Provide the breadcrumb segments. Once the doc is fetched (E4 / #216),
// `truncate(doc.filename, 40)` will replace the id; for now we render
// the id itself so the user can still see what they are looking at.
const crumbs = computed<Crumb[]>(() => [
  { kind: 'link', label: t('breadcrumb.studio'), to: { name: ROUTES.HOME } },
  {
    kind: 'link',
    label: truncate(props.id, 40),
    to: { name: ROUTES.DOC_WORKSPACE, params: { id: props.id } },
  },
  { kind: 'leaf', label: t(`breadcrumb.mode.${props.mode}`) },
])
useCrumbs(crumbs)
</script>
