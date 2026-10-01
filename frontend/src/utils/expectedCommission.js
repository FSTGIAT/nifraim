import { calcExpectedCommission } from './commissionCalc.js'

/*
 * "What should this product pay" — the SAME rule CustomerDetailModal uses, so
 * the comparison's customer list and the customer window never disagree
 * (QA 2026-10-01: the list showed no expected amount where the window showed
 * ₪1,558). Prefer the backend's canonical figure (rate_select); fall back to
 * the agreement shelf by company name only for comparisons saved before the
 * backend priced products. When the backend looked and declined
 * (`expected_is_estimate` is a boolean), there is no fallback — that decline
 * is deliberate.
 */
const INSURANCE_HINTS = ['פוליסות', 'ביטוח', 'פוליסה']
const GEMEL_HINTS = ['גמל', 'השתלמות']
const stripHe = s => (s && s.startsWith('ה') && s.length > 2 ? s.slice(1) : null)

function hintsFor(product, category) {
  if (category) {
    if (category.includes('ביטוח')) return INSURANCE_HINTS
    if (category.includes('גמל')) return GEMEL_HINTS
  }
  if (product.accumulation > 0) return GEMEL_HINTS
  if (product.premium > 0) return INSURANCE_HINTS
  return null
}

function findRate(product, rates, category) {
  if (!rates?.length) return null
  const base = [product.company, product.company_full].filter(Boolean)
  const candidates = [...base]
  for (const c of base) { const s = stripHe(c); if (s) candidates.push(s) }
  const matches = new Set()
  for (const name of candidates) {
    const cl = name.toLowerCase()
    const fw = cl.split(/[\s-]/)[0]
    for (const r of rates) {
      const rn = (r.company_name || '').toLowerCase()
      if (r.company_name === name || cl.includes(rn) || rn.includes(cl) || (fw.length > 2 && rn.startsWith(fw))) {
        matches.add(r)
      }
    }
  }
  const arr = [...matches]
  if (!arr.length) return null
  if (arr.length === 1) return arr[0]
  const hints = hintsFor(product, category)
  return (hints && arr.find(r => hints.some(h => r.company_name.includes(h)))) || arr[0]
}

const backendResolved = p => p && p.expected_is_estimate !== undefined && p.expected_is_estimate !== null

export function expectedFor(p, rates, category = '') {
  if (!p) return null
  if (p.expected_commission != null) return p.expected_commission
  if (backendResolved(p)) return null
  const rate = (typeof p.rate === 'number' && p.rate > 0) ? p.rate : findRate(p, rates, category)?.rate
  return rate ? calcExpectedCommission(p, rate) : null
}
