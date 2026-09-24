import { normalizeCompany } from './companyNorm.js'

/**
 * Customers per company, split by match status — the one implementation
 * behind the dashboard's "לפי חברה" bars and the summary's company pie, so
 * the two can never disagree.
 *
 * A customer is counted once per company they hold a product with, so the
 * per-company totals can sum to more than the headline total; that's intended,
 * not double counting. `unpaidIds` is the set of only_production customers
 * that count as unpaid (gemel drops zero-accumulation ones) — others are
 * skipped so the rows agree with the headline "לא שולם".
 *
 * Returns rows sorted by total desc:
 *   { key, company, matched, only_production, only_commission, total,
 *     customers: { matched: [], only_production: [], only_commission: [] } }
 */
export function companyStatusBreakdown(customers, unpaidIds) {
  const map = new Map()
  const bump = (key, displayName, statusKey, customer) => {
    if (!map.has(key)) {
      map.set(key, {
        key, company: displayName, matched: 0, only_production: 0, only_commission: 0,
        customers: { matched: [], only_production: [], only_commission: [] },
      })
    }
    const row = map.get(key)
    // Same insurer can arrive under several spellings (short 'מגדל' from the
    // commission side vs legal 'מגדל חברה לביטוח בע"מ' from the merged
    // production file). Show the shortest so labels stay readable.
    if (displayName.length < row.company.length) row.company = displayName
    row[statusKey] += 1
    row.customers[statusKey].push(customer)
  }
  for (const c of customers || []) {
    if (c.match_status === 'only_production' && !unpaidIds.has(c.id_number)) continue
    const products = [
      ...(c.production_products || []),
      ...(c.commission_products || []),
      ...(c.product_matches?.matched || []),
      ...(c.product_matches?.unmatched_production || []),
      ...(c.product_matches?.unmatched_commission || []),
    ]
    // `company` FIRST — the SHORT brand name resolved server-side; `company_full`
    // is the raw legal name and would split one insurer into two.
    const names = products.map(p => p.company || p.company_full).filter(Boolean)
    if (!names.length && c.company) names.push(c.company)
    // Deduplicate on the NORMALIZED key — two spellings of one insurer on the
    // same customer would otherwise count it twice (inflated מגדל 73 → 145 live).
    const byKey = new Map()
    for (const raw of names) {
      const name = String(raw).trim()
      if (!name) continue
      const k = normalizeCompany(name) || name
      const prev = byKey.get(k)
      if (!prev || name.length < prev.length) byKey.set(k, name)
    }
    if (!byKey.size) {
      // Bucket rather than drop, or the rows quietly total less than the headline.
      bump('__none__', 'ללא שיוך חברה', c.match_status, c)
    } else {
      for (const [k, displayName] of byKey) bump(k, displayName, c.match_status, c)
    }
  }
  return [...map.values()]
    .map(r => ({ ...r, total: r.matched + r.only_production + r.only_commission }))
    .filter(r => r.total > 0)
    .sort((a, b) => b.total - a.total)
}
