<template>
  <section v-if="offers.length" class="offers" aria-labelledby="po-title">
    <h3 id="po-title">שירותים נוספים עבורך</h3>
    <p class="offers-sub">הסוכן שלך מציע גם:</p>
    <div class="offer-grid">
      <!-- A plain link: opens in a new tab straight from the tap, so it is never
           blocked as a popup (WhatsApp / iOS in-app browsers). The click is
           logged fire-and-forget and never delays navigation. -->
      <a
        v-for="(o, i) in offers"
        :key="o.service_key"
        class="offer-card"
        :href="o.url"
        target="_blank"
        rel="noopener noreferrer"
        :style="{ '--offer-accent': accent(i) }"
        @click="logClick(o)"
      >
        <span class="offer-icon" aria-hidden="true" v-html="icon(o.service_key)"></span>
        <span class="offer-title">{{ o.title }}</span>
        <span class="offer-cta">
          לפרטים ורכישה
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>
        </span>
        <span class="sr-only">(נפתח בחלון חדש)</span>
      </a>
    </div>
  </section>
</template>

<script setup>
import { CHART_PALETTE } from '../../utils/chartPalette.js'

const props = defineProps({
  offers: { type: Array, default: () => [] },
  token: { type: String, required: true },
})

const ACCENTS = [CHART_PALETTE[1], CHART_PALETTE[9], CHART_PALETTE[3], CHART_PALETTE[6], CHART_PALETTE[8]]
const accent = (i) => ACCENTS[i % ACCENTS.length]

const svg = (d) => `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`
const ICONS = {
  travel: svg('<path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"/>'),
  savings: svg('<path d="M19 5c-1.5 0-2.8 1.4-3 2-3.5-1.5-11-.3-11 5 0 1.8 0 3 2 4.5V20h4v-2h3v2h4v-4c1-.5 1.7-1 2-2h2v-4h-2c0-1-.5-1.5-1-2V5z"/><path d="M2 9v1c0 1.1.9 2 2 2h1"/>'),
  health: svg('<path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>'),
  mortgage: svg('<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>'),
  car_home: svg('<path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.4 2.9A3.7 3.7 0 0 0 2 12v4c0 .6.4 1 1 1h2"/><circle cx="7" cy="17" r="2"/><path d="M9 17h6"/><circle cx="17" cy="17" r="2"/>'),
}
const icon = (key) => ICONS[key] || ICONS.savings

function logClick(o) {
  try {
    fetch(`/api/portal/${props.token}/offers/${o.service_key}/click`, {
      method: 'POST',
      keepalive: true,
      headers: { Authorization: `Bearer ${sessionStorage.getItem('portal_token') || ''}` },
    }).catch(() => {})
  } catch { /* logging must never block the link */ }
}
</script>

<style scoped>
.offers { display: flex; flex-direction: column; gap: 10px; margin-top: 28px; }
.offers h3 { margin: 0; font-size: 17px; font-weight: 800; color: var(--text); }
.offers-sub { margin: -6px 0 0; font-size: 13px; color: var(--text-muted); }
.offer-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 12px; }
.offer-card {
  position: relative; display: flex; flex-direction: column; gap: 8px; min-height: 120px;
  padding: 16px; border-radius: 14px; text-decoration: none;
  background: var(--card-bg, #fff); border: 1px solid var(--border-subtle, #E5E7EB);
  border-top: 3px solid var(--offer-accent);
  box-shadow: var(--shadow-sm, 0 2px 6px rgba(24, 24, 24, 0.05));
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.offer-card:hover { transform: translateY(-2px); box-shadow: 0 10px 24px -10px rgba(24, 24, 24, 0.2); }
.offer-card:focus-visible { outline: 2px solid var(--tab-portal-ink, #35719A); outline-offset: 3px; }
.offer-icon {
  width: 38px; height: 38px; display: grid; place-items: center; border-radius: 10px;
  color: var(--offer-accent); background: color-mix(in srgb, var(--offer-accent) 12%, transparent);
}
.offer-title { font-size: 15px; font-weight: 800; color: var(--text); }
.offer-cta { margin-top: auto; display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 700; color: var(--tab-portal-ink, #35719A); }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
@media print { .offers { display: none; } }
@media (prefers-reduced-motion: reduce) { .offer-card { transition: none; } .offer-card:hover { transform: none; } }
</style>
