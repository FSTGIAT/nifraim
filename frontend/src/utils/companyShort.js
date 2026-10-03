import { brandForLabel } from './companyBrand.js'
import { normalizeCompany } from './companyNorm.js'

/** The brand an agent says ("מגדל"), not the legal name ("מגדל חברה לביטוח
 *  בע"מ") — for chart slices and filter tabs where the long name won't fit. */
export function shortCompany(name) {
  if (!name) return 'לא ידוע'
  const b = brandForLabel(name)
  return b.label && b.label !== '?' ? b.label : (normalizeCompany(name) || name)
}
