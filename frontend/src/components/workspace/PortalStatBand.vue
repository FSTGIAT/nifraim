<template>
  <div class="stat-band">
    <article
      v-for="s in stats"
      :key="s.key"
      class="stat"
      :class="`stat--${s.tone}`"
    >
      <span class="stat__circles" aria-hidden="true">
        <span class="stat__circle stat__circle--1"></span>
        <span class="stat__circle stat__circle--2"></span>
        <span class="stat__circle stat__circle--3"></span>
      </span>
      <span class="stat__icon" aria-hidden="true" v-html="s.icon"></span>
      <div class="stat__body">
        <span class="stat__value ltr-number">{{ s.value }}</span>
        <span class="stat__label">{{ s.label }}</span>
      </div>
    </article>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'
import { relativeHebrew } from '../../utils/relativeTime.js'

const store = usePortalAutomationStore()

const ICONS = {
  total: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
  active: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
  healthy: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12h4l2-7 4 14 2-7h6"/></svg>',
  last: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
}

const total = computed(() => store.credentials.length)
const active = computed(() => store.credentials.filter((c) => c.is_active).length)
const healthy = computed(() => store.credentials.filter((c) => c.last_run_status === 'success').length)

const lastRun = computed(() => {
  const b = store.latestBatch
  if (!b) return { value: '—', tone: 'muted' }
  const when = b.finished_at || b.started_at
  const txt = when ? relativeHebrew(when) : '—'
  const tone = b.status === 'failed' ? 'red' : b.status === 'partial' ? 'amber' : 'green'
  return { value: txt, tone }
})

const stats = computed(() => [
  { key: 'total', label: 'סה״כ פורטלים', value: total.value, tone: 'sky', icon: ICONS.total },
  { key: 'active', label: 'פעילים', value: active.value, tone: 'teal', icon: ICONS.active },
  { key: 'healthy', label: 'תקינים', value: `${healthy.value}/${total.value}`, tone: 'green', icon: ICONS.healthy },
  { key: 'last', label: 'ריצה אחרונה', value: lastRun.value.value, tone: lastRun.value.tone === 'muted' ? 'violet' : lastRun.value.tone, icon: ICONS.last },
])
</script>

<style scoped>
.stat-band {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 14px;
}
.stat {
  position: relative;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
  border-radius: var(--radius-lg, 16px);
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(26, 20, 16, 0.03), 0 4px 14px rgba(26, 20, 16, 0.04);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.stat:hover { transform: translateY(-2px); box-shadow: 0 12px 26px rgba(17, 12, 6, 0.08); }

/* Decorative pastel blur circles (very low alpha brand tints) */
.stat__circles { position: absolute; inset: 0; pointer-events: none; }
.stat__circle { position: absolute; border-radius: 50%; opacity: 0.5; }
.stat__circle--1 { width: 120px; height: 120px; top: -50px; inset-inline-start: -30px; background: var(--tint-strong); }
.stat__circle--2 { width: 70px; height: 70px; bottom: -28px; inset-inline-start: 40px; background: var(--tint-soft); }
.stat__circle--3 { width: 40px; height: 40px; top: 10px; inset-inline-start: 90px; background: var(--tint-soft); }

.stat__icon {
  position: relative;
  width: 44px; height: 44px;
  border-radius: 13px;
  display: grid; place-items: center;
  color: var(--accent);
  background: var(--tint-strong);
  flex-shrink: 0;
}
.stat__body { position: relative; display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.stat__value {
  font-size: 24px;
  font-weight: 800;
  line-height: 1.05;
  color: var(--text);
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  letter-spacing: -0.5px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.stat__label { font-size: 12px; font-weight: 700; color: var(--text-muted); }

/* Tones — pastel, mapped to chart palette */
.stat--sky    { --accent: #2F73C4; --tint-strong: rgba(78,157,208,0.16); --tint-soft: rgba(78,157,208,0.08); }
.stat--teal   { --accent: #178f78; --tint-strong: rgba(31,168,140,0.16); --tint-soft: rgba(31,168,140,0.08); }
.stat--green  { --accent: var(--green-deep); --tint-strong: rgba(46,132,74,0.15); --tint-soft: rgba(46,132,74,0.07); }
.stat--violet { --accent: var(--accent-violet); --tint-strong: rgba(127,86,217,0.15); --tint-soft: rgba(127,86,217,0.07); }
.stat--amber  { --accent: var(--amber); --tint-strong: rgba(232,114,10,0.15); --tint-soft: rgba(232,114,10,0.07); }
.stat--red    { --accent: var(--red-deep); --tint-strong: rgba(234,0,30,0.13); --tint-soft: rgba(234,0,30,0.06); }

@media (prefers-reduced-motion: reduce) {
  .stat:hover { transform: none; }
}
</style>
