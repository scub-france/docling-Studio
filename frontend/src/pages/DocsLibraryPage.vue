<template>
  <div>
    <div v-if="showFlashAllModesDisabled" class="flash flash--warning" role="alert">
      {{ t('flags.allModesDisabled') }}
    </div>
    <ComingSoonShell
      :title="t('comingSoon.title')"
      :subtitle="t('comingSoon.subtitle.docsLibrary')"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import { useI18n } from '../shared/i18n'
import ComingSoonShell from '../shared/ui/ComingSoonShell.vue'

const { t } = useI18n()
const route = useRoute()

// Surfaced when the router redirected here because every doc workspace
// mode is feature-flagged off (#210). #211 will replace this with a
// proper banner inside the library page.
const showFlashAllModesDisabled = computed(() => route.query.reason === 'no-mode-enabled')
</script>

<style scoped>
.flash {
  margin: 1rem;
  padding: 0.75rem 1rem;
  border-radius: 6px;
  font-size: 0.875rem;
  color: #92400e;
  background: #fef3c7;
  border: 1px solid #fde68a;
}
</style>
