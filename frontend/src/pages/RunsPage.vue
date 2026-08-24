<template>
  <ComingSoonShell :title="t('comingSoon.title')" :subtitle="t('comingSoon.subtitle.runs')" />
</template>

<script setup lang="ts">
import { useI18n } from '../shared/i18n'

import ComingSoonShell from '@/shared/ui/ComingSoonShell.vue'

const { t } = useI18n()
</script>
