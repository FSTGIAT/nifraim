<template>
  <div class="pick">
    <!-- Search is an icon until it is wanted. The canonical magnifier (r=8 +
         diagonal) — the same mark the rest of the app uses. -->
    <div class="pick-bar">
      <button class="pick-icon" type="button" :class="{ 'pick-icon--on': searchOpen }"
              aria-label="חיפוש חברה" title="חיפוש חברה" @click="toggleSearch">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
        </svg>
      </button>
      <input v-if="searchOpen" ref="searchEl" v-model="query" class="pick-search"
             placeholder="הקלידו שם חברה…" @keydown.esc="toggleSearch" />
      <span v-else class="pick-count ltr-number">{{ index + 1 }} / {{ filtered.length }}</span>
    </div>

    <!-- One company at a time. Wheel, arrows and the keyboard all move the
         same index, so whichever the hand reaches for works. -->
    <div
      class="pick-stage"
      tabindex="0"
      @wheel.prevent="onWheel"
      @keydown.up.prevent="move(-1)"
      @keydown.down.prevent="move(1)"
      @keydown.enter.prevent="confirm"
    >
      <button class="pick-arrow" type="button" aria-label="הקודם"
              :disabled="!filtered.length" @click="move(-1)">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="m18 15-6-6-6 6"/>
        </svg>
      </button>

      <div class="pick-window">
        <Transition :name="dir >= 0 ? 'pk-up' : 'pk-down'" mode="out-in">
          <button v-if="current" :key="current.label" class="pick-co" type="button" @click="confirm">
            <CompanyLogo :company="current.label" :size="88" />
            <span class="pick-co-name">{{ current.label }}</span>
            <span v-if="current.note" class="pick-co-note">
              <svg v-if="current.noteOk" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                   stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
              {{ current.note }}
            </span>
          </button>
          <p v-else key="none" class="pick-none">לא נמצאה חברה בשם הזה</p>
        </Transition>
      </div>

      <button class="pick-arrow" type="button" aria-label="הבא"
              :disabled="!filtered.length" @click="move(1)">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="m6 9 6 6 6-6"/>
        </svg>
      </button>
    </div>

    <button v-if="confirmLabel" class="pick-go" type="button" :disabled="!current" @click="confirm">
      {{ confirmLabel }}
    </button>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import CompanyLogo from './CompanyLogo.vue'

/**
 * Pick one company from a list, one large mark at a time.
 *
 * A grid asked the eye to scan every insurer to find one. This is a shorter
 * path to the same answer and the logo is big enough to recognise without
 * reading. Shared by the contact and portal modals so the two cannot drift.
 *
 * `companies` items: { label, note?, noteOk? } — `note` is the small line
 * under the name ("2 דוחות", "כבר יש כתובת"), `noteOk` gives it a tick.
 */
const props = defineProps({
  companies: { type: Array, default: () => [] },
  confirmLabel: { type: String, default: 'המשך' },
  initial: { type: String, default: '' },
})
const emit = defineEmits(['select'])

const query = ref('')
const searchOpen = ref(false)
const searchEl = ref(null)
const index = ref(0)
const dir = ref(1)

const filtered = computed(() => {
  const q = query.value.trim()
  if (!q) return props.companies
  return props.companies.filter((c) => String(c.label || '').includes(q))
})

const current = computed(() => filtered.value[index.value] || null)

function move(delta) {
  const n = filtered.value.length
  if (!n) return
  dir.value = delta
  // Wraps, so the list never dead-ends at either edge.
  index.value = (index.value + delta + n) % n
}

// Wheel accumulates: a trackpad emits many small deltas and one notch should
// advance one company, not ten.
let wheelAcc = 0
function onWheel(e) {
  wheelAcc += e.deltaY
  if (Math.abs(wheelAcc) < 40) return
  move(wheelAcc > 0 ? 1 : -1)
  wheelAcc = 0
}

function toggleSearch() {
  searchOpen.value = !searchOpen.value
  if (searchOpen.value) nextTick(() => searchEl.value?.focus())
  else query.value = ''
}

function confirm() {
  if (current.value) emit('select', current.value.label)
}

// A narrower list must not leave the cursor pointing past its end.
watch(filtered, (list) => {
  if (index.value >= list.length) index.value = 0
})

// Open on the caller's chosen company when it names one.
watch(() => props.initial, (label) => {
  if (!label) return
  const i = props.companies.findIndex((c) => c.label === label)
  if (i >= 0) index.value = i
}, { immediate: true })

