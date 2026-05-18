import { normalizeCompany, sameCompany } from './companyNorm.js'

function formatAmount(val) {
  if (!val) return '₪0'
  const num = Math.round(val)
  const sign = num < 0 ? '-' : ''
  const abs = Math.abs(num).toLocaleString('en-US')
  return `${sign}₪${abs}`
}

function extractMonthLabel(filename) {
  if (!filename) return ''
  return filename.replace('.xlsx', '').replace('.xls', '').replace('דוח פרודוקציה', '').trim() || filename
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  try {
    const d = new Date(dateStr)
    return d.toLocaleDateString('he-IL', { year: 'numeric', month: '2-digit', day: '2-digit' })
  } catch { return '' }
}

function pickBiggestMover(changedClients) {
  if (!Array.isArray(changedClients) || !changedClients.length) return null
  let best = null
  let bestMag = 0
  for (const c of changedClients) {
    const prem = Math.abs(c.premium_diff || 0)
    const accum = Math.abs(c.accumulation_diff || 0)
    if (prem > bestMag) {
      bestMag = prem
      best = { client: c, field: 'פרמיה', value: c.premium_diff }
    }
    if (accum > bestMag) {
      bestMag = accum
      best = { client: c, field: 'צבירה', value: c.accumulation_diff }
    }
  }
  return best
}

function topCompanyByCommission(commissionByCompany) {
  if (!Array.isArray(commissionByCompany) || !commissionByCompany.length) return null
  return [...commissionByCompany].sort((a, b) => (b.total || 0) - (a.total || 0))[0]
}

// Group new/removed clients by company for breakdown
function groupByCompany(clients) {
  const map = new Map()
  for (const c of clients || []) {
    const key = c.company || '—'
    map.set(key, (map.get(key) || 0) + 1)
  }
  return [...map.entries()].sort((a, b) => b[1] - a[1])
}

// Detect customers who switched insurers: same id_number appears in removed AND new
// under a DIFFERENT NORMALIZED company. Using the canonical key (via
// normalizeCompany) means "הראל" vs "הראל חברה לביטוח בע״מ" is NOT a switch,
// while "הראל" vs "מנורה" IS — fixes spurious switcher rows from corporate-
// suffix noise.
function detectSwitchers(newClients = [], removedClients = []) {
  const removedById = new Map()
  for (const r of removedClients) {
    if (r.id_number) removedById.set(String(r.id_number), r)
  }
  const switchers = []
  for (const n of newClients) {
    if (!n.id_number) continue
    const prior = removedById.get(String(n.id_number))
    if (prior && !sameCompany(prior.company, n.company)) {
      switchers.push({
        id_number: n.id_number,
        name: n.name || prior.name || '',
        from_company: prior.company || '—',
        to_company: n.company || '—',
      })
    }
  }
  return switchers
}

// Top N changed clients ranked by max |premium_diff| or |accumulation_diff|
function topMovers(changedClients, limit = 10) {
  if (!Array.isArray(changedClients)) return []
  return [...changedClients]
    .map(c => ({
      ...c,
      _mag: Math.max(Math.abs(c.premium_diff || 0), Math.abs(c.accumulation_diff || 0)),
    }))
    .filter(c => c._mag > 0)
    .sort((a, b) => b._mag - a._mag)
    .slice(0, limit)
}

// Aggregate premium & accumulation deltas per company across changed_clients
function perCompanyDeltas(changedClients) {
  const map = new Map()
  for (const c of changedClients || []) {
    const key = c.company || '—'
    const agg = map.get(key) || { company: key, premium_diff: 0, accumulation_diff: 0, count: 0 }
    agg.premium_diff += (c.premium_diff || 0)
    agg.accumulation_diff += (c.accumulation_diff || 0)
    agg.count += 1
    map.set(key, agg)
  }
  return [...map.values()].sort(
    (a, b) => Math.abs(b.accumulation_diff) + Math.abs(b.premium_diff)
             - Math.abs(a.accumulation_diff) - Math.abs(a.premium_diff)
  )
}

