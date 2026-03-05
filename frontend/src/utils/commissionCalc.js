/**
 * Shared commission calculation formulas.
 * Used by ComparisonDetail, CustomerDetailModal, and ComparisonDashboard.
 *
 * Gemel/Hishtalmut: accumulation × rate ÷ 12
 * Insurance:        premium × rate × 100
 */

/**
 * Calculate expected commission for a product given a rate.
 * @param {Object} product - Must have accumulation, balance, premium fields
 * @param {number} rate - Decimal rate (e.g. 0.003)
 * @returns {number|null}
 */
export function calcExpectedCommission(product, rate) {
  if (!rate) return null

  // Gemel/Hishtalmut: accumulation * rate / 12
  if (product.accumulation != null && product.accumulation !== 0) {
    return product.accumulation * rate / 12
  }
  // Fallback to balance (commission file accumulation)
  if (product.balance != null && product.balance !== 0) {
    return product.balance * rate / 12
  }
  // Insurance: premium * rate * 100 (no /12)
  if (product.premium != null && product.premium !== 0) {
    return product.premium * rate * 100
  }
  return null
}