defineExpose({ reset() { query.value = ''; searchOpen.value = false; index.value = 0; dir.value = 1 } })
</script>

<style scoped>
.pick { display: flex; flex-direction: column; gap: 12px; }

.pick-bar { display: flex; align-items: center; gap: 9px; min-height: 36px; }
.pick-icon {
  width: 34px; height: 34px; flex-shrink: 0;
  display: grid; place-items: center; cursor: pointer;
  border: 1px solid var(--border-subtle); border-radius: 9px;
  background: var(--card-bg); color: var(--text-muted);
  transition: border-color 0.15s ease, color 0.15s ease, background 0.15s ease;
}
.pick-icon:hover, .pick-icon--on {
  border-color: var(--pick-accent, #D6336C);
  color: var(--pick-accent, #D6336C);
  background: color-mix(in srgb, var(--pick-accent, #D6336C) 6%, var(--card-bg));
}
.pick-search {
  flex: 1; min-width: 0; padding: 8px 11px;
  font-family: inherit; font-size: 13px; color: var(--text);
  border: 1px solid var(--pick-accent, #D6336C); border-radius: var(--radius-sm);
  background: var(--card-bg);
}
.pick-search:focus { outline: none; box-shadow: 0 0 0 3px color-mix(in srgb, var(--pick-accent, #D6336C) 16%, transparent); }
.pick-count { margin-inline-start: auto; font-size: 11.5px; color: var(--text-muted); }

.pick-stage {
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  padding: 6px 0; border-radius: var(--radius-md);
  background: var(--bg); outline: none;
}
.pick-stage:focus-visible { box-shadow: 0 0 0 2px var(--pick-accent, #D6336C); }

.pick-arrow {
  width: 34px; height: 26px; flex-shrink: 0;
  display: grid; place-items: center; cursor: pointer;
  border: none; border-radius: 8px; background: none; color: var(--text-muted);
  transition: color 0.15s ease, background 0.15s ease, transform 0.15s ease;
}
.pick-arrow:hover:not(:disabled) {
  color: var(--pick-accent, #D6336C);
  background: color-mix(in srgb, var(--pick-accent, #D6336C) 9%, transparent);
}
.pick-arrow:active:not(:disabled) { transform: scale(0.9); }
.pick-arrow:disabled { opacity: 0.3; cursor: default; }

.pick-window { height: 136px; width: 100%; display: grid; place-items: center; overflow: hidden; }
.pick-co {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 10px 22px; cursor: pointer; border: none; background: none; font-family: inherit;
}
.pick-co-name { font-size: 15px; font-weight: 700; color: var(--text); }
.pick-co-note {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 11px; font-weight: 600; color: var(--text-muted);
}
.pick-co-note svg { color: var(--green-deep, #1B5E20); }
.pick-none { font-size: 13px; color: var(--text-muted); }

/* Silk: the outgoing company leaves the way the incoming one arrives, so the
   column reads as one strip moving rather than two cards swapping. */
.pk-up-enter-active, .pk-up-leave-active,
.pk-down-enter-active, .pk-down-leave-active {
  transition: opacity 0.22s ease, transform 0.28s cubic-bezier(0.22, 0.61, 0.36, 1);
}
.pk-up-enter-from   { opacity: 0; transform: translateY(26px) scale(0.94); }
.pk-up-leave-to     { opacity: 0; transform: translateY(-26px) scale(0.94); }
.pk-down-enter-from { opacity: 0; transform: translateY(-26px) scale(0.94); }
.pk-down-leave-to   { opacity: 0; transform: translateY(26px) scale(0.94); }

.pick-go {
  width: 100%; padding: 10px; cursor: pointer;
  border: none; border-radius: var(--radius-sm);
  background: var(--pick-accent, #D6336C); color: #fff;
  font-family: inherit; font-size: 13.5px; font-weight: 700;
}
.pick-go:hover:not(:disabled) { filter: brightness(0.93); }
.pick-go:disabled { opacity: 0.45; cursor: not-allowed; }

@media (prefers-reduced-motion: reduce) {
  .pk-up-enter-active, .pk-up-leave-active,
  .pk-down-enter-active, .pk-down-leave-active { transition: opacity 0.12s ease; }
  .pk-up-enter-from, .pk-up-leave-to,
  .pk-down-enter-from, .pk-down-leave-to { transform: none; }
  .pick-arrow:active:not(:disabled) { transform: none; }
}
</style>
