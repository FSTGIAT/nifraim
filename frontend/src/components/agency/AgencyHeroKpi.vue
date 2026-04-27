<template>
  <div class="hero-grid">
    <!-- Hero card: lost money -->
    <div class="hero-card lost">
      <div class="hero-glow"></div>
      <div class="hero-eyebrow">
        <span class="dot"></span>
        כסף אבוד — סוכנות
      </div>
      <div class="hero-number ltr-number">{{ animatedLost }}</div>
      <div class="hero-meta">
        <span><strong>{{ d.lost_money_policy_count.toLocaleString('he-IL') }}</strong> פוליסות</span>
        <span class="dot-sep">·</span>
        <span><strong>{{ topCompanyName }}</strong> מובילה</span>
      </div>
      <div class="hero-spark">
        <svg viewBox="0 0 200 50" preserveAspectRatio="none" width="100%" height="50">
          <path d="M0,30 C20,20 40,40 60,28 C80,16 100,38 120,30 C140,22 160,42 200,18 L200,50 L0,50 Z" fill="rgba(234,0,30,0.10)"/>
          <path d="M0,30 C20,20 40,40 60,28 C80,16 100,38 120,30 C140,22 160,42 200,18" fill="none" stroke="#EA001E" stroke-width="2"/>
        </svg>
      </div>
    </div>

    <!-- Side stack: 4 stat tiles -->
    <div class="side-stack">
      <div class="stat-tile premium">
        <div class="stat-label">סך פרמיה — סוכנות</div>
        <div class="stat-value ltr-number">{{ formatCurrency(d.total_premium) }}</div>
        <div class="stat-sub">{{ d.unique_clients.toLocaleString('he-IL') }} לקוחות ייחודיים</div>
      </div>
      <div class="stat-tile accumulation">
        <div class="stat-label">סך צבירה</div>
        <div class="stat-value ltr-number">{{ formatCurrency(d.total_accumulation) }}</div>
        <div class="stat-sub">בכלל הסוכנים</div>
      </div>
      <div class="stat-tile agents">
        <div class="stat-label">סוכנים</div>
        <div class="stat-value">{{ d.agents_with_data }} <span class="muted">/ {{ d.agent_count }}</span></div>
        <div class="stat-sub">העלו פרודוקציה / סה"כ בסוכנות</div>
      </div>
      <div class="stat-tile bonus">
        <div class="stat-label">בונוסי תפוקה השנה</div>
        <div class="stat-value">
          <span class="ltr-number">{{ d.bonus_paid_this_year }}</span>
          <span class="muted">/ {{ d.bonus_total_this_year }}</span>
        </div>
        <div class="stat-sub">שולמו / סה"כ</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, watch, computed } from 'vue'

const props = defineProps({ d: { type: Object, required: true } })

const animatedTo = ref(0)

watch(() => props.d?.lost_money_amount, (v) => animateTo(Number(v) || 0), { immediate: false })
onMounted(() => animateTo(Number(props.d?.lost_money_amount) || 0))

function animateTo(target) {
  const start = animatedTo.value
  const dur = 900
  const t0 = performance.now()
  function tick(now) {
    const t = Math.min(1, (now - t0) / dur)
    const ease = 1 - Math.pow(1 - t, 3)
    animatedTo.value = Math.round(start + (target - start) * ease)
    if (t < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
}

const animatedLost = computed(() => '₪ ' + animatedTo.value.toLocaleString('he-IL'))
const topCompanyName = computed(() => props.d?.top_lost_company?.name || '—')

function formatCurrency(v) {
  if (v == null) return '—'
  return '₪ ' + Math.round(Number(v)).toLocaleString('he-IL')
}
</script>

<style scoped>
.hero-grid {
  display: grid;
  grid-template-columns: 1.3fr 1fr;
  gap: 20px;
  margin-bottom: 24px;
}

/* ─── Hero ─── */
.hero-card {
  position: relative;
  overflow: hidden;
  border-radius: 24px;
  padding: 28px 32px;
  background: linear-gradient(135deg, #1B0B14 0%, #3B0E18 60%, #5C141E 100%);
  color: #fff;
  box-shadow: 0 24px 50px -20px rgba(234, 0, 30, 0.45);
}
.hero-glow {
  position: absolute; inset: -40% -10% auto auto; width: 60%; aspect-ratio: 1;
  background: radial-gradient(circle at center, rgba(234, 0, 30, 0.6) 0%, transparent 60%);
  filter: blur(40px); opacity: 0.7;
}
.hero-eyebrow {
  display: inline-flex; align-items: center; gap: 8px;
  font-size: 12.5px; font-weight: 600; letter-spacing: 1px;
  color: rgba(255, 200, 200, 0.85);
  text-transform: uppercase; position: relative;
}
.hero-eyebrow .dot {
  width: 8px; height: 8px; border-radius: 50%; background: #EA001E;
  box-shadow: 0 0 0 4px rgba(234, 0, 30, 0.25);
  animation: pulse 1.6s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 4px rgba(234, 0, 30, 0.25); }
  50% { box-shadow: 0 0 0 9px rgba(234, 0, 30, 0); }
}
.hero-number {
  font-size: clamp(40px, 7vw, 76px);
  font-weight: 900;
  letter-spacing: -2px;
  line-height: 1;
  margin: 16px 0 12px;
  background: linear-gradient(120deg, #ffffff 0%, #FFB4BC 50%, #ffffff 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  position: relative;
}
.hero-meta {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.78);
  display: flex; align-items: center; gap: 10px;
  position: relative;
}
.hero-meta strong { color: #fff; font-weight: 700; }
.hero-meta .dot-sep { opacity: 0.5; }
.hero-spark { margin-top: 22px; opacity: 0.85; }

/* ─── Side stack ─── */
.side-stack {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.stat-tile {
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: 18px;
  padding: 18px 18px 16px;
  position: relative;
  overflow: hidden;
  transition: transform .2s var(--transition), box-shadow .2s var(--transition);
}
.stat-tile::after {
  content: ''; position: absolute; top: 0; right: 0; width: 4px; height: 100%;
  background: var(--primary);
  border-radius: 4px 0 0 4px;
  opacity: 0.85;
}
.stat-tile.premium::after { background: linear-gradient(180deg, #F57C00, #FF9800); }
.stat-tile.accumulation::after { background: linear-gradient(180deg, #2E844A, #66BB6A); }
.stat-tile.agents::after { background: linear-gradient(180deg, #7F56D9, #9575CD); }
.stat-tile.bonus::after { background: linear-gradient(180deg, #E8720A, #FFB74D); }
.stat-tile:hover { transform: translateY(-2px); box-shadow: var(--shadow-lg); }
.stat-label {
  font-size: 11.5px; font-weight: 600; color: var(--text-muted);
  letter-spacing: 0.4px; text-transform: uppercase;
}
.stat-value {
  font-size: 24px; font-weight: 800; color: var(--text);
  margin-top: 8px; letter-spacing: -0.5px; line-height: 1.1;
}
.stat-value .muted { color: var(--text-muted); font-weight: 600; font-size: 18px; }
.stat-sub { font-size: 12px; color: var(--text-muted); margin-top: 6px; }
.ltr-number { direction: ltr; unicode-bidi: embed; display: inline-block; }

@media (max-width: 1100px) {
  .hero-grid { grid-template-columns: 1fr; }
  .side-stack { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 600px) {
  .side-stack { grid-template-columns: 1fr; }
}
</style>
