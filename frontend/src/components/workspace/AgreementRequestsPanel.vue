<template>
  <!-- Setup wizard · מדף ההסכמים: Nifraim emails each insurer (from the agent's
       own mailbox) asking for the commission agreement, then follows the reply
       and loads the PDF to the shelf. Lives INSIDE the wizard — no navigation. -->
  <div class="arp">
    <div v-if="loading && !data" class="arp-loading"><span class="arp-spin"></span>טוען…</div>

    <!-- mailbox not ready -->
    <div v-else-if="data && !data.can_send" class="arp-gate">
      <!-- the whole idea in one glance: request → insurer answers → agreement loaded -->
      <ol class="arp-flow" aria-hidden="true">
        <li class="arp-flow-step">
          <span class="arp-flow-ico">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg>
          </span>
          <span class="arp-flow-lbl">שולחים בקשה</span>
        </li>
        <li class="arp-flow-step">
          <span class="arp-flow-ico">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 22h18"/><path d="M6 18v-7M10 18v-7M14 18v-7M18 18v-7"/><path d="m12 2 8 5H4Z"/></svg>
          </span>
          <span class="arp-flow-lbl">החברה עונה</span>
        </li>
        <li class="arp-flow-step arp-flow-step--end">
          <span class="arp-flow-ico">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="m9 15 2 2 4-4"/></svg>
          </span>
          <span class="arp-flow-lbl">ההסכם נטען</span>
        </li>
      </ol>
      <strong class="arp-gate-title">בקשה במייל — ההסכם חוזר לבד</strong>
      <span v-if="data.reason === 'not_connected'" class="arp-gate-sub">קודם מחברים את <span dir="ltr">Nifraim Mail Agent</span>.</span>
      <span v-else class="arp-gate-sub">שליחה אוטומטית זמינה כרגע מתיבת Gmail.</span>
      <button type="button" class="arp-btn" @click="$emit('go-mail')">לחיבור Mail Agent</button>
    </div>

    <!-- ready: one row per company -->
    <template v-else-if="data">
      <p class="arp-from">נשלח מ-<span class="ltr-number">{{ data.mailbox_address }}</span></p>
      <ul class="arp-list">
        <li v-for="row in rows" :key="row.company" class="arp-row">
          <span class="arp-co"><CompanyLogo :company="row.company" :size="24" /><span>{{ row.company }}</span></span>
          <input
            v-model.trim="row.email"
            class="arp-input"
            type="email"
            dir="ltr"
            inputmode="email"
            :placeholder="'contact@' + 'company.co.il'"
            :aria-label="`מייל איש הקשר ב${row.company}`"
          />
          <span v-if="row.status" class="arp-chip" :class="'arp-chip--' + row.status">{{ STATUS[row.status] }}</span>
        </li>
      </ul>
      <p v-if="message" class="arp-msg" :class="{ 'arp-msg--err': messageErr }">{{ message }}</p>
      <div class="arp-actions">
        <button type="button" class="arp-btn" :disabled="sending || !toSend.length" @click="send">
          <span v-if="sending" class="arp-spin arp-spin--light"></span>
          {{ sending ? 'שולח…' : toSend.length ? `שליחת בקשות (${toSend.length})` : 'הזינו מייל לחברה אחת לפחות' }}
        </button>
        <button v-if="data.sent_count" type="button" class="arp-ghost" :disabled="checking" @click="check">
          {{ checking ? 'בודק…' : 'בדיקת תשובות' }}
        </button>
      </div>
    </template>

    <button type="button" class="arp-link" @click="$emit('open-shelf')">או העלאה ידנית במדף ההסכמים</button>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../../api/client.js'
import CompanyLogo from './CompanyLogo.vue'

const emit = defineEmits(['go-mail', 'open-shelf', 'changed'])

const STATUS = { sent: 'נשלח', replied: 'התקבלה תשובה', imported: 'הסכם נטען', failed: 'שליחה נכשלה' }
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const data = ref(null)
const rows = ref([])
const loading = ref(false)
const sending = ref(false)
const checking = ref(false)
const message = ref('')
const messageErr = ref(false)

function apply(d) {
  data.value = d
  // keep what the agent is typing; refresh statuses
  const typed = Object.fromEntries(rows.value.map((r) => [r.company, r.email]))
  rows.value = (d.companies || []).map((c) => ({ ...c, email: typed[c.company] ?? c.email ?? '', sentEmail: c.status ? c.email : null }))
}

async function load() {
  loading.value = true
  try { apply((await api.get('/agreement-requests')).data) } catch (_) { /* keep last */ } finally { loading.value = false }
}

// A row goes out when it has a valid address that hasn't already been sent to.
const toSend = computed(() => rows.value.filter((r) =>
  EMAIL_RE.test(r.email || '') && !(r.sentEmail && r.sentEmail.toLowerCase() === r.email.toLowerCase() && r.status !== 'failed'),
))

async function send() {
  sending.value = true
  message.value = ''
  try {
    const items = toSend.value.map((r) => ({ company: r.company, email: r.email, contact_name: r.contact_name || null }))
    const res = (await api.post('/agreement-requests/send', { items })).data
    apply(res)
    const ok = res.results.filter((x) => x.ok).length
    const bad = res.results.length - ok
    messageErr.value = bad > 0
    message.value = bad ? `נשלחו ${ok}, ${bad} נכשלו` : `נשלחו ${ok} בקשות — נעדכן כאן כשההסכמים יחזרו`
    emit('changed')
  } catch (e) {
    messageErr.value = true
    message.value = e.response?.data?.detail === 'not_connected' ? 'המייל לא מחובר' : 'השליחה נכשלה — נסו שוב'
  } finally {
    sending.value = false
  }
}

