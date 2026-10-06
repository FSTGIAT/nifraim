<template>
  <!-- The walk-in customers / the insurers' addresses, in the app's own drill
       shell (DataModal): it grows out of what was pressed and folds back into
       it, like every drill in the other tabs. Inside, the nifraim-style drill
       order: search → cards that fold open in place → the action pinned at the
       bottom. Adding / editing a walk-in opens WalkinFormModal out of the pressed button. -->
  <DataModal :open="open" :origin="origin" :title="title" :badge="rows.length" accent="var(--tab-emails)" size="sm" @close="emit('close')">
    <div class="cd">
      <!-- ── the list ── -->
      <template v-if="true">
        <label v-if="rows.length > 4" class="cd-search">
          <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>
          <input v-model="q" placeholder="חיפוש" aria-label="חיפוש" />
        </label>

        <p v-if="!shown.length" class="cd-empty">
          {{ q ? 'לא נמצא' : isCo ? 'עוד אין כתובות לחברות.' : 'עוד אין לקוחות חדשים. הוסיפו לקוח, והשיחות איתו יגיעו לסיכום.' }}
        </p>
        <button v-if="isCo && !rows.length && !q" type="button" class="cd-btn cd-btn--wide" @click="emit('seed')">טעינת אנשי הקשר של החברות</button>

        <ul class="cd-list">
          <li v-for="r in shown" :key="r.id" class="cd-card" :class="{ 'cd-card--open': openId === r.id }">
            <button type="button" class="cd-row" :aria-expanded="openId === r.id" @click="openId = openId === r.id ? null : r.id">
              <CompanyLogo v-if="isCo" :company="r.name" :size="30" />
              <span class="cd-id">
                <strong>{{ r.name }}</strong>
                <small class="ltr-number">{{ isCo ? r.email : r.id_number }}</small>
              </span>
              <span v-if="!isCo" class="cd-amount ltr-number">{{ phoneFmt(r.phone) }}</span>
              <svg class="cd-chev" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M6 9l6 6 6-6" /></svg>
            </button>
            <div class="cd-fold">
              <div class="cd-fold-in">
                <dl class="cd-fields">
                  <template v-if="isCo">
                    <div><dt>מייל</dt><dd class="ltr-number">{{ r.email }}</dd></div>
                    <div v-if="r.contact_name"><dt>איש קשר</dt><dd>{{ r.contact_name }}</dd></div>
                    <div v-if="r.notes"><dt>הערות</dt><dd>{{ r.notes }}</dd></div>
                  </template>
                  <template v-else>
                    <div><dt>טלפון</dt><dd class="ltr-number">{{ phoneFmt(r.phone) }}</dd></div>
                    <div v-if="r.email"><dt>מייל</dt><dd class="ltr-number">{{ r.email }}</dd></div>
                    <div v-if="r.created_at"><dt>נוסף</dt><dd class="ltr-number">{{ dateFmt(r.created_at) }}</dd></div>
                  </template>
                </dl>
                <div class="cd-acts">
                  <button type="button" class="cd-act" @click="emit('edit', r, $event.currentTarget)">עריכה</button>
                  <button type="button" class="cd-act cd-act--del" @click="emit('delete', r.id)">מחיקה</button>
                </div>
              </div>
            </div>
          </li>
        </ul>

        <!-- companies still without an address: one tap adds it -->
        <template v-if="isCo && missingShown.length">
          <h5 class="cd-sec">חסרה כתובת <span class="cd-sec-n ltr-number">{{ missingShown.length }}</span></h5>
          <div class="cd-chips">
            <button v-for="m in missingShown" :key="m" type="button" class="cd-chip" @click="emit('add', m, $event.currentTarget)">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
              {{ m }}
            </button>
          </div>
        </template>

        <div class="cd-foot cd-foot--pinned">
          <button type="button" class="cd-btn" @click="emit('add', '', $event.currentTarget)">{{ isCo ? 'הוספת חברה' : 'לקוח חדש' }}</button>
        </div>
      </template>
    </div>
  </DataModal>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import DataModal from './DataModal.vue'
import CompanyLogo from './CompanyLogo.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  origin: { type: null, default: null },
  // walk-ins ({id, name, first_name, last_name, id_number, phone, email}) or, kind="companies",
  // insurer contacts mapped to {id, name, email, contact_name, notes, raw}
  rows: { type: Array, default: () => [] },
  kind: { type: String, default: 'walkins' },
  title: { type: String, default: 'לקוחות חדשים' },
  missing: { type: Array, default: () => [] },
})
const emit = defineEmits(['close', 'add', 'edit', 'delete', 'seed', 'saved'])

const isCo = computed(() => props.kind === 'companies')
const q = ref('')
const openId = ref(null)
const shown = computed(() => {
  const s = q.value.trim()
  const list = [...props.rows].sort((a, b) => (a.name || '').localeCompare(b.name || '', 'he'))
  return s ? list.filter((r) => `${r.name} ${r.phone || ''} ${r.email || ''} ${r.id_number || ''} ${r.contact_name || ''}`.includes(s)) : list
})
const missingShown = computed(() => { const s = q.value.trim(); return s ? props.missing.filter((m) => m.includes(s)) : props.missing })
const phoneFmt = (p) => { const d = String(p || '').replace(/\D/g, ''); return d.length === 10 ? `${d.slice(0, 3)}-${d.slice(3)}` : p }
const dateFmt = (iso) => { const d = new Date(iso); return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('he-IL') }

