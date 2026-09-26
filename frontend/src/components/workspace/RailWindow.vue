<template>
  <!-- Shared window for pages that live in the side rail (אנשי קשר, ניהול תיק
       אישי) — the Mail Agent's shell (MailAgentModal.vue): blurred backdrop, a
       card on the app background, a round ✕. Opens OVER wherever the agent is;
       the page's own dialogs (z 1010+) open on top of it. -->
  <Teleport to="body">
    <Transition name="rw">
      <div v-if="open" class="rw-overlay" @click.self="emit('close')">
        <div class="rw-card" :style="{ '--rw-accent': accent, '--rw-width': width }" dir="rtl"
             role="dialog" aria-modal="true" :aria-label="label">
          <button class="rw-x" type="button" aria-label="סגור" @click="emit('close')">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"
                 stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12" /></svg>
          </button>
          <div class="rw-scroll"><slot /></div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  label: { type: String, default: '' },
  accent: { type: String, default: 'var(--text)' },
  width: { type: String, default: '1040px' },
})
const emit = defineEmits(['close'])

// Escape closes the window — unless another dialog is open on top of it (the
// page's own forms/confirms); that Escape belongs to them.
let cardEl = null
function onKey(e) {
  if (e.key !== 'Escape' || !props.open || e.defaultPrevented) return
  const dialogs = [...document.querySelectorAll('[aria-modal="true"], .cfm-overlay')]
  cardEl = document.querySelector('.rw-card')
  if (dialogs.some((d) => d !== cardEl && !cardEl?.contains(d))) return
  emit('close')
}
onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => {
  window.removeEventListener('keydown', onKey)
  document.body.classList.remove('mam-open')
})
// Same as the Mail Agent: hide the floating messenger pill while open.
watch(() => props.open, (v) => document.body.classList.toggle('mam-open', v))
</script>

<style scoped>
.rw-overlay {
  position: fixed; inset: 0; z-index: 990;
  display: flex; align-items: center; justify-content: center; padding: 20px;
  background: rgba(24, 24, 24, 0.45); backdrop-filter: blur(4px);
}
.rw-card {
  position: relative; width: min(var(--rw-width), 100%); max-height: min(860px, calc(100vh - 40px));
  display: flex; flex-direction: column;
  background: var(--bg); border-radius: var(--radius-lg); box-shadow: var(--shadow-lg); overflow: hidden;
}
.rw-scroll { flex: 1; overflow-y: auto; padding: 18px; }
.rw-x {
  position: absolute; top: 14px; inset-inline-end: 14px; z-index: 5;
  display: inline-flex; padding: 7px; border-radius: 50%; cursor: pointer;
  color: var(--text-secondary); background: var(--card-bg); border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-sm);
}
.rw-x:hover { color: var(--text); }
.rw-x:focus-visible { outline: 2px solid var(--rw-accent); outline-offset: 2px; }

.rw-enter-active, .rw-leave-active { transition: opacity 0.22s ease; }
.rw-enter-active .rw-card, .rw-leave-active .rw-card { transition: transform 0.26s cubic-bezier(0.2, 0.8, 0.2, 1); }
.rw-enter-from, .rw-leave-to { opacity: 0; }
.rw-enter-from .rw-card, .rw-leave-to .rw-card { transform: translateY(14px) scale(0.985); }

@media (max-width: 640px) {
  .rw-overlay { padding: 0; }
  .rw-card { max-height: 100vh; height: 100vh; border-radius: 0; }
  .rw-scroll { padding: 12px; }
}
@media (prefers-reduced-motion: reduce) {
  .rw-enter-active, .rw-leave-active, .rw-enter-active .rw-card, .rw-leave-active .rw-card { transition: none; }
}
</style>