async function check() {
  checking.value = true
  try {
    const res = (await api.post('/agreement-requests/check')).data
    apply(res)
    messageErr.value = false
    message.value = res.loaded ? `נטענו ${res.loaded} הסכמים חדשים` : 'עדיין אין הסכמים חדשים'
    if (res.loaded) emit('changed')
  } catch (_) {
    messageErr.value = true
    message.value = 'הבדיקה נכשלה'
  } finally {
    checking.value = false
  }
}

onMounted(load)
defineExpose({ load })
</script>

<style scoped>
.arp { display: flex; flex-direction: column; gap: 10px; }
.arp-loading { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text-secondary, #706E6B); }
.arp-from { margin: 0; font-size: 13px; color: var(--text-secondary, #706E6B); }
.arp-gate {
  display: flex; flex-direction: column; align-items: flex-start; gap: 8px;
  padding: 20px 22px; border-radius: 16px;
  background: radial-gradient(120% 140% at 100% 0%, #F3EAF7 0%, #FBF8FD 55%, #fff 100%);
  border: 1px solid #EADCF1;
}
.arp-flow {
  list-style: none; margin: 0 0 10px; padding: 0; align-self: stretch;
  display: grid; grid-template-columns: repeat(3, 1fr); position: relative;
}
/* the connector runs behind the icons, centre to centre */
.arp-flow::before {
  content: ''; position: absolute; top: 24px; right: 16.66%; left: 16.66%; height: 2px;
  background: repeating-linear-gradient(90deg, #C9A8D8 0 6px, transparent 6px 11px);
  animation: arpDash 1.4s linear infinite;
}
@keyframes arpDash { to { background-position: -11px 0; } }
.arp-flow-step { position: relative; display: flex; flex-direction: column; align-items: center; gap: 8px; }
.arp-flow-ico {
  width: 48px; height: 48px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  background: #fff; color: #8E44AD; border: 1.5px solid #E4D3EC;
  box-shadow: 0 6px 16px rgba(142, 68, 173, 0.14);
}
.arp-flow-step--end .arp-flow-ico { background: #6B2F86; color: #fff; border-color: #6B2F86; box-shadow: 0 8px 20px rgba(107, 47, 134, 0.32); }
.arp-flow-lbl { font-size: 12.5px; font-weight: 700; color: #6B2F86; white-space: nowrap; }
.arp-gate-title { font-size: 17px; font-weight: 800; color: var(--text, #181818); }
.arp-gate-sub { font-size: 14px; color: var(--text-secondary, #3E3E3C); margin-bottom: 6px; }
.arp-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; max-height: 236px; overflow-y: auto; }
.arp-row {
  display: grid; grid-template-columns: 118px minmax(0, 1fr) auto; align-items: center; gap: 8px;
  padding: 6px 8px; border-radius: 10px; background: #fff; border: 1px solid #EDE6F1;
}
.arp-co { display: inline-flex; align-items: center; gap: 7px; min-width: 0; font-size: 13.5px; font-weight: 700; color: var(--text, #181818); }
.arp-co > span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.arp-input {
  min-width: 0; height: 32px; padding: 0 10px; border-radius: 8px; border: 1px solid var(--border-subtle, #E5E5E5);
  font-family: inherit; font-size: 13px; background: #FBF8FD; text-align: left;
}
.arp-input:focus { outline: none; border-color: #8E44AD; background: #fff; box-shadow: 0 0 0 3px rgba(142, 68, 173, 0.12); }
.arp-chip { font-size: 11.5px; font-weight: 800; padding: 3px 9px; border-radius: 999px; white-space: nowrap; }
.arp-chip--sent { background: #F3EAF7; color: #6B2F86; }
.arp-chip--replied { background: var(--amber-light, #FBF4DC); color: var(--amber, #8A6300); }
.arp-chip--imported { background: #EAF5EE; color: #2E844A; }
.arp-chip--failed { background: rgba(234, 0, 30, 0.08); color: #B91C1C; }
.arp-msg { margin: 0; font-size: 13px; font-weight: 600; color: #2E844A; }
.arp-msg--err { color: #B91C1C; }
.arp-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.arp-btn {
  display: inline-flex; align-items: center; gap: 8px; height: 40px; padding: 0 18px; border: none; border-radius: 10px;
  background: #6B2F86; color: #fff; font-family: inherit; font-size: 14px; font-weight: 700; cursor: pointer;
  box-shadow: 0 4px 12px rgba(142, 68, 173, 0.33); transition: transform 0.15s ease, filter 0.15s ease;
}
.arp-btn:hover:not(:disabled) { transform: translateY(-1px); filter: brightness(1.06); }
.arp-btn:disabled { opacity: 0.6; cursor: default; box-shadow: none; }
.arp-ghost {
  height: 40px; padding: 0 14px; border-radius: 10px; border: 1px solid #D9C6E3; background: #fff;
  color: #6B2F86; font-family: inherit; font-size: 13.5px; font-weight: 700; cursor: pointer;
}
.arp-link {
  align-self: flex-start; padding: 0; border: none; background: none; cursor: pointer;
  font-family: inherit; font-size: 12.5px; color: var(--text-secondary, #706E6B); text-decoration: underline;
}
.arp-spin { width: 14px; height: 14px; border-radius: 50%; border: 2px solid rgba(107, 47, 134, 0.25); border-top-color: #6B2F86; animation: arpSpin 0.8s linear infinite; }
.arp-spin--light { border-color: rgba(255, 255, 255, 0.35); border-top-color: #fff; }
@keyframes arpSpin { to { transform: rotate(360deg); } }
</style>
