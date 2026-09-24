<template>
  <!--
    Home-only nav rail. It replaces the floating circle menu on the home
    screen; inside a tab the strip keeps that round button, because there the
    horizontal strip is already the navigation and a second rail would be a
    second answer to the same question.

    Left edge, deliberately, in an RTL app: the right edge is already a
    documented rail — bell · assistant · messenger, top to bottom — and nav
    there would land on top of it.
  -->
  <aside class="rail" :class="{ 'rail--open': open }" @mouseenter="open = true" @mouseleave="open = false">
    <div class="rail-top">
      <button
        type="button"
        class="rail-face"
        aria-label="עריכת אווטאר"
        title="עריכת אווטאר"
        @click="picking = !picking"
      >
        <Avatar
          :name="user?.full_name || ''"
          :username="user?.username || ''"
          :avatar-seed="currentSeed"
          :size="54"
        />
        <span class="rail-face-pen" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 20h9" /><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
          </svg>
        </span>
      </button>
      <div class="rail-who">
        <span class="rail-name">{{ user?.full_name || user?.username || '' }}</span>
        <span class="rail-mail ltr-number">{{ user?.email || '' }}</span>
      </div>
    </div>

    <!-- No dialog. Choosing a face is a small thing and a modal made it feel
         like a form; the deck just opens where the face already is. -->
    <Transition name="rail-pick">
      <div v-if="picking && open" class="rail-deck">
        <!-- Two families, kept apart. Mixed into one deck you had to walk past
             fourteen illustrations to reach the 3D ones. -->
        <div class="rail-fam" role="tablist" aria-label="סגנון אווטאר">
          <button
            v-for="f in AVATAR_FAMILIES"
            :key="f"
            type="button"
            role="tab"
            class="rail-fam-btn"
            :class="{ 'is-on': family === f }"
            :aria-selected="family === f"
            @click="family = f"
          >{{ FAMILY_LABEL[f] }}</button>
        </div>
        <AvatarSwiper
          ref="swiper"
          :seeds="seeds"
          :username="user?.username || ''"
          :name="user?.full_name || ''"
          :model-value="currentSeed"
          :size="84"
          style="--deck-size: 84px"
          @front="front = $event"
          @choose="saveAvatar"
        />
        <div class="rail-deck-bar">
          <button type="button" class="rail-deck-arrow" aria-label="הקודם" @click="swiper?.step(-1)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6" /></svg>
          </button>
          <button
            type="button"
            class="rail-deck-save"
            :disabled="saving || !front || front === currentSeed"
            @click="saveAvatar(front)"
          >{{ saving ? 'שומר…' : (front === currentSeed ? 'הנוכחי' : 'בחר') }}</button>
          <button type="button" class="rail-deck-arrow" aria-label="הבא" @click="swiper?.step(1)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6" /></svg>
          </button>
        </div>
        <p v-if="avatarError" class="rail-deck-err">{{ avatarError }}</p>
      </div>
    </Transition>

    <div class="rail-rule"></div>

    <nav class="rail-nav">
      <button
        v-for="it in main"
        :key="it.key"
        type="button"
        class="rail-item"
        :aria-label="it.label"
        @click="$emit('select', it.key)"
      >
        <span class="rail-ico">
          <span v-html="ICONS[it.icon]"></span>
          <span v-if="it.badge" class="rail-badge ltr-number">{{ it.badge > 9 ? '9+' : it.badge }}</span>
        </span>
        <span class="rail-label">{{ it.label }}</span>
      </button>
    </nav>

    <div class="rail-foot">
      <button
        v-if="signOut"
        type="button"
        class="rail-item rail-item--out"
        :aria-label="signOut.label"
        @click="$emit('select', signOut.key)"
      >
        <span class="rail-ico" v-html="ICONS[signOut.icon]"></span>
        <span class="rail-label">{{ signOut.label }}</span>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import Avatar from '../Avatar.vue'
import { candidateSeeds, seedFor, avatarFamily, AVATAR_FAMILIES } from '../../utils/avatarSeed.js'
import AvatarSwiper from './AvatarSwiper.vue'
import { useMessengerStore } from '../../stores/messenger.js'

const props = defineProps({
  // The SAME list the circle menu uses, so the two can never drift apart.
  items: { type: Array, default: () => [] },
  user: { type: Object, default: null },
})
defineEmits(['select'])

const open = ref(false)

/* ── avatar ──────────────────────────────────────────────────────────────
   No new avatar system here on purpose. `utils/avatarSeed.js` is already the
   one source of truth — the CSS face, the messenger and the Remotion avatar
   all derive from the same seed, and that file says in as many words that a
   second hash would make the swatch you tap "a lie". The picker itself lives
   in its own modal: a deck of cards needs room the 76px rail does not have. */
const messenger = useMessengerStore()
const picking = ref(false)
const swiper = ref(null)
const front = ref('')
const saving = ref(false)
const avatarError = ref('')
const FAMILY_LABEL = { flat: 'איור', soft: 'תלת־ממד' }
// Opens on the family you are already wearing, so the first thing you see is
// the face you are changing away from.
const family = ref(avatarFamily(seedFor(props.user)))
const seeds = computed(() => candidateSeeds(props.user?.username || '', family.value))
const currentSeed = computed(() => seedFor(props.user))

