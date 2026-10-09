<template>
  <!-- Admin · תפעול: the Maslaka Gateway's release. Deploying does NOT reach the
       Gateway — an admin releases the deployed version here (the human gate in
       front of the regulator-facing machine), the Gateway self-tests it and
       switches, and rolls back if it doesn't run a healthy tick.
       app/api/maslaka_gateway.py · .claude/plans/gateway-self-update.md -->
  <section class="gw">
    <header class="gw-head">
      <h3 class="gw-title">
        <span class="gw-dot" :class="g && g.online ? 'gw-dot--on' : 'gw-dot--off'" aria-hidden="true"></span>
        גייטוויי מסלקה
      </h3>
      <span v-if="g" class="gw-status">{{ statusLine }}</span>
    </header>

    <p v-if="error" class="gw-err" role="alert">{{ error }}</p>
    <p v-else-if="!g" class="gw-muted">טוען…</p>

    <template v-else>
      <dl class="gw-versions">
        <div><dt>בשרת</dt><dd class="ltr-number">{{ short(g.deployed) }}</dd></div>
        <div><dt>שוחרר</dt><dd class="ltr-number">{{ short(g.released) || '—' }}</dd></div>
        <div :class="{ 'gw-v--ok': g.up_to_date }">
          <dt>רץ בגייטוויי</dt><dd class="ltr-number">{{ short(g.running) || '—' }}</dd>
        </div>
      </dl>
      <p v-if="g.detail && g.state !== 'ok'" class="gw-detail">{{ g.detail }}</p>

      <div class="gw-actions">
        <template v-if="!confirming">
          <button type="button" class="gw-btn" :disabled="!canRelease || busy" @click="confirming = true">
            שחרר לגייטוויי
          </button>
        </template>
        <template v-else>
          <span class="gw-confirm">לשחרר את <span class="ltr-number">{{ short(g.deployed) }}</span>?</span>
          <button type="button" class="gw-btn" :disabled="busy" @click="release">כן, לשחרר</button>
          <button type="button" class="gw-ghost" :disabled="busy" @click="confirming = false">ביטול</button>
        </template>
        <button type="button" class="gw-ghost" :disabled="busy" @click="togglePin">
          {{ g.pinned ? 'בטל נעילה' : 'נעל עדכונים' }}
        </button>
      </div>
    </template>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import api from '../../api/client.js'

const g = ref(null)
const error = ref('')
const busy = ref(false)
const confirming = ref(false)
let timer = null

const short = (v) => (v ? String(v).slice(0, 8) : '')
const STATE = {
  ok: 'תקין', trial: 'בתקופת ניסיון', updating: 'מתעדכן', needs_pip: 'נדרשת התקנת חבילות',
  update_failed: 'העדכון נכשל — נשאר בגרסה הקודמת', rolled_back: 'הוחזר לגרסה הקודמת',
}
const statusLine = computed(() => {
  const x = g.value
  if (!x.online) return x.reported_at ? 'לא מדווח — בדקו את המחשב' : 'עוד לא דיווח (לפני התקנת העדכון העצמי)'
  if (x.pinned) return 'נעול — לא יתעדכן'
  if (x.release_pending) return 'ממתין לעדכון'
  return STATE[x.state] || x.state || 'תקין'
})
const canRelease = computed(() => {
  const x = g.value
  return !!x && !x.pinned && x.deployed && (x.released !== x.deployed || x.running !== x.deployed)
})

async function load() {
  try {
    g.value = (await api.get('/maslaka/gateway/admin')).data
    error.value = ''
  } catch (e) {
    error.value = e.response?.data?.detail || 'טעינת מצב הגייטוויי נכשלה'
  }
}
async function release() {
  busy.value = true
  try {
    g.value = (await api.post('/maslaka/gateway/admin/release')).data
    confirming.value = false
  } catch (e) {
    error.value = e.response?.data?.detail || 'השחרור נכשל'
  } finally {
    busy.value = false
  }
}
async function togglePin() {
  busy.value = true
  try {
    g.value = (await api.post('/maslaka/gateway/admin/pin', { pinned: !g.value.pinned })).data
  } catch (e) {
    error.value = e.response?.data?.detail || 'הפעולה נכשלה'
  } finally {
    busy.value = false
  }
}
onMounted(() => { load(); timer = setInterval(load, 20000) })
onBeforeUnmount(() => clearInterval(timer))
</script>

<style scoped>
.gw { display: flex; flex-direction: column; gap: 12px; padding: 16px 18px; background: var(--card-bg, #fff);
  border: 1px solid var(--border-subtle, #E5E5E5); border-radius: 14px; box-shadow: var(--shadow-sm); }
.gw-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.gw-title { margin: 0; display: flex; align-items: center; gap: 8px; font-size: 16px; font-weight: 800; color: var(--text, #181818); }
.gw-dot { width: 9px; height: 9px; border-radius: 50%; }
.gw-dot--on { background: var(--green, #2E844A); box-shadow: 0 0 0 4px color-mix(in srgb, var(--green, #2E844A) 18%, transparent); }
.gw-dot--off { background: var(--text-muted, #999); }
.gw-status { font-size: 13px; font-weight: 600; color: var(--text-secondary, #706E6B); }
.gw-muted, .gw-detail { margin: 0; font-size: 13px; color: var(--text-muted, #999); }
.gw-detail { padding: 8px 12px; border-radius: 10px; background: var(--amber-light, #FBF4DC); color: var(--amber, #8A6300); }
.gw-err { margin: 0; font-size: 13px; color: var(--red, #C23934); }
.gw-versions { margin: 0; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border: 1px solid var(--border-subtle, #E5E5E5);
  border-radius: 12px; overflow: hidden; }
.gw-versions > div { display: flex; flex-direction: column; align-items: flex-start; gap: 2px; padding: 10px 14px; }
.gw-versions > div + div { border-inline-start: 1px solid var(--border-subtle, #E5E5E5); }
.gw-versions dt { font-size: 12px; color: var(--text-muted, #999); }
.gw-versions dd { margin: 0; font-size: 17px; font-weight: 800; font-family: ui-monospace, monospace; color: var(--text, #181818); }
.gw-v--ok dd { color: var(--green, #2E844A); }
.gw-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.gw-confirm { font-size: 13.5px; font-weight: 600; color: var(--text, #181818); }
.gw-btn { padding: 8px 18px; border: none; border-radius: 10px; background: var(--primary, #181818); color: #fff; cursor: pointer;
  font-family: inherit; font-size: 13.5px; font-weight: 700; transition: transform 0.15s, background 0.15s; }
.gw-btn:hover:not(:disabled) { transform: translateY(-1px); background: var(--primary-deep, #000); }
.gw-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.gw-ghost { padding: 8px 16px; border: 1px solid var(--border, #DDD); border-radius: 10px; background: var(--card-bg, #fff);
  cursor: pointer; font-family: inherit; font-size: 13px; font-weight: 600; color: var(--text-secondary, #706E6B); }
.gw-ghost:hover:not(:disabled) { color: var(--text, #181818); }
@media (max-width: 560px) { .gw-versions { grid-template-columns: 1fr; } .gw-versions > div + div { border-inline-start: none; border-top: 1px solid var(--border-subtle, #E5E5E5); } }
</style>
