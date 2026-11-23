import { defineStore } from 'pinia'
import { ref, watch, watchEffect } from 'vue'
import type { Locale, Theme } from '../../shared/types'
import { appLocale } from '../../shared/appConfig'
import { STORAGE_KEYS } from '../../shared/storage/keys'

function readStorageItem(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function writeStorageItem(key: string, value: string): void {
  try {
    localStorage.setItem(key, value)
  } catch {
    // localStorage unavailable (private browsing, quota exceeded)
  }
}

export const useSettingsStore = defineStore('settings', () => {
  const theme = ref<Theme>((readStorageItem(STORAGE_KEYS.theme) as Theme) || 'dark')
  const locale = ref<Locale>((readStorageItem(STORAGE_KEYS.locale) as Locale) || 'fr')

  watch(theme, (v) => writeStorageItem(STORAGE_KEYS.theme, v))
  watch(
    locale,
    (v) => {
      writeStorageItem(STORAGE_KEYS.locale, v)
      appLocale.value = v
    },
    { immediate: true },
  )

  watchEffect(() => {
    document.documentElement.classList.toggle('light', theme.value === 'light')
  })

  function setTheme(t: Theme): void {
    theme.value = t
  }
  function setLocale(l: Locale): void {
    locale.value = l
  }

  return { theme, locale, setTheme, setLocale }
})
