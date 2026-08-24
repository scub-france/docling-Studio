<template>
  <ComingSoonShell
    :title="t('comingSoon.title')"
    :subtitle="t('comingSoon.subtitle.runDetail')"
    :hint="hint"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from '../shared/i18n'

import ComingSoonShell from '@/shared/ui/ComingSoonShell.vue'

const props = defineProps<{ id: string }>()

const { t } = useI18n()

const hint = computed(() => t('comingSoon.hint.runDetail', { id: props.id }))
</script>
