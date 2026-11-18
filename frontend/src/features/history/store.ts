import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { AnalysisSummary } from '../../shared/types'
import * as api from './api'

export const useHistoryStore = defineStore('history', () => {
  const analyses = ref<AnalysisSummary[]>([])
  const error = ref<string | null>(null)

  async function load(): Promise<void> {
    try {
      error.value = null
      analyses.value = await api.fetchHistory()
    } catch (e) {
      error.value = (e as Error).message || 'Failed to load history'
      console.error('Failed to load history', e)
    }
  }

  async function remove(id: string): Promise<void> {
    try {
      await api.deleteHistoryEntry(id)
      analyses.value = analyses.value.filter((a) => a.id !== id)
    } catch (e) {
      error.value = (e as Error).message || 'Failed to delete analysis'
      console.error('Failed to delete analysis', e)
    }
  }

  return { analyses, error, load, remove }
})