async function saveAvatar(seed) {
  if (!seed || saving.value) return
  if (seed === currentSeed.value) { picking.value = false; return }
  saving.value = true
  avatarError.value = ''
  try {
    await messenger.changeAvatar(seed)
    picking.value = false
  } catch {
    avatarError.value = 'שמירה נכשלה'
  } finally {
    saving.value = false
  }
}

// Collapsed, the deck is clipped to a 76px column and you would be choosing
// blind, so the rail closing closes it too.
watch(open, (v) => { if (!v) picking.value = false })
// Re-open on the family you are wearing, not on whichever tab was left behind.
watch(picking, (v) => { if (v) family.value = avatarFamily(currentSeed.value) })

// `home` is dropped here: this rail only exists on home, and `goHome()`
// early-returns when it is already home — it would be a button that does
// nothing. Sign-out is pulled out of the flow and parked at the bottom, away
// from the things you press by accident.
const main = computed(() => props.items.filter((i) => i.key !== 'home' && i.key !== 'logout'))
const signOut = computed(() => props.items.find((i) => i.key === 'logout') || null)

/* Lucide-style strokes, matching the icons the circle menu renders in React.
   Static constants, never user input, so `v-html` has no injection surface. */
const S = 'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'
const ICONS = {
  Home: `<svg viewBox="0 0 24 24" ${S}><path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/><path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>`,
  Search: `<svg viewBox="0 0 24 24" ${S}><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>`,
  Settings: `<svg viewBox="0 0 24 24" ${S}><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>`,
  Mail: `<svg viewBox="0 0 24 24" ${S}><path d="M13 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6"/><path d="m2 7 8.97 5.7a1.94 1.94 0 0 0 2.06 0L16.5 10"/><path fill="currentColor" stroke="none" d="M19 1c.34 2.2 1.3 3.16 3.5 3.5-2.2.34-3.16 1.3-3.5 3.5-.34-2.2-1.3-3.16-3.5-3.5C17.7 4.16 18.66 3.2 19 1Z"/></svg>`,
  HelpCircle: `<svg viewBox="0 0 24 24" ${S}><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><path d="M12 17h.01"/></svg>`,
  LogOut: `<svg viewBox="0 0 24 24" ${S}><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/></svg>`,
}
</script>

<style scoped>
.rail {
  position: fixed;
  top: 44px;
  left: 24px;
  z-index: 102;
  /* Tall, with sign-out pinned to its foot — but stopping clear of the
     insights launcher. That orbit is a 280px box sitting 24px off the bottom
     and it shares this column, so anything below 304px lands inside its ring.
     Measured, not guessed: x 24..304 at every viewport height tried. */
  bottom: 320px;
  min-height: 286px;
  width: 76px;
  display: flex;
  flex-direction: column;
  padding: 14px 15px;
  border-radius: 20px;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  box-shadow: 0 10px 34px rgba(24, 24, 24, 0.07);
  overflow: hidden;
  /* Fixed, so widening never reflows the page behind it. */
  transition: width 0.28s cubic-bezier(0.32, 0.72, 0, 1),
              box-shadow 0.28s ease;
  direction: rtl;
}
.rail--open {
  width: 212px;
  box-shadow: 0 16px 46px rgba(24, 24, 24, 0.12);
}

