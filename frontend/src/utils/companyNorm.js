// Mirror of backend/app/utils/company_norm.py — keep in sync so the
// frontend switcher detector and backend classifier agree on equality.
//
// The QA bug "אבלין פיפרברג שייכת רק לנפרעים" came from substring matching
// silently failing on company names with corporate suffixes. This function
// returns the deterministic canonical key.

const ALIASES = [
  ['הפניקס אקסלנס', 'הפניקס'],
  ['פניקס אקסלנס', 'הפניקס'],
  ['הפניקס', 'הפניקס'],
  ['פניקס', 'הפניקס'],
]

const SUFFIX_TOKENS = [
  'בע"מ', "בע''מ", 'בע״מ', 'בעמ',
  'חברה לביטוח', 'חברה ל ביטוח',
  'ביטוח', 'פנסיה', 'גמל והשתלמות', 'גמל', 'השתלמות',
  'ופנסיה', 'וגמל', 'חיים ובריאות', 'חיים',
  'ל ביטוח', 'ביטוחים', 'פנסיה וגמל',
]

export function normalizeCompany(name) {
  if (!name) return ''
  let s = String(name).trim()
  if (!s) return ''
  // Drop quote-style noise
  s = s.replace(/['"`׳״|]/g, '')
  s = s.replace(/\s+/g, ' ').trim()
  // Alias check (longest first via array order)
  for (const [k, v] of ALIASES) {
    if (s === k || s.startsWith(k)) return v
  }
  // Strip trailing corporate suffixes repeatedly
  let changed = true
  while (changed) {
    changed = false
    for (const suf of SUFFIX_TOKENS) {
      if (s.endsWith(' ' + suf)) {
        s = s.slice(0, -(suf.length + 1)).trimEnd()
        changed = true
        break
      }
      if (s === suf) { s = ''; changed = true; break }
    }
  }
  return s.trim()
}

export function sameCompany(a, b) {
  const na = normalizeCompany(a)
  const nb = normalizeCompany(b)
  return !!na && na === nb
}
