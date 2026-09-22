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
      <Avatar
        :name="user?.full_name || ''"
        :username="user?.username || ''"
        :avatar-seed="user?.avatar_seed || ''"
        :size="42"
        class="rail-avatar"
      />
      <div class="rail-who">
        <span class="rail-name">{{ user?.full_name || user?.username || '' }}</span>
        <span class="rail-mail ltr-number">{{ user?.email || '' }}</span>
      </div>
    </div>

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
        <span class="rail-ico" v-html="ICONS[it.icon]"></span>
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
import { ref, computed } from 'vue'
import Avatar from '../Avatar.vue'

const props = defineProps({
  // The SAME list the circle menu uses, so the two can never drift apart.
  items: { type: Array, default: () => [] },
  user: { type: Object, default: null },
})
defineEmits(['select'])

const open = ref(false)

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
  /* Hugs its content. A full-height rail put sign-out down in the corner,
     straight through the insights launcher's orbit, and left a tall empty
     column in between. */
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
.rail-top { display: flex; align-items: center; gap: 11px; min-height: 42px; }
.rail-avatar { flex: none; }
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

.rail-rule {
  height: 1px; margin: 13px 0 11px;
  background: var(--border-subtle);
}

/* ── items ────────────────────────────────────────────────────────────── */
.rail-nav { display: flex; flex-direction: column; gap: 4px; }
.rail-foot { margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--border-subtle); }

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
.rail-ico { flex: none; display: grid; place-items: center; width: 32px; height: 20px; }
.rail-ico :deep(svg) { width: 18px; height: 18px; }
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
  .rail-who, .rail-label { display: none; }
  .rail-item { width: auto; justify-content: center; padding: 9px 0; }
  .rail-ico { width: 22px; }
}
@media (max-width: 720px) {
  .rail { display: none; }
}
</style>
