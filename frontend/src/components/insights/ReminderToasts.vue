<template>
  <!-- Nifra reminders — the morning brief and the 15-minute heads-up, on every screen of the app.
       Spoken in Hebrew when the agent enabled voice (Nifra Insights → השמע תזכורות). -->
  <Teleport to="body">
    <TransitionGroup name="rt" tag="div" class="rt-stack" aria-live="polite">
      <article v-for="t in toasts" :key="t.id" class="rt" :class="'rt--' + t.kind">
        <span class="rt-icon" aria-hidden="true">
          <svg v-if="t.kind === 'brief'" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></svg>
          <svg v-else viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="13" r="8" /><path d="M12 9v4l2.5 2M9 2h6" /></svg>
        </span>
        <div class="rt-body">
          <p class="rt-title">{{ t.title }}</p>
          <p class="rt-text">{{ t.text }}</p>
          <div class="rt-actions">
            <template v-if="t.kind === 'task'">
              <button type="button" class="rt-btn rt-btn--main" @click="done(t)">בוצע</button>
              <button type="button" class="rt-btn" @click="snooze(t)">דחה 10 דק׳</button>
            </template>
            <button v-if="store.voiceOn" type="button" class="rt-btn" @click="replay(t)">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M11 5L6 9H3v6h3l5 4V5z" /><path d="M15.5 8.5a5 5 0 010 7" /></svg>
              השמע
            </button>
            <button type="button" class="rt-btn" :class="{ 'rt-btn--main': t.kind === 'brief' }" @click="open(t, $event.currentTarget)">פתח</button>
          </div>
        </div>
        <button type="button" class="rt-x" aria-label="סגירה" @click="dismiss(t.id)">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 6l12 12M18 6L6 18" /></svg>
        </button>
      </article>
    </TransitionGroup>
  </Teleport>
</template>

<script setup>
import { useCallsInsightsStore } from '../../stores/callsInsights.js'
import { useVoiceReminders } from '../../composables/useVoiceReminders.js'

const emit = defineEmits(['open'])
const store = useCallsInsightsStore()
const { toasts, dismiss, snooze, done, replay } = useVoiceReminders()

function open(t, el) {
  emit('open', el)   // the studio grows out of the button that was pressed
  setTimeout(() => dismiss(t.id), 600)
}
</script>

<style scoped>
.rt-stack {
  position: fixed; bottom: 22px; left: 50%; transform: translateX(-50%); z-index: 1050;
  display: flex; flex-direction: column; gap: 8px; width: min(440px, calc(100vw - 32px)); pointer-events: none;
}
.rt {
  pointer-events: auto; position: relative; display: flex; gap: 12px; align-items: flex-start; padding: 14px 16px 12px 40px;
  border-radius: 16px; background: rgba(255, 255, 255, 0.96); backdrop-filter: blur(10px);
  box-shadow: 0 18px 50px rgba(16, 32, 36, 0.18), 0 0 0 1px rgba(44, 95, 107, 0.14); font-family: 'Heebo', sans-serif;
}
.rt-icon { flex-shrink: 0; width: 34px; height: 34px; border-radius: 50%; display: grid; place-items: center; background: var(--tab-insights-wash); color: var(--tab-insights-ink); }
.rt-body { flex: 1; min-width: 0; }
.rt-title { margin: 0; font-size: 14px; font-weight: 900; }
.rt-text { margin: 2px 0 0; font-size: 13px; color: var(--text-secondary, #5C5C5C); line-height: 1.45; }
.rt-actions { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
.rt-btn {
  display: inline-flex; align-items: center; gap: 4px; padding: 6px 12px; border-radius: 9px; border: 1px solid var(--border-subtle, #E5E5E5);
  background: #fff; font: inherit; font-size: 12px; font-weight: 700; cursor: pointer; color: var(--text-primary, #181818);
  transition: transform 0.18s ease, border-color 0.18s;
}
.rt-btn:hover { transform: translateY(-1px); border-color: var(--tab-insights); }
.rt-btn--main { background: var(--tab-insights); border-color: var(--tab-insights); color: #fff; box-shadow: 0 4px 10px rgba(44, 95, 107, 0.22); }
.rt-x { position: absolute; top: 10px; left: 10px; width: 24px; height: 24px; border-radius: 7px; border: none; background: none; cursor: pointer; display: grid; place-items: center; color: var(--text-secondary, #5C5C5C); }
.rt-x:hover { background: #F3F3F3; }
.rt-enter-active { transition: opacity 0.5s ease, transform 0.6s cubic-bezier(0.2, 0.8, 0.2, 1); }
.rt-leave-active { transition: opacity 0.3s ease, transform 0.3s ease; }
.rt-enter-from { opacity: 0; transform: translateY(16px) scale(0.98); }
.rt-leave-to { opacity: 0; transform: translateY(8px); }
@media (prefers-reduced-motion: reduce) { .rt-enter-active, .rt-leave-active { transition: opacity 0.2s; } .rt-enter-from, .rt-leave-to { transform: none; } }
@media print { .rt-stack { display: none; } }
</style>