/**
 * Build a SHORT Hebrew prose summary (for the inline insight card)
 * + 3 data-driven suggestion chips
 * + a RICH structured view-context string forwarded to the backend AI as ground-truth
 *   for this specific comparison view.
 * Null-safe.
 */
export function buildProductionComparisonSummary(result) {
  if (!result || !result.summary) return null
  const s = result.summary

  const curLabel = extractMonthLabel(s.current_filename) || 'הקובץ הנוכחי'
  const prevLabel = extractMonthLabel(s.previous_filename) || 'הקובץ הקודם'

  // ---------- Short prose (insight card) ----------
  const sentences = []
  const parts = []
  if (s.new_count) parts.push(`${s.new_count} חדשים`)
  if (s.changed_count) parts.push(`${s.changed_count} השתנו`)
  if (s.removed_count) parts.push(`${s.removed_count} הוסרו`)
  if (parts.length) sentences.push(`בין ${curLabel} ל-${prevLabel}: ${parts.join(' · ')}.`)

  // BIGGEST MOVER — explicitly label as a SINGLE customer's delta so the
  // text doesn't mislead readers into thinking it's the company aggregate.
  // The old phrasing "עלייה של ₪X בצבירה ב-Mor" caused QA bug #N where the
  // reader and the AI both interpreted "מור" as "Mor company aggregate"
  // when it was actually one customer (אורי פלד) at Mor.
  const mover = pickBiggestMover(result.changed_clients)
  if (mover && mover.value) {
    const direction = mover.value > 0 ? 'עלייה' : 'ירידה'
    const who = mover.client.name || mover.client.id_number || 'לקוח'
    const company = mover.client.company ? ` (${mover.client.company})` : ''
    sentences.push(`הלקוח עם השינוי הגדול ביותר — ${who}${company}: ${direction} של ${formatAmount(Math.abs(mover.value))} ב${mover.field}.`)
  }

  // Per-company aggregated top — sums across all clients in each company.
  // This is the TRUE "which company moved the most" answer.
  const companyDeltasAll = perCompanyDeltas(result.changed_clients)
  const topCompanyByAccum = companyDeltasAll
    .map(d => ({ company: d.company, delta: d.accumulation_diff }))
    .filter(x => x.delta !== 0)
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))[0]
  if (topCompanyByAccum) {
    const dir = topCompanyByAccum.delta > 0 ? 'עלתה' : 'ירדה'
    sentences.push(`החברה שזזה הכי הרבה בצבירה: ${topCompanyByAccum.company} — ${dir} ב-${formatAmount(Math.abs(topCompanyByAccum.delta))}.`)
  }

  if (s.has_commission_data && s.commission_total) {
    const periodNote = s.period_month ? ` (חודש ${s.period_month})` : ''
    const top = topCompanyByCommission(s.commission_by_company)
    sentences.push(top
      ? `סך העמלות${periodNote}: ${formatAmount(s.commission_total)} — החברה המובילה היא ${top.company}.`
      : `סך העמלות${periodNote}: ${formatAmount(s.commission_total)}.`)
  }

  const summary = sentences.join(' ')

  // ---------- Suggestions ----------
  const switchers = detectSwitchers(result.new_clients, result.removed_clients)
  const suggestions = []
  if (mover) {
    suggestions.push(`למה ${mover.value > 0 ? 'עלתה' : 'ירדה'} ה${mover.field}${mover.client.company ? ` ב-${mover.client.company}` : ''}?`)
  } else if (s.changed_count) {
    suggestions.push('מי הלקוחות שהכי השתנו?')
  }
  if (s.has_commission_data) suggestions.push('תראה לי את העמלות')
  else if (s.premium_positive || s.premium_negative) suggestions.push('מי עלה הכי הרבה בפרמיה?')
  if (switchers.length) suggestions.push('מי עבר חברת ביטוח?')
  else if (s.removed_count) suggestions.push('מי נעלם מהתיק?')
  else suggestions.push('סכם את החברות הבולטות')

  const generic = ['איזו חברה ירדה הכי הרבה?', 'הסבר לי את השינויים הגדולים', 'מי הלקוחות החדשים?']
  for (const g of generic) {
    if (suggestions.length >= 3) break
    if (!suggestions.includes(g)) suggestions.push(g)
  }
  const uniqueSuggestions = Array.from(new Set(suggestions)).slice(0, 3)

  // ---------- Rich view-context payload (backend) ----------
  // STRUCTURE (intentional order — FACTS first, narrative tail last, so
  // truncation drops storytelling not numbers):
  //   1. Header (file labels + dates)
  //   2. FACTS — counts, sums, per-company commissions, switchers,
  //      per-customer truth blocks for top 30 customers (immune to truncation)
  //   3. Narrative tail — top movers, breakdowns, sample lists
  //
  // The "עובדות לקוח" block exists specifically so the AI can NEVER claim a
  // customer is only-in-one-file when they're actually in both (the
  // אבלין פיפרברג QA bug). Each line is computed deterministically from the
  // raw comparison result.
  const FACTS = []
  const NARR = []
  FACTS.push(`השוואת קבצי פרודוקציה — ${curLabel} מול ${prevLabel}`)
  if (s.current_date) FACTS.push(`קובץ נוכחי: ${curLabel} (${formatDate(s.current_date)})`)
  if (s.previous_date) FACTS.push(`קובץ קודם: ${prevLabel} (${formatDate(s.previous_date)})`)
  FACTS.push('')

  FACTS.push('מונים:')
  FACTS.push(`- חדשים: ${s.new_count || 0}`)
  FACTS.push(`- השתנו: ${s.changed_count || 0}`)
  FACTS.push(`- הוסרו: ${s.removed_count || 0}`)
  FACTS.push(`- ללא שינוי: ${s.unchanged_count || 0}`)
  FACTS.push('')

  // Keep `L` alias so the rest of the function (narrative) keeps reading idiomatically.
  const L = NARR

  // Commission totals at the TOP of FACTS (was last, got truncated under load)
  if (Array.isArray(s.commission_by_company) && s.commission_by_company.length) {
    const sortedComm = [...s.commission_by_company].sort((a, b) => (b.total || 0) - (a.total || 0))
    FACTS.push('עמלות לפי חברה (עובדה — לא לחשב מחדש):')
    let commSum = 0
    for (const c of sortedComm.slice(0, 15)) {
      FACTS.push(`- ${c.company}: ${formatAmount(c.total || 0)} (${c.clients_count || 0} לקוחות)`)
      commSum += (c.total || 0)
    }
    FACTS.push(`סה"כ עמלות מסוכמות: ${formatAmount(commSum)}`)
    FACTS.push('')
  }

  // Switchers — direct, deterministic answer to "מי עבר חברה?"
  if (switchers.length) {
    FACTS.push(`לקוחות שעברו חברה (סך ${switchers.length}):`)
    for (const sw of switchers.slice(0, 30)) {
      FACTS.push(`- ${sw.id_number} ${sw.name}: ${sw.from_company} → ${sw.to_company}`)
    }
    if (switchers.length > 30) FACTS.push(`  (... ועוד ${switchers.length - 30})`)
    FACTS.push('')
  }

  // ===== Per-COMPANY aggregated deltas (the canonical "Mor's increase") =====
  // CRITICAL: this block must come BEFORE the per-customer truth block, and
  // BEFORE any individual-mover list. The QA bug "₪2,658,447 increase at
  // Mor" came from the AI quoting אורי פלד's personal delta as if it were
  // Mor's company aggregate. By putting the real company aggregates at the
  // top of FACTS — labeled explicitly as "company aggregate" — the AI has a
  // clear, deterministic answer to "how much did Mor go up by?".
  const companyDeltasFacts = perCompanyDeltas(result.changed_clients)
  if (companyDeltasFacts.length) {
    FACTS.push('=== שינויים מצטברים לפי חברה (סכום של כל הלקוחות באותה חברה — לא לבלבל עם דלתא של לקוח בודד!) ===')
    for (const d of companyDeltasFacts.slice(0, 20)) {
      const bits = [`${d.count} לקוחות`]
      if (d.premium_diff) bits.push(`Δפרמיה ${d.premium_diff > 0 ? '+' : ''}${formatAmount(d.premium_diff)}`)
      if (d.accumulation_diff) bits.push(`Δצבירה ${d.accumulation_diff > 0 ? '+' : ''}${formatAmount(d.accumulation_diff)}`)
      FACTS.push(`- ${d.company}: ${bits.join(' · ')}`)
    }
    FACTS.push('')
  }

  // ===== Per-customer truth block (top 30 by absolute change/exposure) =====
  // This is the AI's defense against bucket-confusion bugs like the
  // אבלין פיפרברג case. For each top customer, we state explicitly which
  // bucket they're in — the AI MUST NOT contradict this.
  const truthCandidates = []
  for (const c of (result.changed_clients || [])) {
    truthCandidates.push({
      id: c.id_number, name: c.name, company: c.company,
      bucket: 'השתנו',
      premium_diff: c.premium_diff || 0,
      accumulation_diff: c.accumulation_diff || 0,
      mag: Math.max(Math.abs(c.premium_diff || 0), Math.abs(c.accumulation_diff || 0)),
    })
  }
  for (const c of (result.new_clients || [])) {
    truthCandidates.push({
      id: c.id_number, name: c.name, company: c.company,
      bucket: 'חדש בקובץ הנוכחי בלבד',
      mag: Math.abs(c.premium || c.accumulation || 0),
    })
  }
  for (const c of (result.removed_clients || [])) {
    truthCandidates.push({
      id: c.id_number, name: c.name, company: c.company,
      bucket: 'היה בקובץ הקודם בלבד',
      mag: Math.abs(c.premium || c.accumulation || 0),
    })
  }
  truthCandidates.sort((a, b) => (b.mag || 0) - (a.mag || 0))
  const truthTop = truthCandidates.slice(0, 30)
  if (truthTop.length) {
    FACTS.push('=== עובדות לקוח (לא להמציא — מקור: דיף הפרודוקציה) ===')
    for (const t of truthTop) {
      const bits = [t.bucket]
      if (t.premium_diff) bits.push(`Δפרמיה ${t.premium_diff > 0 ? '+' : ''}${formatAmount(t.premium_diff)}`)
      if (t.accumulation_diff) bits.push(`Δצבירה ${t.accumulation_diff > 0 ? '+' : ''}${formatAmount(t.accumulation_diff)}`)
      const co = t.company ? ` [${t.company}]` : ''
      FACTS.push(`- ${t.id || '—'} ${t.name || ''}${co}: ${bits.join(' · ')}`)
    }
    FACTS.push('')
  }

  L.push('סך שינויים:')
  if (s.premium_positive || s.premium_negative) {
    L.push(`- פרמיה: ${s.premium_positive || 0} עליות / ${s.premium_negative || 0} ירידות`)
  }
  if (s.accum_positive || s.accum_negative) {
    L.push(`- צבירה: ${s.accum_positive || 0} עליות / ${s.accum_negative || 0} ירידות`)
  }
  if (s.has_commission_data) {
    L.push(`- עמלות: סה"כ ${formatAmount(s.commission_total || 0)}`)
    if (s.commission_diff_positive || s.commission_diff_negative) {
      L.push(`  (${s.commission_diff_positive || 0} עלייה, ${s.commission_diff_negative || 0} ירידה)`)
    }
    if (s.commission_positive_count || s.commission_zero_count) {
      L.push(`  (${s.commission_positive_count || 0} עם עמלה, ${s.commission_zero_count || 0} ללא)`)
    }
  }
  L.push('')

  // (Per-company aggregated deltas now emitted at the TOP of FACTS, before
  // the per-customer truth block — see the "שינויים מצטברים לפי חברה"
  // section above. Not duplicated here to avoid the AI conflating
  // per-customer with per-company numbers.)

  // New clients breakdown
  const newByCompany = groupByCompany(result.new_clients)
  if (newByCompany.length) {
    L.push('חדשים לפי חברה:')
    for (const [co, n] of newByCompany.slice(0, 10)) L.push(`- ${co}: ${n}`)
    L.push('')
  }

  // Removed clients breakdown
  const removedByCompany = groupByCompany(result.removed_clients)
  if (removedByCompany.length) {
    L.push('הוסרו לפי חברה:')
    for (const [co, n] of removedByCompany.slice(0, 10)) L.push(`- ${co}: ${n}`)
    L.push('')
  }

  // Switchers — the direct answer to "מי עבר חברת ביטוח?"
  if (switchers.length) {
    L.push(`לקוחות שעברו חברה (${switchers.length}):`)
    for (const sw of switchers.slice(0, 15)) {
      L.push(`- ${sw.id_number} ${sw.name}: ${sw.from_company} → ${sw.to_company}`)
    }
    if (switchers.length > 15) L.push(`  (... ועוד ${switchers.length - 15})`)
    L.push('')
  } else if (s.new_count && s.removed_count) {
    L.push('לקוחות שעברו חברה: 0 (אין ת.ז המשותפים לרשימות החדשים וההוסרו)')
    L.push('')
  }

  // Top 10 movers with full detail — INDIVIDUAL customer deltas only.
  // Label is explicit so the AI doesn't confuse one customer's delta
  // with the company aggregate (the Mor ₪2,658,447 bug).
  const movers = topMovers(result.changed_clients, 10)
  if (movers.length) {
    L.push('10 לקוחות בודדים עם השינוי הגדול ביותר (הערכים הם ללקוח אחד בלבד — אסור לדווח אותם כדלתא של חברה!):')
    for (const m of movers) {
      const bits = []
      if (m.premium_diff) bits.push(`פרמיה ${m.premium_diff > 0 ? '+' : ''}${formatAmount(m.premium_diff)}`)
      if (m.accumulation_diff) bits.push(`צבירה ${m.accumulation_diff > 0 ? '+' : ''}${formatAmount(m.accumulation_diff)}`)
      const company = m.company ? ` (${m.company})` : ''
      L.push(`- ${m.id_number} ${m.name}${company}: ${bits.join(' · ')}`)
    }
    L.push('')
  }

  // (Commission breakdown already emitted at the top of FACTS — not duplicated here.)

  // Truncation policy: FACTS NEVER truncated. NARR truncated to fit the
  // remaining budget. Total budget bumped 6500→12000 (memory backend cap
  // raised in parallel) so per-customer truth block + facts always fit.
  const TOTAL_CAP = 12000
  const factsString = FACTS.join('\n')
  const narrString = NARR.join('\n')
  let viewContextString = factsString
  let truncated = false
  const remainingBudget = TOTAL_CAP - factsString.length - 64  // slack for header
  if (narrString.length <= remainingBudget) {
    viewContextString += '\n' + narrString
  } else if (remainingBudget > 200) {
    viewContextString += '\n' + narrString.slice(0, remainingBudget) + '\n[... נתונים נוספים קוצצו — נא דייקי לחברה/חודש מסוים ...]'
    truncated = true
  } else {
    truncated = true
  }

  return {
    summary,
    suggestions: uniqueSuggestions,
    viewContextString,
    viewContextTruncated: truncated,
  }
}


