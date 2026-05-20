/**
 * useNotificationsStore — persistent alerts list shown in the header bell.
 *
 * Sources:
 *   - Portal automation: failed/timeout runs in the last 7 days
 *   - Latest commission comparison (gemel_hishtalmut + insurance categories):
 *     customers with unpaid products from a company that DID pay for someone
 *     ("the company is paying, just not this customer") — the actionable signal
 *
 * State persists in localStorage so dismissals survive a reload.
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import api from '../api/client.js'

const LS_DISMISSED = 'notif.dismissed.v1'   // { [alertId]: timestamp }

function loadDismissed() {
  try {
    const raw = localStorage.getItem(LS_DISMISSED)
    return raw ? JSON.parse(raw) : {}
  } catch { return {} }
}
function saveDismissed(obj) {
  try { localStorage.setItem(LS_DISMISSED, JSON.stringify(obj)) } catch { /* quota */ }
}

function fmtMoney(n) {
  const v = Math.round(Number(n) || 0)
  return new Intl.NumberFormat('he-IL').format(v)
}
function fmtRelativeHe(iso) {
  try {
    const d = new Date(iso)
    const diff = (Date.now() - d.getTime()) / 1000
    if (diff < 60) return 'עכשיו'
    if (diff < 3600) return `לפני ${Math.round(diff / 60)} דק׳`
    if (diff < 86400) return `לפני ${Math.round(diff / 3600)} שע׳`
    return `לפני ${Math.round(diff / 86400)} ימים`
  } catch { return '' }
}
const HE_MONTHS = ['ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני', 'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר']
const HE_MONTH_TO_NUM = Object.fromEntries(HE_MONTHS.map((n, i) => [n, i + 1]))

