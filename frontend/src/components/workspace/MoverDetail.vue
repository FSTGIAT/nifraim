<template>
  <div v-if="mover" class="md">
    <!-- The headline IS the answer: how much, which way. Everything under it
         is the evidence. A three-column table for one row made the reader
         assemble that themselves out of ₪7,680, — and +₪7,680. -->
    <div class="md-hero" :class="tone">
      <span class="md-delta ltr-number">{{ signedMoney(mover.delta) }}</span>
      <span class="md-caption">{{ caption }}</span>
    </div>

    <div class="md-bars">
      <div v-for="row in bars" :key="row.key" class="md-bar-row">
        <span class="md-bar-label">{{ row.label }}</span>
        <span class="md-bar-track">
          <span class="md-bar-fill" :class="row.tone"
                :style="{ width: (shown ? row.pct : 0) + '%' }"></span>
        </span>
        <span class="md-bar-val ltr-number" :class="{ 'md-muted': !row.value }">
          {{ row.value ? money(row.value) : '—' }}
        </span>
      </div>
    </div>

    <p v-if="mover.reported === false" class="md-note">
      לא התקבל דוח נפרעים מחברה זו החודש. הירידה משקפת הורדה שלא הושלמה, לא הפסקת תשלום —
      הרץ את ההורדה האוטומטית שוב כדי לדעת מה באמת שולם.
    </p>
    <p v-else-if="!mover.previous" class="md-note">
      לא היו עמלות מגורם זה בחודש הקודם, ולכן כל הסכום נספר כשינוי.
    </p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { money, signedMoney } from '../../utils/chartDefaults'

const props = defineProps({ mover: { type: Object, default: null } })
const shown = ref(false)

const tone = computed(() => {
  if (!props.mover) return ''
  if (props.mover.reported === false) return 'is-absent'
  return props.mover.delta < 0 ? 'is-down' : 'is-up'
})

const caption = computed(() => {
  const m = props.mover
  if (!m) return ''
  if (m.reported === false) return 'לא התקבל דוח החודש'
  if (!m.previous) return 'חדש החודש'
  const pct = Math.round((m.delta / m.previous) * 100)
  const dir = m.delta < 0 ? 'ירידה' : 'עלייה'
  return `${dir} של ${Math.abs(pct)}% מול החודש הקודם`
})

// Both months share one scale, so the two bars are directly comparable —
// scaling each to its own width would make any two months look alike.
const bars = computed(() => {
  const m = props.mover
  if (!m) return []
  const max = Math.max(Math.abs(m.previous || 0), Math.abs(m.now || 0), 1)
  return [
    { key: 'prev', label: 'חודש קודם', value: m.previous || 0,
      pct: (Math.abs(m.previous || 0) / max) * 100, tone: 'is-prev' },
    { key: 'now', label: 'החודש', value: m.now || 0,
      pct: (Math.abs(m.now || 0) / max) * 100, tone: tone.value },
  ]
})

function play() {
  shown.value = false
  requestAnimationFrame(() => requestAnimationFrame(() => { shown.value = true }))
}
onMounted(play)
watch(() => props.mover, play)
</script>

<style scoped>
.md { display: flex; flex-direction: column; gap: 18px; }

.md-hero {
  display: flex; flex-direction: column; gap: 2px; align-items: center;
  padding: 18px 16px; border-radius: var(--radius-md);
  background: var(--border-subtle);
}
.md-hero.is-up { background: color-mix(in srgb, var(--chart-gain) 10%, transparent); }
.md-hero.is-down { background: color-mix(in srgb, var(--chart-loss) 9%, transparent); }
.md-hero.is-absent { background: var(--border-subtle); }
.md-delta { font-size: 30px; font-weight: 800; letter-spacing: -0.5px; }
.md-hero.is-up .md-delta { color: var(--chart-gain); }
.md-hero.is-down .md-delta { color: var(--chart-loss); }
.md-hero.is-absent .md-delta { color: var(--text-muted); }
.md-caption { font-size: 12px; color: var(--text-muted); }

.md-bars { display: flex; flex-direction: column; gap: 10px; }
.md-bar-row {
  display: grid; grid-template-columns: 72px 1fr 82px;
  align-items: center; gap: 12px;
}
.md-bar-label { font-size: 12px; color: var(--text-muted); }
.md-bar-track {
  height: 10px; border-radius: 5px; background: var(--border-subtle);
  overflow: hidden; direction: ltr;
}
.md-bar-fill {
  display: block; height: 100%; border-radius: 5px;
  transition: width 0.5s cubic-bezier(0.2, 0, 0.2, 1);
}
.md-bar-fill.is-prev { background: var(--text-muted); opacity: 0.45; }
.md-bar-fill.is-up { background: var(--chart-gain); }
.md-bar-fill.is-down { background: var(--chart-loss); }
.md-bar-fill.is-absent { background: var(--chart-absent); }
.md-bar-val { font-size: 13px; font-weight: 700; color: var(--text); text-align: left; }
.md-muted { color: var(--text-muted); font-weight: 500; }

.md-note {
  font-size: 12px; color: var(--text-muted); line-height: 1.7;
  padding: 10px 12px; border-radius: var(--radius-sm); background: var(--border-subtle);
}

@media (prefers-reduced-motion: reduce) {
  .md-bar-fill { transition: none; }
}
</style>