// ────────────────────────────────────────────────────────────────────────────
// Commission comparison (השוואת נפרעים) — production × commission per customer
// ────────────────────────────────────────────────────────────────────────────

function sumCustomerCommissionPaid(c) {
  let total = 0
  for (const p of (c.product_matches?.matched || [])) total += (p.commission || 0)
  return total
}

function customerHasOnlyZeroAccum(c) {
  // For gemel: a customer with all-zero accumulation has no real exposure.
  const products = c.production_products || c.product_matches?.unmatched_production || []
  if (!products.length) return false
  return products.every((p) => !(p.accumulation || p.balance || 0))
}

function customerExposure(c, isInsurance) {
  // For insurance: total premium. For gemel: total accumulation across products.
  if (isInsurance) return c.total_premium || 0
  let accum = 0
  for (const p of (c.product_matches?.matched || [])) accum += (p.balance || p.accumulation || 0)
  for (const p of (c.product_matches?.unmatched_commission || [])) accum += (p.balance || 0)
  for (const p of (c.product_matches?.unmatched_production || [])) accum += (p.accumulation || p.balance || 0)
  for (const p of (c.production_products || [])) accum += (p.accumulation || p.balance || 0)
  return accum
}

function topCompanyByUnpaid(unpaidCustomers) {
  const by = new Map()
  for (const c of unpaidCustomers) {
    const co = c.company || '—'
    by.set(co, (by.get(co) || 0) + 1)
  }
  let top = null
  for (const [co, n] of by.entries()) {
    if (!top || n > top.count) top = { company: co, count: n }
  }
  return top
}

