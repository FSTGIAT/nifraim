<template>
  <aside class="activity">
    <!-- ── Worker status ─────────────────────────────────────── -->
    <section class="acard">
      <header class="acard__head">
        <span class="acard__eyebrow">המחשב המקומי</span>
      </header>
      <div class="worker" :class="worker.online ? 'worker--on' : 'worker--off'">
        <span class="worker__dot" aria-hidden="true"></span>
        <div class="worker__body">
          <span class="worker__state">{{ worker.online ? 'מחובר ופעיל' : 'מנותק' }}</span>
          <span class="worker__meta">
            <template v-if="worker.online">{{ worker.hostname || 'מחשב הסוכן' }}</template>
            <template v-else-if="worker.last_seen">נראה לאחרונה {{ rel(worker.last_seen) }}</template>
            <template v-else>המחשב לא דיווח עדיין</template>
          </span>
        </div>
      </div>
      <p v-if="worker.online && worker.current_job" class="worker__job">{{ worker.current_job }}</p>
      <button
        v-if="worker.online"
        class="worker__update"
        type="button"
        :disabled="updating || worker.update_pending"
        @click="onUpdateWorker"
        title="מושך את הקוד העדכני ומפעיל מחדש את המחשב המקומי — בלי גיט ובלי לגעת במחשב"
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M21 12a9 9 0 1 1-2.64-6.36" /><path d="M21 3v6h-6" />
        </svg>
        <span>{{ (updating || worker.update_pending) ? 'מתעדכן…' : 'עדכן עובד' }}</span>
      </button>
      <p v-if="updateMsg" class="worker__update-msg">{{ updateMsg }}</p>
    </section>

    <!-- ── Last batch result ─────────────────────────────────── -->
    <section class="acard">
      <header class="acard__head">
        <span class="acard__eyebrow">ריצה אחרונה</span>
      </header>

      <div v-if="batch" class="batch">
        <span class="batch__pill" :class="`batch__pill--${tone}`">
          <span class="batch__pill-dot" aria-hidden="true"></span>{{ statusLabel }}
        </span>
        <div class="batch__counts">
          <span class="batch__count batch__count--ok">
            <span class="ltr-number">{{ batch.succeeded }}</span> הצליחו
          </span>
          <span class="batch__count batch__count--fail">
            <span class="ltr-number">{{ batch.failed }}</span> נכשלו
          </span>
        </div>
        <span class="batch__when">{{ rel(batch.finished_at || batch.started_at) }}</span>
        <button class="batch__cta" type="button" @click="$emit('view-results')">
          צפה בתוצאות
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M15 18l-6-6 6-6" />
          </svg>
        </button>
      </div>

      <div v-else class="batch-empty">
        <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" />
        </svg>
        <span>טרם בוצעה הורדה אוטומטית</span>
      </div>
    </section>
  </aside>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'
import { relativeHebrew } from '../../utils/relativeTime.js'

defineEmits(['view-results'])
const store = usePortalAutomationStore()

const updating = ref(false)
const updateMsg = ref('')
async function onUpdateWorker() {
  if (updating.value) return
  updating.value = true
  updateMsg.value = ''
  try {
    const res = await store.requestWorkerUpdate()
    updateMsg.value = res?.detail || 'בקשת עדכון נשלחה — המחשב יתעדכן ויופעל מחדש'
    await store.fetchWorkerStatus()
  } catch (e) {
    updateMsg.value = e?.response?.data?.detail || 'שליחת בקשת העדכון נכשלה'
  } finally {
    setTimeout(() => { updating.value = false }, 4000)
    setTimeout(() => { updateMsg.value = '' }, 9000)
  }
}

const worker = computed(() => store.workerStatus || { online: false })
const batch = computed(() => store.latestBatch)

const tone = computed(() => {
  const s = batch.value?.status
  if (s === 'failed') return 'fail'
  if (s === 'partial') return 'partial'
  if (['running', 'pending'].includes(s)) return 'live'
  return 'ok'
})
const statusLabel = computed(() => {
  const s = batch.value?.status
  if (s === 'failed') return 'נכשלה'
  if (s === 'partial') return 'הסתיימה חלקית'
  if (['running', 'pending'].includes(s)) return 'רצה כעת'
  return 'הצליחה'
})

