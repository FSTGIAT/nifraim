<template>
  <!-- The Mail Agent opens OVER wherever the agent is (from the side rail or
       the bell) instead of replacing the view. z-index sits under the page's
       own drawer (1010) and senders modal (1000), which open on top of it. -->
  <Teleport to="body">
    <Transition name="mam">
      <div v-if="open" class="mam-overlay" @click.self="close">
        <div class="mam-card" dir="rtl" role="dialog" aria-modal="true" aria-label="Nifraim Mail Agent">
          <button class="mam-x" type="button" aria-label="סגור" @click="close">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"
                 stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12" /></svg>
          </button>
          <div class="mam-scroll">
            <MailTab />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import MailTab from './MailTab.vue'

const props = defineProps({ open: { type: Boolean, default: false } })
const emit = defineEmits(['close'])

function close() { emit('close') }
// MailTab handles Escape first (capture) for its drawer / senders list and
// marks the event; only an unused Escape closes the whole agent.
function onKey(e) {
  if (e.key === 'Escape' && props.open && !e.defaultPrevented) close()
}
onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<style scoped>
.mam-overlay {
  position: fixed; inset: 0; z-index: 990;
  display: flex; align-items: center; justify-content: center; padding: 20px;
  background: rgba(24, 24, 24, 0.45); backdrop-filter: blur(4px);
}
.mam-card {
  position: relative; width: min(1180px, 100%); height: min(860px, calc(100vh - 40px));
  display: flex; flex-direction: column;
  background: var(--bg); border-radius: var(--radius-lg); box-shadow: var(--shadow-lg); overflow: hidden;
}
.mam-scroll { flex: 1; overflow-y: auto; padding: 18px; }
.mam-x {
  position: absolute; top: 14px; inset-inline-end: 14px; z-index: 5;
  display: inline-flex; padding: 7px; border-radius: 50%; cursor: pointer;
  color: var(--text-secondary); background: var(--card-bg); border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-sm);
}
.mam-x:hover { color: var(--text); }
.mam-x:focus-visible { outline: 2px solid var(--tab-mail); outline-offset: 2px; }

.mam-enter-active, .mam-leave-active { transition: opacity 0.22s ease; }
.mam-enter-active .mam-card, .mam-leave-active .mam-card { transition: transform 0.26s cubic-bezier(0.2, 0.8, 0.2, 1); }
.mam-enter-from, .mam-leave-to { opacity: 0; }
.mam-enter-from .mam-card, .mam-leave-to .mam-card { transform: translateY(14px) scale(0.985); }

@media (max-width: 640px) {
  .mam-overlay { padding: 0; }
  .mam-card { height: 100vh; border-radius: 0; }
  .mam-scroll { padding: 12px; }
}
@media (prefers-reduced-motion: reduce) {
  .mam-enter-active, .mam-leave-active, .mam-enter-active .mam-card, .mam-leave-active .mam-card { transition: none; }
}
</style>