/**
 * Build inline insight + suggestion chips + rich view-context for the
 * Production × Commission comparison view (השוואת נפרעים).
 *
 * @param {Array} customers   the array passed to ComparisonDashboard
 * @param {string} categoryLabel  e.g. "ביטוח" or "גמל"
 * @param {Array<string>} companySources commission company names included
 */
export function buildCommissionComparisonSummary(customers, categoryLabel, companySources) {
  if (!Array.isArray(customers) || customers.length === 0) return null

  const isInsurance = (categoryLabel || '').includes('ביטוח')

  const matched = customers.filter((c) => c.match_status === 'matched')
  const onlyComm = customers.filter((c) => c.match_status === 'only_commission')
  const onlyProd = customers.filter((c) => c.match_status === 'only_production')
  // For gemel, "effective unpaid" excludes zero-accumulation customers (no exposure → not really unpaid).
  const effectiveUnpaid = isInsurance ? onlyProd : onlyProd.filter((c) => !customerHasOnlyZeroAccum(c))

  const totalCommissionPaid = customers.reduce((s, c) => s + sumCustomerCommissionPaid(c), 0)

  // ---------- Short prose (insight card) ----------
  const sentences = []
  const periodSrcs = (companySources && companySources.length ? companySources : []).slice(0, 3).join(' · ')
  const headline = [`${customers.length} לקוחות${categoryLabel ? ' ב' + categoryLabel : ''}`]
  if (periodSrcs) headline.push(`(${periodSrcs}${companySources.length > 3 ? ' ...' : ''})`)
  sentences.push(headline.join(' '))

  const parts = []
  if (matched.length) parts.push(`${matched.length} בשניהם`)
  if (effectiveUnpaid.length) parts.push(`${effectiveUnpaid.length} לא שולם`)
  if (onlyComm.length) parts.push(`${onlyComm.length} רק בנפרעים`)
  if (parts.length) sentences.push(parts.join(' · ') + '.')

  if (totalCommissionPaid > 0) {
    sentences.push(`סך עמלות ששולמו: ${formatAmount(totalCommissionPaid)}.`)
  }

  const topUnpaidCo = topCompanyByUnpaid(effectiveUnpaid)
  if (topUnpaidCo && topUnpaidCo.count >= 2) {
    sentences.push(`חברה עם הכי הרבה לא שולם — ${topUnpaidCo.company} (${topUnpaidCo.count}).`)
  }

  const summary = sentences.join(' ')

  // ---------- Suggestions ----------
  const suggestions = []
  if (effectiveUnpaid.length) suggestions.push('מי הלקוחות הלא משולמים הגדולים ביותר?')
  if (topUnpaidCo) suggestions.push(`למה ${topUnpaidCo.company} לא משלמת על חלק מהלקוחות?`)
  if (onlyComm.length) suggestions.push('מי מופיע בנפרעים אך לא בפרודוקציה?')
  if (matched.length && totalCommissionPaid > 0) suggestions.push('איזו חברה משלמת הכי הרבה?')
  const generic = ['סכם את החברות הבולטות', 'אילו לקוחות צריכים תזכורת?', 'כמה לקוחות הם רק בנפרעים?']
  for (const g of generic) {
    if (suggestions.length >= 3) break
    if (!suggestions.includes(g)) suggestions.push(g)
  }
  const uniqueSuggestions = Array.from(new Set(suggestions)).slice(0, 3)

  // ---------- Rich view-context (backend) ----------
  // FACTS = counts, commission totals, per-customer truth (top 30).
  // NARR  = ranked lists, narrative breakdowns.
  // Truncation drops NARR only — FACTS are immune.
  const FACTS = []
  const NARR = []
  FACTS.push(`השוואת נפרעים — ${categoryLabel || 'קטגוריה לא ידועה'}`)
  if (companySources && companySources.length) {
    FACTS.push(`חברות מקור עמלה: ${companySources.slice(0, 10).join(', ')}${companySources.length > 10 ? ' ...' : ''}`)
  }
  FACTS.push('')

  // Mutual-exclusivity assertion the AI can quote verbatim — closes the
  // 673/396/277 sanity-check gap (memory note: arithmetic must add up).
  const sumCheck = matched.length + effectiveUnpaid.length + onlyComm.length
  FACTS.push('מונים (חייבים להסתכם — אסור להמציא בקטגוריזציה):')
  FACTS.push(`- סה"כ לקוחות: ${customers.length}`)
  FACTS.push(`- בשניהם (שולם): ${matched.length}`)
  FACTS.push(`- רק בפרודוקציה (לא שולם): ${effectiveUnpaid.length}`)
  if (!isInsurance && onlyProd.length !== effectiveUnpaid.length) {
    FACTS.push(`  (מתוכם ${onlyProd.length - effectiveUnpaid.length} ללא צבירה — לא נחשבים כחוב)`)
  }
  FACTS.push(`- רק בנפרעים (חריג): ${onlyComm.length}`)
  FACTS.push(`  בדיקת סכימה: ${matched.length}+${effectiveUnpaid.length}+${onlyComm.length}=${sumCheck} ${sumCheck === customers.length ? '✓' : '⚠️ ' + customers.length}`)
  FACTS.push('')

  if (totalCommissionPaid > 0) {
    FACTS.push(`סך עמלות ששולמו: ${formatAmount(totalCommissionPaid)} (עובדה — לא לחשב מחדש)`)
    FACTS.push('')
  }

  // ===== Per-customer truth block (top 30) =====
  // Direct fix for "אבלין פיפרברג ת.ז 12255162 רק בנפרעים" QA bug — the AI
  // had no per-customer ground truth, so it inferred from aggregates and
  // got the classification wrong. Now every top-30 customer's bucket is
  // stated explicitly in the context.
  const truthCandidates = customers
    .map((c) => ({ c, exp: customerExposure(c, isInsurance), paid: sumCustomerCommissionPaid(c) }))
    .sort((a, b) => Math.max(b.exp, b.paid) - Math.max(a.exp, a.paid))
    .slice(0, 30)
  if (truthCandidates.length) {
    FACTS.push('=== עובדות לקוח (לא להמציא — מקור: דיף נפרעים) ===')
    for (const { c, exp, paid } of truthCandidates) {
      const inProd = (c.match_status === 'matched' || c.match_status === 'only_production') ? 'כן' : 'לא'
      const inComm = (c.match_status === 'matched' || c.match_status === 'only_commission') ? 'כן' : 'לא'
      const co = c.company ? ` [${c.company}]` : ''
      const bits = [`פרודוקציה=${inProd}`, `נפרעים=${inComm}`]
      if (exp) bits.push(`${isInsurance ? 'פרמיה' : 'צבירה'} ${formatAmount(exp)}`)
      if (paid) bits.push(`עמלה ${formatAmount(paid)}`)
      FACTS.push(`- ${c.id_number || '—'} ${c.name || ''}${co}: ${bits.join(' · ')}`)
    }
    FACTS.push('')
  }

  // Alias L → NARR so the rest of this function keeps reading idiomatically.
  const L = NARR

  // Per-company unpaid breakdown
  const byCoUnpaid = new Map()
  for (const c of effectiveUnpaid) {
    const co = c.company || '—'
    const entry = byCoUnpaid.get(co) || { count: 0, exposure: 0 }
    entry.count += 1
    entry.exposure += customerExposure(c, isInsurance)
    byCoUnpaid.set(co, entry)
  }
  if (byCoUnpaid.size) {
    const sortedCo = [...byCoUnpaid.entries()].sort((a, b) => b[1].count - a[1].count)
    L.push('לא משולם לפי חברה:')
    for (const [co, info] of sortedCo.slice(0, 12)) {
      const bits = [`${info.count} לקוחות`]
      if (info.exposure) bits.push(`${isInsurance ? 'פרמיה' : 'צבירה'} ${formatAmount(info.exposure)}`)
      L.push(`- ${co}: ${bits.join(' · ')}`)
    }
    L.push('')
  }

  // Per-company commission paid
  const byCoPaid = new Map()
  for (const c of matched) {
    const co = c.company || '—'
    const paid = sumCustomerCommissionPaid(c)
    if (!paid) continue
    const entry = byCoPaid.get(co) || { paid: 0, customers: 0 }
    entry.paid += paid
    entry.customers += 1
    byCoPaid.set(co, entry)
  }
  if (byCoPaid.size) {
    const sortedCo = [...byCoPaid.entries()].sort((a, b) => b[1].paid - a[1].paid)
    L.push('עמלות לפי חברה:')
    for (const [co, info] of sortedCo.slice(0, 12)) {
      L.push(`- ${co}: ${formatAmount(info.paid)} · ${info.customers} לקוחות`)
    }
    L.push('')
  }

  // Top 10 unpaid customers by exposure (premium for insurance, accumulation for gemel)
  const rankedUnpaid = [...effectiveUnpaid]
    .map((c) => ({ c, exp: customerExposure(c, isInsurance) }))
    .filter((x) => x.exp > 0)
    .sort((a, b) => b.exp - a.exp)
    .slice(0, 10)
  if (rankedUnpaid.length) {
    L.push(`10 הלא-משולמים הגדולים ביותר לפי ${isInsurance ? 'פרמיה' : 'צבירה'}:`)
    for (const { c, exp } of rankedUnpaid) {
      const co = c.company ? ` (${c.company})` : ''
      L.push(`- ${c.id_number} ${c.name || ''}${co}: ${formatAmount(exp)}`)
    }
    L.push('')
  }

  // Customers only in commission file (anomalies — usually re-paid old policies)
  if (onlyComm.length) {
    L.push(`רק בנפרעים (עד 10 דוגמאות): ${onlyComm.length}`)
    for (const c of onlyComm.slice(0, 10)) {
      const co = c.company ? ` (${c.company})` : ''
      L.push(`- ${c.id_number} ${c.name || ''}${co}`)
    }
    L.push('')
  }

  const TOTAL_CAP = 12000
  const factsString = FACTS.join('\n')
  const narrString = NARR.join('\n')
  let viewContextString = factsString
  let truncated = false
  const remainingBudget = TOTAL_CAP - factsString.length - 64
  if (narrString.length <= remainingBudget) {
    viewContextString += '\n' + narrString
  } else if (remainingBudget > 200) {
    viewContextString += '\n' + narrString.slice(0, remainingBudget) + '\n[... נתונים נוספים קוצצו — נא דייקי לחברה/חודש מסוים ...]'
    truncated = true
  } else {
    truncated = true
  }

  return { summary, suggestions: uniqueSuggestions, viewContextString, viewContextTruncated: truncated }
}