function rel(iso) {
  return iso ? relativeHebrew(iso) : '—'
}

let poll = null
onMounted(() => {
  store.fetchWorkerStatus()
  poll = setInterval(() => store.fetchWorkerStatus(), 20000)
})
onUnmounted(() => { if (poll) clearInterval(poll) })
</script>

<style scoped>
.activity {
  display: flex;
  flex-direction: column;
  gap: 14px;
  position: sticky;
  top: 80px;
  align-self: flex-start;
}
.acard {
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg, 16px);
  padding: 16px;
  box-shadow: 0 1px 2px rgba(26, 20, 16, 0.03), 0 4px 14px rgba(26, 20, 16, 0.04);
}
.acard__head { margin-bottom: 12px; }
.acard__eyebrow {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.4px;
  color: var(--text-muted);
  text-transform: uppercase;
}

/* Worker */
.worker { display: flex; align-items: center; gap: 12px; }
.worker__dot {
  width: 12px; height: 12px;
  border-radius: 50%;
  background: var(--text-muted);
  flex-shrink: 0;
}
.worker--on .worker__dot {
  background: var(--green);
  box-shadow: 0 0 0 0 rgba(46, 132, 74, 0.5);
  animation: worker-pulse 1.8s ease-out infinite;
}
@keyframes worker-pulse {
  0%   { box-shadow: 0 0 0 0 rgba(46, 132, 74, 0.5); }
  70%  { box-shadow: 0 0 0 8px rgba(46, 132, 74, 0); }
  100% { box-shadow: 0 0 0 0 rgba(46, 132, 74, 0); }
}
.worker__body { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.worker__state { font-size: 14px; font-weight: 800; color: var(--text); }
.worker--off .worker__state { color: var(--text-muted); }
.worker__meta { font-size: 11.5px; color: var(--text-muted); }
.worker__job {
  margin: 10px 0 0;
  font-size: 11.5px;
  color: var(--text-secondary, var(--text-muted));
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 6px 9px;
}
.worker__update {
  margin-top: 10px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-secondary, var(--text-muted));
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 6px 11px;
  cursor: pointer;
  transition: background .15s, border-color .15s, transform .15s;
}
.worker__update:hover:not(:disabled) {
  background: var(--card-bg);
  border-color: var(--text-muted);
  transform: translateY(-1px);
}
.worker__update:disabled { opacity: .6; cursor: default; }
.worker__update svg { flex: none; }
.worker__update-msg {
  margin: 8px 0 0;
  font-size: 11.5px;
  color: var(--text-secondary, var(--text-muted));
}

/* Batch */
.batch { display: flex; flex-direction: column; gap: 10px; }
.batch__pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  align-self: flex-start;
  padding: 4px 11px 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  border: 1px solid transparent;
}
.batch__pill-dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
.batch__pill--ok      { background: rgba(46,132,74,0.12); color: var(--green-deep); border-color: rgba(46,132,74,0.24); }
.batch__pill--partial { background: rgba(232,114,10,0.13); color: var(--amber); border-color: rgba(232,114,10,0.26); }
.batch__pill--fail    { background: rgba(234,0,30,0.10); color: var(--red-deep); border-color: rgba(234,0,30,0.24); }
.batch__pill--live    { background: var(--tab-automation-wash); color: var(--tab-automation); border-color: rgba(14, 140, 138, 0.3); }

.batch__counts { display: flex; gap: 14px; }
.batch__count { font-size: 12.5px; font-weight: 600; color: var(--text-secondary, var(--text-muted)); }
.batch__count--ok   { color: var(--green-deep); }
.batch__count--fail { color: var(--red-deep); }
.batch__when {
  font-size: 11.5px;
  color: var(--text-muted);
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
}
.batch__cta {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-top: 2px;
  height: 36px;
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  background: var(--bg);
  color: var(--text);
  font-family: inherit;
  font-weight: 700;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, transform 0.15s;
}
.batch__cta:hover { background: var(--card-bg); border-color: var(--text-muted); transform: translateY(-1px); }

.batch-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 14px 8px;
  text-align: center;
  color: var(--text-muted);
  font-size: 12.5px;
}

@media (prefers-reduced-motion: reduce) {
  .worker--on .worker__dot { animation: none; }
  .batch__cta:hover { transform: none; }
}
</style>