/* ── identity ─────────────────────────────────────────────────────────── */
.rail-top { display: flex; align-items: center; gap: 11px; min-height: 54px; }
.rail-face {
  position: relative; flex: none; padding: 0; border: none;
  background: none; cursor: pointer; border-radius: 50%; line-height: 0;
}
.rail-face:focus-visible { outline: 2px solid var(--tab-production, #2F73C4); outline-offset: 3px; }
/* The pencil only shows on approach — an avatar with a permanent edit badge
   reads as a form field rather than as you. */
.rail-face-pen {
  position: absolute; inset-inline-end: -3px; bottom: -3px;
  width: 20px; height: 20px; border-radius: 50%;
  display: grid; place-items: center;
  background: var(--card-bg); border: 1px solid var(--border-subtle);
  color: var(--text-muted);
  opacity: 0; transform: scale(0.7);
  transition: opacity 0.16s ease, transform 0.16s ease;
}
.rail-face-pen svg { width: 10px; height: 10px; }
.rail:hover .rail-face-pen,
.rail-face:focus-visible .rail-face-pen { opacity: 1; transform: none; }

/* The name block is laid out at the OPEN width at all times and clipped by the
   rail's overflow, so it never re-wraps as the rail grows — text reflowing
   mid-transition is the thing that makes a rail like this look cheap. */
.rail-who {
  display: flex; flex-direction: column; gap: 1px;
  width: 120px; flex: none; min-width: 0;
  opacity: 0; transform: translateX(6px);
  transition: opacity 0.2s ease 0.06s, transform 0.28s cubic-bezier(0.32, 0.72, 0, 1);
}
.rail--open .rail-who { opacity: 1; transform: none; }
.rail-name {
  font-size: 13px; font-weight: 700; color: var(--text);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.rail-mail {
  font-size: 10.5px; color: var(--text-muted);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.rail-deck {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  width: 182px; margin-top: 12px;
}
.rail-fam {
  display: flex; gap: 3px; padding: 3px;
  border-radius: 9px; background: var(--bg);
}
.rail-fam-btn {
  padding: 5px 12px; border: none; border-radius: 7px;
  background: none; color: var(--text-muted); cursor: pointer;
  font-family: inherit; font-size: 11.5px; font-weight: 700;
  transition: background 0.16s ease, color 0.16s ease;
}
.rail-fam-btn.is-on { background: var(--card-bg); color: var(--text); box-shadow: 0 1px 3px rgba(24, 24, 24, 0.10); }

.rail-deck-bar { display: flex; align-items: center; gap: 6px; }
.rail-deck-arrow {
  flex: none; width: 26px; height: 26px; display: grid; place-items: center;
  border: 1px solid var(--border-subtle); border-radius: 50%;
  background: var(--card-bg); color: var(--text-muted); cursor: pointer;
}
.rail-deck-arrow svg { width: 13px; height: 13px; }
.rail-deck-arrow:hover { background: var(--bg); color: var(--text); }
.rail-deck-save {
  min-width: 68px; padding: 6px 14px; border: none; border-radius: 9px;
  background: var(--tab-production, #2F73C4); color: #fff;
  font-family: inherit; font-size: 12px; font-weight: 700; cursor: pointer;
}
.rail-deck-save:disabled { background: var(--bg); color: var(--text-muted); cursor: default; }
.rail-deck-err { font-size: 11px; color: var(--red-deep, #C23934); }
.rail-pick-enter-active, .rail-pick-leave-active { transition: opacity 0.18s ease; }
.rail-pick-enter-from, .rail-pick-leave-to { opacity: 0; }

.rail-rule {
  height: 1px; margin: 13px 0 11px;
  background: var(--border-subtle);
}

/* ── items ────────────────────────────────────────────────────────────── */
.rail-nav { display: flex; flex-direction: column; gap: 4px; }
.rail-foot { margin-top: auto; padding-top: 10px; border-top: 1px solid var(--border-subtle); }

.rail-item {
  display: flex; align-items: center; gap: 12px;
  width: 182px;          /* open width; clipped while collapsed */
  padding: 9px 7px;
  border: none; border-radius: 11px;
  background: none; cursor: pointer;
  font-family: inherit; font-size: 13px; font-weight: 600;
  color: var(--text-muted);
  text-align: start;
  transition: background 0.16s ease, color 0.16s ease;
}
.rail-item:hover { background: var(--bg); color: var(--text); }
.rail-item:focus-visible {
  outline: 2px solid var(--tab-production, #2F73C4);
  outline-offset: 1px;
}
.rail-ico { position: relative; flex: none; display: grid; place-items: center; width: 32px; height: 20px; }
.rail-ico > span:first-child { display: grid; place-items: center; }
.rail-ico :deep(svg) { width: 18px; height: 18px; }
/* Count of mail waiting for the agent's approval (Mail Agent item). */
.rail-badge {
  position: absolute; top: -7px; inset-inline-start: 0;
  min-width: 17px; height: 17px; padding: 0 4px; border-radius: 999px;
  display: grid; place-items: center; font-size: 10px; font-weight: 800; line-height: 1;
  color: #fff; background: var(--tab-mail-ink); border: 2px solid var(--card-bg);
  animation: rail-badge-in 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}
@keyframes rail-badge-in { from { transform: scale(0); } }
@media (prefers-reduced-motion: reduce) { .rail-badge { animation: none; } }
.rail-label {
  white-space: nowrap;
  opacity: 0; transform: translateX(6px);
  transition: opacity 0.2s ease 0.06s, transform 0.28s cubic-bezier(0.32, 0.72, 0, 1);
}
.rail--open .rail-label { opacity: 1; transform: none; }

/* Leaving is the one destructive thing in here, so it is the one thing that
   changes colour. */
.rail-item--out:hover {
  background: color-mix(in srgb, var(--red-deep, #C23934) 9%, transparent);
  color: var(--red-deep, #C23934);
}

@media (prefers-reduced-motion: reduce) {
  .rail, .rail-who, .rail-label { transition: none; }
}

/* Below this the centred card grid starts to reach the rail. Give up the
   hover-expand rather than let a nav panel sit on top of the cards. */
@media (max-width: 1180px) {
  .rail { left: 12px; padding: 12px 11px; width: 66px; }
  .rail--open { width: 66px; box-shadow: 0 10px 34px rgba(24, 24, 24, 0.07); }
  .rail-who, .rail-label, .rail-deck { display: none; }
  .rail-item { width: auto; justify-content: center; padding: 9px 0; }
  .rail-ico { width: 22px; }
}
@media (max-width: 720px) {
  .rail { display: none; }
}
</style>
