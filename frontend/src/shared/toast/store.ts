import { defineStore } from 'pinia'
import { ref } from 'vue'

export type ToastLevel = 'info' | 'warning' | 'error' | 'success'

export interface ToastItem {
  id: number
  level: ToastLevel
  message: string
  detail?: string | null
}

let nextToastId = 1

export const useToastStore = defineStore('toast', () => {
  const items = ref<ToastItem[]>([])

  function push(
    level: ToastLevel,
    message: string,
    timeoutMs = 6000,
    detail: string | null = null,
  ): number {
    const id = nextToastId++
    items.value.push({ id, level, message, detail })
    if (timeoutMs > 0) {
      setTimeout(() => dismiss(id), timeoutMs)
    }
    return id
  }

  function dismiss(id: number): void {
    items.value = items.value.filter((item) => item.id !== id)
  }

  function clear(): void {
    items.value = []
  }

  return { items, push, dismiss, clear }
})
