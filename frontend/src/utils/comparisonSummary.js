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
// under a DIFFERENT company
function detectSwitchers(newClients = [], removedClients = []) {
  const removedById = new Map()
  for (const r of removedClients) {
    if (r.id_number) removedById.set(String(r.id_number), r)
  }
  const switchers = []
  for (const n of newClients) {
    if (!n.id_number) continue
    const prior = removedById.get(String(n.id_number))
    if (prior && (prior.company || '') !== (n.company || '')) {
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

  const mover = pickBiggestMover(result.changed_clients)
  if (mover && mover.value) {
    const direction = mover.value > 0 ? 'עלייה' : 'ירידה'
    const company = mover.client.company ? ` ב-${mover.client.company}` : ''
    sentences.push(`השינוי הבולט — ${direction} של ${formatAmount(Math.abs(mover.value))} ב${mover.field}${company}.`)
  }

  if (s.has_commission_data && s.commission_total) {
    const top = topCompanyByCommission(s.commission_by_company)
    sentences.push(top
      ? `סך העמלות לתקופה: ${formatAmount(s.commission_total)} — החברה המובילה היא ${top.company}.`
      : `סך העמלות לתקופה: ${formatAmount(s.commission_total)}.`)
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
  const L = []
  L.push(`השוואת קבצי פרודוקציה — ${curLabel} מול ${prevLabel}`)
  if (s.current_date) L.push(`קובץ נוכחי: ${curLabel} (${formatDate(s.current_date)})`)
  if (s.previous_date) L.push(`קובץ קודם: ${prevLabel} (${formatDate(s.previous_date)})`)
  L.push('')

  L.push('מונים:')
  L.push(`- חדשים: ${s.new_count || 0}`)
  L.push(`- השתנו: ${s.changed_count || 0}`)
  L.push(`- הוסרו: ${s.removed_count || 0}`)
  L.push(`- ללא שינוי: ${s.unchanged_count || 0}`)
  L.push('')

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

  // Per-company deltas among CHANGED clients — crucial for "why did accumulation drop at X"
  const companyDeltas = perCompanyDeltas(result.changed_clients)
  if (companyDeltas.length) {
    L.push('שינויים לפי חברה (בתוך הלקוחות ששונו):')
    for (const d of companyDeltas.slice(0, 12)) {
      const bits = [`${d.count} לקוחות`]
      if (d.premium_diff) bits.push(`פרמיה ${d.premium_diff > 0 ? '+' : ''}${formatAmount(d.premium_diff)}`)
      if (d.accumulation_diff) bits.push(`צבירה ${d.accumulation_diff > 0 ? '+' : ''}${formatAmount(d.accumulation_diff)}`)
      L.push(`- ${d.company}: ${bits.join(' · ')}`)
    }
    L.push('')
  }

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

  // Top 10 movers with full detail
  const movers = topMovers(result.changed_clients, 10)
  if (movers.length) {
    L.push('10 הלקוחות עם השינוי הגדול ביותר:')
    for (const m of movers) {
      const bits = []
      if (m.premium_diff) bits.push(`פרמיה ${m.premium_diff > 0 ? '+' : ''}${formatAmount(m.premium_diff)}`)
      if (m.accumulation_diff) bits.push(`צבירה ${m.accumulation_diff > 0 ? '+' : ''}${formatAmount(m.accumulation_diff)}`)
      const company = m.company ? ` (${m.company})` : ''
      L.push(`- ${m.id_number} ${m.name}${company}: ${bits.join(' · ')}`)
    }
    L.push('')
  }

  // Commission by company
  if (Array.isArray(s.commission_by_company) && s.commission_by_company.length) {
    L.push('עמלות לפי חברה:')
    for (const c of s.commission_by_company.slice(0, 10)) {
      L.push(`- ${c.company}: ${formatAmount(c.total || 0)} (${c.clients_count || 0} לקוחות)`)
    }
  }

  // Hard cap at 6500 chars (leaves headroom under backend's 8000 limit)
  let viewContextString = L.join('\n')
  if (viewContextString.length > 6500) {
    viewContextString = viewContextString.slice(0, 6500) + '\n[... נתונים נוספים קוצצו ...]'
  }

  return {
    summary,
    suggestions: uniqueSuggestions,
    viewContextString,
  }
}
