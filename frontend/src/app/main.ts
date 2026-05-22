import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { router } from './router'
import { useFeatureFlagStore } from '../features/feature-flags'
import App from './App.vue'

const app = createApp(App)
app.use(createPinia())
app.use(router)

// Surface flags (#257) gate the router's `beforeEach` guard: when
// `studioModeEnabled` is false the legacy /studio surface is redirected
// to /docs. The store's defaults are returned until `/api/health`
// resolves, so mounting before the first load() completes raced the
// first navigation into a redirect even when the backend had the
// surface enabled — visible in the e2e UI suite when
// STUDIO_MODE_ENABLED=true at the server but the page lands on /docs
// anyway.
//
// Wait for either /api/health to resolve OR a short timeout, whichever
// comes first. `apiFetch` has no built-in timeout, so the race protects
// the boot from a hanging backend (3 s is well above a healthy LAN
// p99 and still acceptable as worst-case first-paint). The store's
// catch flips `loaded` to true on HTTP errors, so on the happy path
// (fast 200) we mount with real flags; on the slow / failure path we
// mount with safe defaults.
const HEALTH_BOOT_TIMEOUT_MS = 3000
const featureFlags = useFeatureFlagStore()
const healthTimeout = new Promise<void>((resolve) => setTimeout(resolve, HEALTH_BOOT_TIMEOUT_MS))
Promise.race([featureFlags.load(), healthTimeout]).finally(() => app.mount('#app'))