watch(() => props.open, (o) => {
  if (!o) return
  q.value = ''
  openId.value = null
})
</script>

<style scoped>
.cd { display: flex; flex-direction: column; gap: 10px; min-height: 0; }
.cd-search { display: flex; align-items: center; gap: 8px; height: 38px; padding: 0 12px; border-radius: 10px;
  background: var(--bg); color: var(--text-muted); }
.cd-search:focus-within { background: var(--card-bg); box-shadow: 0 0 0 2px var(--tab-emails); }
.cd-search input { flex: 1; min-width: 0; border: none; outline: none; background: none; font: inherit; font-size: 14px; color: var(--text); }
.cd-empty { margin: 18px 4px; text-align: center; font-size: 14px; line-height: 1.6; color: var(--text-muted); }

.cd-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.cd-card { border: 1px solid var(--border-subtle); border-radius: 12px; background: var(--card-bg); transition: border-color 0.2s, box-shadow 0.2s; }
.cd-card--open { border-color: color-mix(in srgb, var(--tab-emails) 35%, var(--border-subtle)); box-shadow: var(--shadow-sm); }
.cd-row { width: 100%; display: flex; align-items: center; gap: 12px; padding: 11px 14px; border: none; background: none;
  cursor: pointer; font-family: inherit; text-align: start; border-radius: 12px; }
.cd-row:hover { background: var(--bg); }
.cd-row:focus-visible { outline: 2px solid var(--tab-emails); outline-offset: -2px; }
.cd-id { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.cd-id strong { font-size: 14.5px; font-weight: 700; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cd-id small { align-self: flex-start; font-size: 12.5px; color: var(--text-muted); }
.cd-amount { font-size: 13.5px; font-weight: 700; color: var(--tab-emails-ink); }
.cd-chev { flex: none; color: var(--text-muted); transition: transform 0.35s cubic-bezier(0.32, 0.72, 0, 1); }
.cd-card--open .cd-chev { transform: rotate(180deg); }
/* the card opens in place (grid-rows 0fr → 1fr) */
.cd-fold { display: grid; grid-template-rows: 0fr; transition: grid-template-rows 0.4s cubic-bezier(0.32, 0.72, 0, 1); }
.cd-card--open .cd-fold { grid-template-rows: 1fr; }
.cd-fold-in { overflow: hidden; min-height: 0; }
.cd-fields { margin: 0 14px; padding: 4px 0 0; border-top: 1px solid var(--border-subtle); }
.cd-fields > div { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; padding: 7px 0; }
.cd-fields dt { font-size: 12.5px; color: var(--text-muted); }
.cd-fields dd { margin: 0; font-size: 14px; color: var(--text); }
.cd-acts { display: flex; gap: 6px; padding: 6px 14px 12px; }
.cd-act { padding: 6px 12px; border-radius: 8px; border: 1px solid var(--border); background: var(--card-bg); cursor: pointer;
  font-family: inherit; font-size: 13px; font-weight: 600; color: var(--text-secondary); }
.cd-act:hover { color: var(--text); border-color: var(--text-muted); }
.cd-act--del:hover { color: var(--red); background: var(--red-light); border-color: transparent; }

.cd-sec { margin: 10px 0 0; display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 700; color: var(--text-secondary); }
.cd-sec-n { font-size: 11px; font-weight: 800; padding: 1px 7px; border-radius: 99px; background: var(--tab-emails-wash); color: var(--tab-emails-ink); }
.cd-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.cd-chip { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 99px; cursor: pointer;
  border: 1px dashed color-mix(in srgb, var(--tab-emails) 38%, white); background: var(--card-bg);
  font-family: inherit; font-size: 12.5px; font-weight: 600; color: var(--text-secondary); }
.cd-chip svg { color: var(--tab-emails); }
.cd-chip:hover { border-style: solid; border-color: var(--tab-emails); color: var(--tab-emails-ink); background: var(--tab-emails-wash); }

.cd-foot { display: flex; gap: 8px; padding-top: 6px; }
/* the action pinned at the bottom of the drill */
.cd-foot--pinned { position: sticky; bottom: -1px; margin-top: 4px; padding: 10px 0 2px; background: linear-gradient(to top, var(--card-bg) 70%, transparent); }
.cd-btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 10px 22px; border: none; border-radius: 10px;
  cursor: pointer; background: var(--tab-emails-ink); color: #fff; font-family: inherit; font-size: 14px; font-weight: 700;
  box-shadow: 0 4px 12px color-mix(in srgb, var(--tab-emails) 26%, transparent); transition: transform 0.15s, filter 0.15s; }
.cd-btn:hover:not(:disabled) { transform: translateY(-1px); filter: brightness(0.93); }
.cd-btn:disabled { opacity: 0.45; cursor: not-allowed; box-shadow: none; }
.cd-btn--ghost { background: var(--card-bg); color: var(--text-secondary); border: 1px solid var(--border); box-shadow: none; }
.cd-btn--wide { width: 100%; }

@media (prefers-reduced-motion: reduce) { .cd-fold, .cd-chev { transition: none; } }
</style>
