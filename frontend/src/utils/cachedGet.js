import api from '../api/client'

/*
 * One in-flight/settled request per URL, shared by every component that asks
 * for it while one Production view is on screen. The "דורש טיפול" band reads
 * the same /production/alerts and /production/rate-audit payloads as the panels
 * it points into; without this each is fetched twice (rate-audit is the slowest
 * call on the tab). ProductionDashboard calls `invalidateCachedGet()` in its
 * setup, before its children mount, so a fresh view always refetches.
 */
const cache = new Map()

export function cachedGet(url) {
  if (!cache.has(url)) {
    const p = api.get(url).catch((e) => {
      cache.delete(url) // a failure must not stick for the rest of the view
      throw e
    })
    cache.set(url, p)
  }
  return cache.get(url)
}

export function invalidateCachedGet() {
  cache.clear()
}
