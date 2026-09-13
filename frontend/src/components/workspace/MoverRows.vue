<template>
  <ul class="mv">
    <li v-for="(m, i) in rows" :key="m.id_number || m.company || i"
        class="mv-row" :class="{ 'mv-row--in': shown }"
        :style="{ transitionDelay: (i * 35) + 'ms' }"
        @click="$emit('pick', { ...m, label: label(m) })">
      <span class="mv-name" :title="label(m)">{{ label(m) }}</span>

      <!-- One shared zero axis down the middle: which side a bar sits on IS
           the direction, so the reader never has to check a sign. Forced LTR
           so left/right stay literal inside an RTL page. -->
      <span class="mv-track">
        <span class="mv-zero" aria-hidden="true"></span>
        <span class="mv-bar" :class="cls(m)"
              :style="barStyle(m)"></span>
      </span>

      <span class="mv-amt ltr-number" :class="cls(m)">{{ signedMoney(m.delta) }}</span>
      <span v-if="m.reported === false" class="mv-tag">אין דוח</span>
    </li>
  </ul>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { signedMoney } from '../../utils/chartDefaults'

const props = defineProps({
  rows: { type: Array, default: () => [] },
  labelKey: { type: String, default: 'name' },
})
defineEmits(['pick'])

const shown = ref(false)

// Scale every bar against the largest movement in EITHER direction, so the two
// sides of the axis stay comparable. Half the track per side.
const max = computed(
  () => Math.max(1, ...props.rows.map(m => Math.abs(Number(m.delta) || 0))),
)

function label(m) {
  return m[props.labelKey] || m.company || m.name || m.id_number || '—'
}

function cls(m) {
  // A company that sent no report has not "dropped" — it is absent. Neutral,
  // never the loss colour, or a failed download reads as a business decline.
  if (m.reported === false) return 'is-missing'
  return Number(m.delta) < 0 ? 'is-down' : 'is-up'
}

function barStyle(m) {
  const v = Number(m.delta) || 0
  // Minimum 2% so a tiny-but-real movement is still a visible mark rather than
  // nothing at all (live: ילין at −₪54 beside הפניקס at −₪8,347).
  const pct = Math.max(2, (Math.abs(v) / max.value) * 50)
  return v < 0
    ? { right: '50%', width: pct + '%' }
    : { left: '50%', width: pct + '%' }
}

onMounted(() => {
  // One entrance: the bars grow out of the axis once.
  requestAnimationFrame(() => { shown.value = true })
})
</script>

<style scoped>
.mv { list-style: none; display: flex; flex-direction: column; }

.mv-row {
  display: grid;
  grid-template-columns: minmax(72px, 132px) 1fr auto auto;
  align-items: center; gap: 10px;
  padding: 7px 8px; border-radius: var(--radius-sm); cursor: pointer;
}
.mv-row:hover { background: var(--border-subtle); }

.mv-name {
  font-size: 13px; color: var(--text);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.mv-track {
  position: relative; direction: ltr;
  height: 18px; border-radius: 3px;
}
.mv-zero {
  position: absolute; left: 50%; top: -3px; bottom: -3px;
  width: 1px; background: var(--text-muted); opacity: 0.35;
}
.mv-bar {
  position: absolute; top: 2px; bottom: 2px;
  border-radius: 3px;
  /* Grows out of the axis on first paint; no looping, no hover replay. */
  transform: scaleX(0); transform-origin: var(--mv-origin, left center);
  transition: transform 0.55s cubic-bezier(0.2, 0, 0.2, 1);
}
.mv-row--in .mv-bar { transform: scaleX(1); }
.mv-bar.is-up { background: var(--chart-gain); --mv-origin: left center; }
.mv-bar.is-down { background: var(--chart-loss); --mv-origin: right center; }
.mv-bar.is-missing { background: var(--chart-absent); --mv-origin: right center; }

.mv-amt {
  font-size: 13px; font-weight: 700; min-width: 74px; text-align: left;
}
.mv-amt.is-up { color: var(--chart-gain); }
.mv-amt.is-down { color: var(--chart-loss); }
.mv-amt.is-missing { color: var(--text-muted); }

.mv-tag {
  padding: 1px 7px; border-radius: 10px; background: var(--border-subtle);
  color: var(--text-muted); font-size: 10px; font-weight: 600; white-space: nowrap;
}

@media (prefers-reduced-motion: reduce) {
  .mv-bar { transition: none; transform: scaleX(1); }
}
</style>
