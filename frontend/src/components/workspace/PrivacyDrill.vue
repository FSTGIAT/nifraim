<template>
  <!-- לא להעלות: numbers whose calls never leave the agent's phone, and the personal calls
       that were hidden (by the summary, by the agent, or because of the number). Same drill
       shell as the other contacts apps — grows out of its round icon. -->
  <DataModal :open="open" :origin="origin" title="לא להעלות" :badge="numbers.length" accent="var(--tab-emails)" size="sm" @close="emit('close')">
    <template #head-action>
      <button type="button" class="pd-head-btn" :aria-expanded="adding" @click="toggleAdd">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
        מספר
      </button>
    </template>
    <div class="pd">
      <p class="pd-note">שיחות עם המספרים האלה לא יוצאות מהטלפון. שיחה אישית שהגיעה מוסתרת, וההקלטה שלה נמחקת.</p>

      <form v-if="adding" class="pd-add" @submit.prevent="add">
        <input ref="phoneEl" v-model.trim="phone" type="tel" inputmode="tel" dir="ltr" placeholder="050-0000000" aria-label="מספר טלפון" />
        <input v-model.trim="label" placeholder="שם (אמא, אח…)" aria-label="שם" />
        <button type="submit" class="pd-btn" :disabled="digits(phone).length < 9 || busy">הוספה</button>
      </form>
      <p v-if="error" class="pd-err" role="alert">{{ error }}</p>

      <ul v-if="numbers.length" class="pd-list">
        <li v-for="n in numbers" :key="n.id" class="pd-row">
          <svg class="pd-ico" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M10.7 13.3a16 16 0 0 0 3.4 2.6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1M5.2 13.8A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8 9.9" /><path d="M22 2 2 22" />
          </svg>
          <span class="pd-id"><strong>{{ n.label || 'מספר פרטי' }}</strong><small class="ltr-number">{{ fmt(n.phone) }}</small></span>
          <button type="button" class="pd-x" :aria-label="'הסרה של ' + (n.label || n.phone)" @click="remove(n.id)">הסרה</button>
        </li>
      </ul>
      <p v-else-if="!adding" class="pd-empty">אין מספרים ברשימה.</p>

      <template v-if="hidden.length">
        <h5 class="pd-sec">שיחות אישיות שהוסתרו <span class="pd-sec-n ltr-number">{{ hidden.length }}</span></h5>
        <ul class="pd-list">
          <li v-for="c in hidden" :key="c.id" class="pd-row">
            <span class="pd-id">
              <strong>{{ c.title }}</strong>
              <small><span class="ltr-number">{{ when(c.at) }}</span><template v-if="c.phone"> · <span class="ltr-number">{{ fmt(c.phone) }}</span></template> · {{ REASON[c.reason] || 'אישית' }}</small>
            </span>
            <button type="button" class="pd-x" @click="restore(c.id)">החזרה</button>
          </li>
        </ul>
      </template>
    </div>
  </DataModal>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'
import DataModal from './DataModal.vue'
import api from '../../api/client.js'

const props = defineProps({
  open: { type: Boolean, default: false },
  origin: { type: null, default: null },
})
const emit = defineEmits(['close', 'changed'])
const REASON = { summary: 'זוהתה כאישית', agent: 'סומנה כאישית', blocked: 'מספר ברשימה' }

const numbers = ref([])
const hidden = ref([])
const adding = ref(false)
const phone = ref('')
const label = ref('')
const busy = ref(false)
const error = ref('')
const phoneEl = ref(null)
const digits = (x) => String(x || '').replace(/\D/g, '')
const fmt = (p) => { const d = digits(p); return d.length === 10 ? `${d.slice(0, 3)}-${d.slice(3)}` : p }
const when = (iso) => { const d = new Date(iso); return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('he-IL', { day: '2-digit', month: '2-digit' }) }

async function load() {
  try {
    const { data } = await api.get('/blocked-phones')
    numbers.value = data.numbers || []
    hidden.value = data.hidden_calls || []
    emit('changed', numbers.value.length)
  } catch { /* the drill shows what it has */ }
}
async function toggleAdd() {
  adding.value = !adding.value
  error.value = ''
  if (adding.value) { await nextTick(); phoneEl.value?.focus() }
}
async function add() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    await api.post('/blocked-phones', { phone: phone.value, label: label.value })
    phone.value = ''
    label.value = ''
    adding.value = false
    await load()
  } catch (e) {
    error.value = e?.response?.data?.detail || 'ההוספה נכשלה'
  } finally {
    busy.value = false
  }
}
async function remove(id) { await api.delete(`/blocked-phones/${id}`); await load() }
async function restore(id) { await api.post(`/blocked-phones/calls/${id}/restore`); await load() }

watch(() => props.open, (o) => { if (o) { adding.value = false; error.value = ''; load() } })
defineExpose({ load })
</script>

<style scoped>
.pd { display: flex; flex-direction: column; gap: 10px; }
.pd-note { margin: 0; font-size: 13px; line-height: 1.6; color: var(--text-muted); }
.pd-head-btn { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border: none; border-radius: 9px; cursor: pointer;
  background: var(--tab-emails-ink); color: #fff; font-family: inherit; font-size: 13px; font-weight: 700;
  box-shadow: 0 3px 10px color-mix(in srgb, var(--tab-emails) 24%, transparent); }
.pd-add { display: grid; grid-template-columns: 1fr 1fr auto; gap: 8px; }
.pd-add input { min-width: 0; padding: 9px 11px; font-family: inherit; font-size: 14px; color: var(--text); background: var(--card-bg);
  border: 1px solid var(--border); border-radius: var(--radius-sm); }
.pd-add input[dir='ltr'] { text-align: right; }
.pd-add input:focus { outline: none; border-color: var(--tab-emails); box-shadow: 0 0 0 3px color-mix(in srgb, var(--tab-emails) 18%, transparent); }
.pd-btn { padding: 0 16px; border: none; border-radius: 10px; cursor: pointer; background: var(--tab-emails-ink); color: #fff;
  font-family: inherit; font-size: 13.5px; font-weight: 700; }
.pd-btn:disabled { opacity: 0.45; cursor: not-allowed; }
.pd-err { margin: 0; font-size: 12.5px; color: var(--red-deep, #C23934); }
.pd-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.pd-row { display: flex; align-items: center; gap: 12px; padding: 11px 14px; border: 1px solid var(--border-subtle); border-radius: 12px; background: var(--card-bg); }
.pd-ico { flex: none; color: var(--tab-emails-ink); }
.pd-id { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.pd-id strong { font-size: 14px; font-weight: 700; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pd-id small { font-size: 12.5px; color: var(--text-muted); }
.pd-x { flex: none; padding: 5px 11px; border-radius: 8px; border: 1px solid var(--border); background: var(--card-bg); cursor: pointer;
  font-family: inherit; font-size: 12.5px; font-weight: 600; color: var(--text-secondary); }
.pd-x:hover { color: var(--text); border-color: var(--text-muted); }
.pd-empty { margin: 6px 0; font-size: 13.5px; color: var(--text-muted); }
.pd-sec { margin: 8px 0 0; display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 700; color: var(--text-secondary); }
.pd-sec-n { font-size: 11px; font-weight: 800; padding: 1px 7px; border-radius: 99px; background: var(--tab-emails-wash); color: var(--tab-emails-ink); }
@media (max-width: 420px) { .pd-add { grid-template-columns: 1fr; } }
</style>
