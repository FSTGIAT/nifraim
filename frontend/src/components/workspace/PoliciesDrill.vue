<template>
  <!-- פוליסות: every customer whose policies we hold — fetched from הר הביטוח by Nifra ("תביא לי מהר
       הביטוח …") or uploaded as a policy PDF (Claude turns it into Markdown the agent can ask about).
       Same drill shell as the other contacts apps; grows out of its round icon. -->
  <DataModal :open="open" :origin="origin" title="פוליסות" :badge="customers.length || null" accent="var(--tab-emails)" size="lg" @close="emit('close')">
    <template #head-action>
      <button type="button" class="po-head-btn" :aria-expanded="adding" @click="toggleAdd">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
        פוליסה PDF
      </button>
    </template>

    <div class="po">
      <p class="po-note">
        לשליפת התיק הביטוחי מהר הביטוח — כתבו ל-Nifra: <b>"תביא לי מהר הביטוח"</b> + ת.ז, תאריך לידה ותאריך הנפקה.
        העובד מתחבר, הקוד נקלט לבד, והפוליסות מגיעות לכאן.
      </p>

      <form v-if="adding" class="po-add" @submit.prevent>
        <input v-model.trim="uploadId" inputmode="numeric" dir="ltr" placeholder="ת.ז הלקוח (לא חובה)" aria-label="ת.ז הלקוח" />
        <label class="po-btn" :class="{ 'is-busy': uploading }">
          <input ref="fileEl" type="file" accept="application/pdf" multiple hidden :disabled="uploading" @change="onFiles" />
          {{ uploading ? 'מעלה…' : 'בחירת PDF' }}
        </label>
      </form>
      <p v-if="adding" class="po-hint">בלי ת.ז — הלקוח מזוהה מהפוליסה עצמה. קריאת פוליסה ארוכה לוקחת כדקה–שתיים.</p>
      <p v-if="error" class="po-err" role="alert">{{ error }}</p>

      <ul v-if="customers.length" class="po-list">
        <li v-for="c in customers" :key="c.id_number" class="po-card" :class="{ 'is-open': openId === c.id_number }">
          <button type="button" class="po-row" :aria-expanded="openId === c.id_number" @click="toggle(c.id_number)">
            <span class="po-id">
              <strong>{{ c.customer_name || 'ת.ז ' + c.id_number }}</strong>
              <small><span class="ltr-number">{{ c.id_number }}</span><template v-if="c.totals.companies.length"> · {{ c.totals.companies.slice(0, 4).join(' · ') }}</template></small>
            </span>
            <span v-if="c.processing" class="po-pill po-pill--wait">בעיבוד</span>
            <span v-if="c.totals.policies" class="po-pill"><span class="ltr-number">{{ c.totals.policies }}</span> פוליסות</span>
            <span v-if="c.totals.monthly_premium_active >= 0.5" class="po-amt">
              <b class="ltr-number">{{ money(c.totals.monthly_premium_active) }}</b>
              <small>פרמיה חודשית</small>
            </span>
            <svg class="po-chev" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m15 18-6-6 6-6" /></svg>
          </button>

          <div class="po-fold">
            <div class="po-fold-inner">
              <template v-if="detail[c.id_number]">
                <p v-if="detail[c.id_number].fetched_at" class="po-meta">
                  נשלף מהר הביטוח ב-<span class="ltr-number">{{ day(detail[c.id_number].fetched_at) }}</span>
                  · <span class="ltr-number">{{ detail[c.id_number].totals.active_policies }}</span> בתוקף מתוך <span class="ltr-number">{{ detail[c.id_number].totals.policies }}</span>
                </p>
                <section v-if="detail[c.id_number].changes" class="po-changes">
                  <h5 class="po-sec">מה השתנה מאז השליפה הקודמת</h5>
                  <p class="po-change-sum">{{ detail[c.id_number].changes.summary_he }}</p>
                  <ul class="po-change-list">
                    <li v-for="(p, k) in detail[c.id_number].changes.new_policies" :key="'n' + k"><b>חדשה</b> {{ p.branch }} — {{ p.sub_branches.join(' + ') }} · {{ p.company }}<template v-if="p.policy_number"> · <span class="ltr-number">{{ p.policy_number }}</span></template></li>
                    <li v-for="(p, k) in detail[c.id_number].changes.removed_policies" :key="'r' + k"><b>לא מופיעה יותר</b> {{ p.branch }} — {{ p.sub_branches.join(' + ') }} · {{ p.company }}<template v-if="p.policy_number"> · <span class="ltr-number">{{ p.policy_number }}</span></template></li>
                    <li v-for="(x, k) in detail[c.id_number].changes.premium_changes" :key="'p' + k"><b>פרמיה</b> {{ x.company }} {{ x.coverage || '' }} {{ x.sub_branch || '' }} · <span class="ltr-number">{{ money(x.old) }} → {{ money(x.new) }}</span></li>
                    <li v-for="(x, k) in detail[c.id_number].changes.period_changes" :key="'t' + k"><b>תקופה</b> {{ x.company }} {{ x.sub_branch || '' }} · <span class="ltr-number">{{ x.old }} → {{ x.new }}</span></li>
                  </ul>
                </section>
                <template v-for="(group, dom) in byDomain(detail[c.id_number].policies)" :key="dom">
                  <h5 class="po-sec">{{ dom }}</h5>
                  <ul class="po-pols">
                    <li v-for="(p, k) in group" :key="k" class="po-pol" :class="{ 'is-ended': !p.active }">
                      <span class="po-pol-main">
                        <strong>{{ p.branch }} — {{ p.sub_branches.join(' + ') }}</strong>
                        <small>{{ p.company_short }}<template v-if="p.policy_number"> · פוליסה <span class="ltr-number">{{ p.policy_number }}</span></template><template v-if="p.period"> · <span class="ltr-number">{{ p.period }}</span></template><template v-if="!p.active"> · הסתיימה</template></small>
                      </span>
                      <span v-if="p.monthly_premium >= 0.5" class="po-pol-amt ltr-number">{{ money(p.monthly_premium) }}</span>
                    </li>
                  </ul>
                </template>
                <template v-if="detail[c.id_number].history.length > 1">
                  <h5 class="po-sec">שליפות קודמות</h5>
                  <ul class="po-docs">
                    <li v-for="h in detail[c.id_number].history.slice(1)" :key="h.request_id">
                      <button type="button" class="po-doc" :disabled="!h.document_id" @click="openDoc(h.document_id, $event.currentTarget)">
                        <span><span class="ltr-number">{{ day(h.fetched_at) }}</span> · <span class="ltr-number">{{ h.coverages || 0 }}</span> כיסויים</span>
                        <small>{{ h.changes || 'שליפה ראשונה' }}</small>
                      </button>
                    </li>
                  </ul>
                </template>
                <template v-if="detail[c.id_number].documents.length">
                  <h5 class="po-sec">מסמכים</h5>
                  <ul class="po-docs">
                    <li v-for="d in detail[c.id_number].documents" :key="d.id">
                      <button type="button" class="po-doc" :disabled="d.status !== 'ready'" @click="openDoc(d.id, $event.currentTarget)">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6M8 13h8M8 17h5" /></svg>
                        <span>{{ d.title }}</span>
                        <small>{{ SRC[d.source] }}{{ d.status === 'processing' ? ' · בעיבוד…' : d.status === 'failed' ? ' · נכשל' : '' }}</small>
                      </button>
                    </li>
                  </ul>
                </template>
              </template>
              <p v-else class="po-meta">טוען…</p>
            </div>
          </div>
        </li>
      </ul>
      <p v-else-if="loaded" class="po-empty">עוד אין פוליסות. שלפו מהר הביטוח דרך Nifra או העלו PDF של פוליסה.</p>

      <template v-if="unassigned.length">
        <h5 class="po-sec">פוליסות שהלקוח שלהן לא זוהה</h5>
        <ul class="po-docs">
          <li v-for="d in unassigned" :key="d.id">
            <button type="button" class="po-doc" :disabled="d.status !== 'ready'" @click="openDoc(d.id, $event.currentTarget)">
              <span>{{ d.title }}</span>
              <small>{{ d.status === 'processing' ? 'בעיבוד…' : d.status === 'failed' ? (d.error || 'נכשל') : d.company || '' }}</small>
            </button>
          </li>
        </ul>
      </template>
    </div>
  </DataModal>

  <!-- one policy document, rendered from its Markdown -->
  <DataModal :open="!!doc" :origin="docOrigin" :layer="1020" :title="doc?.title || ''" accent="var(--tab-emails)" size="lg" @close="doc = null">
    <template #head-action>
      <button v-if="doc?.has_file" type="button" class="po-ghost" @click="openFile(doc.id)">PDF מקורי</button>
      <button v-if="doc?.source === 'pdf'" type="button" class="po-ghost po-ghost--danger" @click="removeDoc(doc.id)">מחיקה</button>
    </template>
    <!-- eslint-disable-next-line vue/no-v-html -- mdToHtml escapes every text node -->
    <article v-if="doc" class="po-md" v-html="mdToHtml(doc.markdown)"></article>
  </DataModal>
</template>

<script setup>
import { onBeforeUnmount, reactive, ref, watch } from 'vue'
import DataModal from './DataModal.vue'
import api from '../../api/client.js'
import { mdToHtml } from '../../utils/mdLite.js'

const props = defineProps({
  open: { type: Boolean, default: false },
  origin: { type: null, default: null },
})
const emit = defineEmits(['close', 'changed'])
const SRC = { harb_portfolio: 'הר הביטוח', harb_policy: 'הר הביטוח — פרטי פוליסה', pdf: 'PDF' }

const customers = ref([])
const unassigned = ref([])
const loaded = ref(false)
const detail = reactive({})
const openId = ref('')
const adding = ref(false)
const uploadId = ref('')
const uploading = ref(false)
const error = ref('')
const fileEl = ref(null)
const doc = ref(null)
const docOrigin = ref(null)
let timer = null

const money = (v) => '₪' + Number(v).toLocaleString('he-IL', { maximumFractionDigits: v < 100 ? 2 : 0 })
const day = (iso) => { const d = new Date(iso); return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('he-IL') }
function byDomain(pols) {
  const out = {}
  for (const p of pols) (out[p.domain || 'אחר'] ||= []).push(p)
  return out
}

async function load() {
  try {
    const { data } = await api.get('/policies/customers')
    customers.value = data.customers || []
    unassigned.value = data.unassigned || []
    emit('changed', customers.value.length)
    if (openId.value) await loadDetail(openId.value)
  } catch { /* the drill shows what it has */ } finally { loaded.value = true }
  schedule()
}
async function loadDetail(id) {
  try { detail[id] = (await api.get(`/policies/customers/${id}`)).data } catch { /* keep the old one */ }
}
// a PDF is converted in the background (~1–2 min) — refresh while one is processing
function schedule() {
  clearTimeout(timer)
  const busy = customers.value.some((c) => c.processing) || unassigned.value.some((d) => d.status === 'processing')
  if (props.open && busy) timer = setTimeout(load, 6000)
}
async function toggle(id) {
  openId.value = openId.value === id ? '' : id
  if (openId.value) await loadDetail(id)
}
function toggleAdd() { adding.value = !adding.value; error.value = '' }
async function onFiles(e) {
  const files = [...(e.target.files || [])]
  if (!files.length) return
  uploading.value = true
  error.value = ''
  try {
    for (const f of files) {
      const fd = new FormData()
      fd.append('file', f)
      fd.append('id_number', uploadId.value)
      await api.post('/policies/upload', fd)
    }
    adding.value = false
    uploadId.value = ''
    await load()
  } catch (err) {
    error.value = err?.response?.data?.detail || 'ההעלאה נכשלה'
  } finally {
    uploading.value = false
    if (fileEl.value) fileEl.value.value = ''
  }
}
async function openDoc(id, el) {
  docOrigin.value = el
  try { doc.value = (await api.get(`/policies/documents/${id}`)).data } catch { error.value = 'המסמך לא נפתח' }
}
async function openFile(id) {
  const { data } = await api.get(`/policies/documents/${id}/file`, { responseType: 'blob' })
  window.open(URL.createObjectURL(data), '_blank', 'noopener')
}
async function removeDoc(id) {
  await api.delete(`/policies/documents/${id}`)
  doc.value = null
  await load()
}

watch(() => props.open, (o) => { if (o) { adding.value = false; error.value = ''; load() } else clearTimeout(timer) })
onBeforeUnmount(() => clearTimeout(timer))
defineExpose({ load })
</script>

<style scoped>
.po { display: flex; flex-direction: column; gap: 10px; }
.po-note { margin: 0; font-size: 13px; line-height: 1.6; color: var(--text-muted); }
.po-note b { color: var(--text); font-weight: 700; }
.po-head-btn { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border: none; border-radius: 9px; cursor: pointer;
  background: var(--tab-emails-ink); color: #fff; font-family: inherit; font-size: 13px; font-weight: 700;
  box-shadow: 0 3px 10px color-mix(in srgb, var(--tab-emails) 24%, transparent); }
.po-add { display: grid; grid-template-columns: 1fr auto; gap: 8px; }
.po-add input { min-width: 0; padding: 9px 11px; font-family: inherit; font-size: 14px; color: var(--text); background: var(--card-bg);
  border: 1px solid var(--border); border-radius: var(--radius-sm); text-align: right; }
.po-add input:focus { outline: none; border-color: var(--tab-emails); box-shadow: 0 0 0 3px color-mix(in srgb, var(--tab-emails) 18%, transparent); }
.po-btn { display: inline-flex; align-items: center; padding: 0 16px; border-radius: 10px; cursor: pointer; background: var(--tab-emails-ink); color: #fff;
  font-size: 13.5px; font-weight: 700; }
.po-btn.is-busy { opacity: .6; cursor: progress; }
.po-hint { margin: -4px 0 0; font-size: 12px; color: var(--text-muted); }
.po-err { margin: 0; font-size: 12.5px; color: var(--red-deep, #C23934); }
.po-list, .po-pols, .po-docs { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.po-card { border: 1px solid var(--border-subtle); border-radius: 12px; background: var(--card-bg); overflow: hidden; }
.po-row { width: 100%; display: flex; align-items: center; gap: 12px; padding: 12px 14px; background: none; border: none; cursor: pointer;
  font-family: inherit; text-align: right; color: inherit; }
.po-row:hover { background: var(--bg); }
.po-id { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.po-id strong { font-size: 14px; font-weight: 700; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.po-id small { font-size: 12.5px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.po-pill { flex: none; font-size: 12px; font-weight: 700; padding: 2px 9px; border-radius: 99px; background: var(--tab-emails-wash); color: var(--tab-emails-ink); }
.po-pill--wait { background: var(--amber-light); color: var(--amber); }
.po-amt { flex: none; display: flex; flex-direction: column; align-items: flex-end; min-width: 84px; }
.po-amt b { font-size: 15px; font-weight: 800; color: var(--text); }
.po-amt small { font-size: 11px; color: var(--text-muted); }
.po-chev { flex: none; color: var(--text-muted); transition: transform .25s ease; }
.po-card.is-open .po-chev { transform: rotate(-90deg); }
.po-fold { display: grid; grid-template-rows: 0fr; transition: grid-template-rows .3s ease; }
.po-card.is-open .po-fold { grid-template-rows: 1fr; }
.po-fold-inner { overflow: hidden; padding: 0 14px; }
.po-card.is-open .po-fold-inner { padding: 0 14px 14px; }
.po-meta { margin: 0 0 6px; font-size: 12.5px; color: var(--text-muted); }
.po-sec { margin: 10px 0 6px; font-size: 13px; font-weight: 700; color: var(--text-secondary); }
.po-pol { display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 10px; background: var(--bg); }
.po-pol.is-ended { opacity: .6; }
.po-pol-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.po-pol-main strong { font-size: 13px; font-weight: 700; color: var(--text); }
.po-pol-main small { font-size: 12px; color: var(--text-muted); }
.po-pol-amt { flex: none; font-size: 13px; font-weight: 700; color: var(--text); }
.po-doc { width: 100%; display: flex; align-items: center; gap: 8px; padding: 9px 11px; border: 1px solid var(--border-subtle); border-radius: 10px;
  background: var(--card-bg); cursor: pointer; font-family: inherit; text-align: right; color: var(--text); }
.po-doc:hover:not(:disabled) { border-color: var(--tab-emails); }
.po-doc:disabled { cursor: default; opacity: .7; }
.po-doc svg { flex: none; color: var(--tab-emails-ink); }
.po-doc span { flex: 1; min-width: 0; font-size: 13px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.po-doc small { flex: none; font-size: 12px; color: var(--text-muted); }
.po-empty { margin: 6px 0; font-size: 13.5px; color: var(--text-muted); }
.po-changes { margin: 4px 0 6px; padding: 10px 12px; border-radius: 10px; background: var(--tab-emails-wash); }
.po-changes .po-sec { margin-top: 0; color: var(--tab-emails-ink); }
.po-change-sum { margin: 0 0 6px; font-size: 13px; font-weight: 700; color: var(--text); }
.po-change-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; font-size: 12.5px; color: var(--text-secondary); }
.po-change-list b { color: var(--tab-emails-ink); font-weight: 700; margin-inline-end: 4px; }
.po-ghost { padding: 6px 12px; border-radius: 9px; border: 1px solid var(--border); background: var(--card-bg); cursor: pointer;
  font-family: inherit; font-size: 13px; font-weight: 600; color: var(--text-secondary); }
.po-ghost--danger:hover { color: var(--red); border-color: var(--red); background: color-mix(in srgb, var(--red) 6%, transparent); }
.po-md { font-size: 14px; line-height: 1.7; color: var(--text); }
.po-md :deep(h2) { font-size: 18px; margin: 4px 0 10px; }
.po-md :deep(h3) { font-size: 15px; margin: 16px 0 8px; color: var(--tab-emails-ink); }
.po-md :deep(h4), .po-md :deep(h5) { font-size: 14px; margin: 12px 0 6px; }
.po-md :deep(ul) { margin: 4px 0 8px; padding-inline-start: 20px; }
.po-md :deep(hr) { border: none; border-top: 1px solid var(--border-subtle); margin: 12px 0; }
.po-md :deep(blockquote) { margin: 8px 0; padding: 8px 12px; border-inline-start: 3px solid var(--tab-emails); background: var(--tab-emails-wash); border-radius: 6px; }
.po-md :deep(.md-table) { overflow-x: auto; margin: 6px 0 10px; }
.po-md :deep(table) { width: 100%; border-collapse: collapse; font-size: 13px; }
.po-md :deep(th) { text-align: right; font-weight: 700; background: var(--bg); padding: 6px 8px; border-bottom: 1px solid var(--border); white-space: nowrap; }
.po-md :deep(td) { padding: 6px 8px; border-bottom: 1px solid var(--border-subtle); vertical-align: top; }
@media (max-width: 520px) { .po-amt { display: none; } }
@media (prefers-reduced-motion: reduce) { .po-fold, .po-chev { transition: none; } }
</style>