function fmtPeriodHe(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${HE_MONTHS[d.getMonth()]} ${String(d.getFullYear()).slice(-2)}`
}

/** Best-effort period_month extraction from a filename when the backend
 *  hasn't persisted one. Mirrors the resolution order in
 *  parser_service.py::detect_period_month (Hebrew month → numeric MM-YY). */
function parsePeriodFromFilename(filename, fallbackUploadedAt) {
  if (!filename) return null
  const name = String(filename)

  // 1) Hebrew month name + a nearby 2- or 4-digit year
  for (const [heMonth, m] of Object.entries(HE_MONTH_TO_NUM)) {
    if (!name.includes(heMonth)) continue
    // Year token in the filename (preferred)
    const yearMatch = name.match(/\b(20\d{2}|\d{2})\b/)
    let year = null
    if (yearMatch) {
      const y = yearMatch[1]
      year = y.length === 4 ? parseInt(y, 10) : 2000 + parseInt(y, 10)
    } else if (fallbackUploadedAt) {
      // No year in filename — fall back to upload year, capped so that a
      // month later in the calendar than the upload's month maps to the
      // previous year (e.g. "דצמבר" uploaded in January → previous year).
      const f = new Date(fallbackUploadedAt)
      year = f.getFullYear()
      if (m > (f.getMonth() + 1)) year -= 1
    }
    if (year) return `${year}-${String(m).padStart(2, '0')}-01`
  }

  // 2) Numeric MM-YY / MM_YYYY (e.g. "03-26", "12_2025")
  const numMatch = name.match(/(\d{1,2})[-_/](\d{2}|\d{4})/)
  if (numMatch) {
    const m = parseInt(numMatch[1], 10)
    const y2 = numMatch[2]
    const year = y2.length === 4 ? parseInt(y2, 10) : 2000 + parseInt(y2, 10)
    if (m >= 1 && m <= 12) return `${year}-${String(m).padStart(2, '0')}-01`
  }

  return null
}

function effectivePeriod(upload) {
  return upload?.period_month || parsePeriodFromFilename(upload?.filename, upload?.uploaded_at)
}

export const useNotificationsStore = defineStore('notifications', () => {
  // ─── State ───────────────────────────────────────────────
  const alerts = ref([])                  // active (undismissed) alerts
  const loading = ref(false)
  const error = ref(null)
  const lastRefreshedAt = ref(null)
  const dismissed = ref(loadDismissed())  // { [id]: ts }

  // ─── Derived ─────────────────────────────────────────────
  const visibleAlerts = computed(() =>
    alerts.value.filter((a) => !dismissed.value[a.id]),
  )
  const unreadCount = computed(() => visibleAlerts.value.length)

  // ─── Mutations ───────────────────────────────────────────
  function _setAlerts(next) {
    // Dedup by id so repeated refresh doesn't duplicate.
    const seen = new Set()
    alerts.value = next.filter((a) => {
      if (seen.has(a.id)) return false
      seen.add(a.id)
      return true
    })
  }

  function dismiss(id) {
    dismissed.value = { ...dismissed.value, [id]: Date.now() }
    saveDismissed(dismissed.value)
  }
  function dismissAll() {
    const now = Date.now()
    const next = { ...dismissed.value }
    for (const a of visibleAlerts.value) next[a.id] = now
    dismissed.value = next
    saveDismissed(next)
  }
  function restoreAll() {
    dismissed.value = {}
    saveDismissed({})
  }

  // ─── Refresh ─────────────────────────────────────────────
  async function refresh() {
    loading.value = true
    error.value = null
    const collected = []

    // 0) Period alignment — figure out which companies are missing נפרעים
    // for the latest production period. The comparison-derived "unpaid"
    // alerts in step 2 must be SUPPRESSED for companies without a matching
    // commission file (otherwise we'd flag April customers as "unpaid"
    // just because the company has only uploaded March so far).
    let productionPeriod = null     // ISO 'YYYY-MM-01' of latest production
    const expectedCompanies = new Set()        // companies with any historical commission upload
    const aligned = new Set()                  // companies that have a commission file at productionPeriod
    let uploadsList = []
    try {
      uploadsList = (await api.get('/uploads')).data || []
    } catch { /* keep going */ }

    // Latest production period_month (max of all production uploads with a period).
    // Falls back to parsing the filename when the backend hasn't persisted one.
    const prodPeriods = uploadsList
      .filter((u) => u.file_category === 'production')
      .map((u) => effectivePeriod(u))
      .filter(Boolean)
      .sort()
    productionPeriod = prodPeriods.length ? prodPeriods[prodPeriods.length - 1] : null

    // Per-company latest commission period (same filename fallback).
    const latestCommissionByCompany = new Map()
    for (const u of uploadsList) {
      if (u.file_category !== 'commission' || !u.company_source) continue
      expectedCompanies.add(u.company_source)
      const p = effectivePeriod(u)
      if (!p) continue
      const prev = latestCommissionByCompany.get(u.company_source)
      if (!prev || p > prev) latestCommissionByCompany.set(u.company_source, p)
    }
    if (productionPeriod) {
      for (const [co, p] of latestCommissionByCompany) {
        if (p >= productionPeriod) aligned.add(co)
      }
    }

    // Emit "missing נפרעים" alerts for companies whose latest commission
    // file is older than the production period (or who have no file at all).
    if (productionPeriod) {
      const productionPeriodHe = fmtPeriodHe(productionPeriod)
      for (const co of expectedCompanies) {
        if (aligned.has(co)) continue
        const latest = latestCommissionByCompany.get(co)
        const latestHe = latest ? fmtPeriodHe(latest) : null
        const bodyParts = [
          `אין קובץ נפרעים ל-${productionPeriodHe}`,
        ]
        if (latestHe) bodyParts.push(`האחרון: ${latestHe}`)
        bodyParts.push('הרץ אוטומציה להורדה')
        collected.push({
          id: `missing-nifraim-${co}-${productionPeriod}`,
          kind: 'missing_nifraim',
          severity: 'warning',
          title: `${co} — חסר קובץ נפרעים`,
          body: bodyParts.join(' · '),
          createdAt: new Date().toISOString(),
          actions: ['run_automation'],
          meta: { companyName: co, productionPeriod, productionPeriodHe, latestCommissionPeriod: latest },
        })
      }
    }

    // 1) Portal automation — recent failures
    try {
      const runs = (await api.get('/portal-automation/runs', { params: { limit: 20 } })).data || []
      const sevenDaysAgo = Date.now() - 7 * 86400 * 1000
      for (const r of runs) {
        if (!['failed', 'timeout'].includes(r.status)) continue
        const ts = new Date(r.finished_at || r.started_at).getTime()
        if (ts < sevenDaysAgo) continue
        collected.push({
          id: `run-${r.id}`,
          kind: 'run_failed',
          severity: 'error',
          title: 'אוטומציה נכשלה',
          body: `${fmtRelativeHe(r.finished_at || r.started_at)} · ${(r.error_message || 'שגיאה לא ידועה').slice(0, 100)}`,
          createdAt: r.finished_at || r.started_at,
          actions: ['view_runs'],
          meta: { runId: r.id, credentialId: r.credential_id },
        })
      }
    } catch (e) { /* keep going, other sources may succeed */ }

    // 2) Latest comparison per category — aggregate unpaid customers BY COMPANY,
    // but ONLY for companies whose latest commission upload is aligned with
    // the production period. Otherwise the "unpaid" status is meaningless —
    // it just means the נפרעים file hasn't arrived yet (covered by the
    // missing_nifraim alerts above).
    for (const category of ['gemel_hishtalmut', 'insurance']) {
      try {
        const res = await api.get('/comparison/latest', { params: { category } })
        const result = res.data?.result
        if (!result) continue
        // Show the production data period (e.g. "אפריל 26"), not the
        // computation timestamp ("מאי 26" — that's just when the cron ran).
        const period = productionPeriod ? fmtPeriodHe(productionPeriod) : fmtPeriodHe(res.data.computed_at)
        const unpaid = (result.customers || []).filter((c) => (c.unpaid_count || 0) > 0)
        if (!unpaid.length) continue

        // Group by primary company (first one we can find on the customer)
        const byCompany = new Map()
        for (const c of unpaid) {
          const company = (
            (c.production_products || []).map((p) => p.company || p.receiving_company).find(Boolean)
            || 'חברה לא ידועה'
          )
          if (!byCompany.has(company)) {
            byCompany.set(company, { company, customers: [], totalPremium: 0, totalUnpaidProducts: 0 })
          }
          const g = byCompany.get(company)
          g.customers.push(c)
          g.totalUnpaidProducts += c.unpaid_count || 0
          const sum = (c.product_matches?.unmatched_production || [])
            .reduce((s, p) => s + Number(p.premium || 0), 0)
          g.totalPremium += sum
        }

        const catLabel = category === 'gemel_hishtalmut' ? 'גמל/השתלמות' : 'ביטוח'
        for (const g of byCompany.values()) {
          if (!g.customers.length) continue
          // Suppress when there's no matching-period commission file —
          // a missing_nifraim alert already covers this case.
          if (productionPeriod && !aligned.has(g.company)) continue
          const topNames = g.customers
            .slice()
            .sort((a, b) => (b.unpaid_count || 0) - (a.unpaid_count || 0))
            .slice(0, 3)
            .map((c) => [c.first_name, c.last_name].filter(Boolean).join(' ') || c.id_number)
          const more = Math.max(0, g.customers.length - topNames.length)
          const namesStr = topNames.join(', ') + (more > 0 ? ` ועוד ${more}` : '')
          collected.push({
            id: `unpaid-${category}-${g.company}`,
            kind: 'unpaid_company',
            severity: 'warning',
            title: `${g.company} — ${g.customers.length} לקוחות לא קיבלו עמלה`,
            body: `${catLabel} · ${g.totalUnpaidProducts} מוצרים${g.totalPremium ? ` · פרמיה ₪${fmtMoney(g.totalPremium)}` : ''}${period ? ` · ${period}` : ''} · ${namesStr}`,
            createdAt: res.data.computed_at,
            actions: ['send_email', 'open_comparison'],
            meta: {
              category,
              companyName: g.company,
              period,
              totalPremium: g.totalPremium,
              customersCount: g.customers.length,
              totalUnpaidProducts: g.totalUnpaidProducts,
              customerNames: topNames,
            },
          })
        }
      } catch (e) { /* keep going */ }
    }

    // 3) Sort by createdAt DESC (newest first), cap at 50 visible
    collected.sort((a, b) => (b.createdAt || '').localeCompare(a.createdAt || ''))
    _setAlerts(collected.slice(0, 50))

    lastRefreshedAt.value = new Date().toISOString()
    loading.value = false
  }

  // Background refresh every 5 minutes; the bell can call refresh() on open too.
  let bgTimer = null
  function startBackground() {
    if (bgTimer) return
    refresh().catch(() => {})
    bgTimer = setInterval(() => refresh().catch(() => {}), 5 * 60 * 1000)
  }
  function stopBackground() {
    if (bgTimer) { clearInterval(bgTimer); bgTimer = null }
  }

  return {
    alerts, loading, error, lastRefreshedAt, dismissed,
    visibleAlerts, unreadCount,
    refresh, dismiss, dismissAll, restoreAll,
    startBackground, stopBackground,
  }
})
