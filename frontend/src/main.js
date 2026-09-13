import { createApp } from 'vue'
import { createPinia } from 'pinia'
import VueApexCharts from 'vue3-apexcharts'
import App from './App.vue'
import router from './router/index.js'

// ── Recover from a deploy that happened while the app was open ───────────
//
// Vite fingerprints every chunk, and a new build DELETES the previous ones. A
// browser still holding an older `index-*.js` then asks for a chunk that no
// longer exists: live, `WorkspaceView-4chdrjoW.css` returned 404 while its
// entry bundle still returned 200, so the workspace rendered with no styles at
// all and nothing in the UI said why.
//
// Vite fires `vite:preloadError` when a dynamic import fails. Reloading picks
// up the current index.html and its matching chunks. The session flag stops a
// reload loop if the asset is genuinely gone rather than merely stale — one
// attempt, then let the error surface.
const RELOAD_FLAG = 'chunk-reload-at'

function recoverFromStaleChunk() {
  let last = 0
  try {
    last = Number(sessionStorage.getItem(RELOAD_FLAG) || 0)
  } catch (_) { /* private mode — treat as first attempt */ }

  if (Date.now() - last < 15000) return false   // already tried; don't loop
  try {
    sessionStorage.setItem(RELOAD_FLAG, String(Date.now()))
  } catch (_) { /* ignore */ }

  window.location.reload()
  return true
}

window.addEventListener('vite:preloadError', (event) => {
  if (recoverFromStaleChunk()) event.preventDefault()
})

// `vite:preloadError` only covers Vite's own preload helper. A route whose
// dynamic import fails rejects through the ROUTER instead, so catch that too —
// otherwise a stale chunk leaves a blank view with nothing in the UI to say why.
const STALE_CHUNK = /Failed to fetch dynamically imported module|error loading dynamically imported module|Importing a module script failed/i

router.onError((err) => {
  if (STALE_CHUNK.test(String(err && err.message))) recoverFromStaleChunk()
})

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(VueApexCharts)
app.mount('#app')
