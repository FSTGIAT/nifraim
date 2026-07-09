<template>
  <!-- HOME MODE: Premium card grid -->
  <div v-if="viewMode === 'home'" class="home-container">
    <div class="cards-grid">
      <button
        v-for="(tab, idx) in tabs"
        :key="tab.id"
       
        class="card"
        :style="{ '--i': idx, '--accent': tab.accent, '--accent-glow': tab.accentGlow, '--accent-ink': tab.ink }"
        @click="$emit('select-card', tab.id)"
        @mouseenter="hoveredCard = tab.id"
        @mouseleave="hoveredCard = null"
      >
        <!-- Noise texture overlay -->
        <div class="card-noise"></div>
        <!-- Subtle gradient accent at top -->
        <div class="card-accent-line"></div>
        <!-- Ambient color-matched Remotion loop — only while hovered -->
        <Transition name="cardfade">
          <CardAmbientIsland
            v-if="hoveredCard === tab.id"
            class="card-anim-bg"
            :color="ANIM_COLORS[tab.id]"
          />
        </Transition>
        <!-- Content -->
        <div class="card-body">
          <span class="card-icon-wrap">
            <AppIcon :name="tab.id" :size="22" />
          </span>
          <span class="card-label">{{ tab.label }}</span>
          <span class="card-desc">{{ tab.description }}</span>
        </div>
        <!-- Hover arrow indicator -->
        <span class="card-arrow">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="19" y1="12" x2="5" y2="12"/>
            <polyline points="12 5 5 12 12 19"/>
          </svg>
        </span>
      </button>
    </div>
  </div>

  <!-- CONTENT MODE: Compact mini-strip -->
  <div v-else class="strip-container">
    <div class="strip">
      <button
        v-for="tab in tabs"
        :key="tab.id"
       
        class="strip-pill"
        :class="{ active: modelValue === tab.id }"
        :style="{ '--accent': tab.accent, '--accent-wash': tab.accentGlow, '--accent-ink': tab.ink }"
        @click="$emit('update:modelValue', tab.id)"
      >
        <span class="strip-icon">
          <AppIcon :name="tab.id" :size="15" />
        </span>
        <span class="strip-label">{{ tab.label }}</span>
      </button>

      <div class="strip-divider"></div>

      <!-- Home button -->
      <button class="strip-pill home-pill" @click="$emit('go-home')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="7" height="7"/>
          <rect x="14" y="3" width="7" height="7"/>
          <rect x="3" y="14" width="7" height="7"/>
          <rect x="14" y="14" width="7" height="7"/>
        </svg>
      </button>

      <!-- Mount-point for the CircleMenu (or anything else WorkspaceView
           wants docked at the end of the strip, beside the home-pill). -->
      <slot name="strip-end" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import AppIcon from '../icons/AppIcon.vue'
import CardAmbientIsland from './CardAmbientIsland.vue'

const props = defineProps({
  modelValue: { type: String, required: true },
  viewMode: { type: String, default: 'home' },
})
defineEmits(['update:modelValue', 'select-card', 'go-home'])

/* Which home card is hovered → mounts ONE ambient Remotion loop at a time. */
const hoveredCard = ref(null)

/* Resolved --tab-* accent hex per card, handed to the ambient loop so it tints
   itself (Remotion runs in its own React tree and can't read the CSS var). Keep
   in sync with App.vue :root --tab-* tokens. */
const ANIM_COLORS = {
  production: '#2F73C4',
  comparison: '#2E844A',
  'commission-rates': '#8E44AD',
  'company-emails': '#E84A7F',
  recruits: '#3DB6B0',
  portal: '#4E9DD0',
  'ai-library': '#B79CEB',
  'portal-automation': '#0E8C8A',
}

/* Tab identity system — every tab owns ONE CHART_PALETTE color (tokens in
   App.vue :root). accent = identity, accentGlow = wash for tinted surfaces,
   ink = text-safe accent (only where the accent fails 4.5:1 on white). */
const tabs = [
  {
    id: 'production',
    label: 'פרודוקציה',
    description: 'העלאה וניתוח קבצי פרודוקציה',
    accent: 'var(--tab-production)',
    accentGlow: 'var(--tab-production-wash)',
    ink: 'var(--tab-production)',
  },
  {
    id: 'comparison',
    label: 'השוואת נפרעים',
    description: 'השוואת נפרעים מול פרודוקציה',
    accent: 'var(--tab-comparison)',
    accentGlow: 'var(--tab-comparison-wash)',
    ink: 'var(--tab-comparison)',
  },
  {
    id: 'commission-rates',
    label: 'טבלת עמלות',
    description: 'ניהול שיעורי עמלות',
    accent: 'var(--tab-commission)',
    accentGlow: 'var(--tab-commission-wash)',
    ink: 'var(--tab-commission)',
  },
  {
    id: 'company-emails',
    label: 'אימיילים לחברות',
    description: 'אנשי קשר בחברות ביטוח',
    accent: 'var(--tab-emails)',
    accentGlow: 'var(--tab-emails-wash)',
    ink: 'var(--tab-emails-ink)',
  },
  {
    id: 'recruits',
    label: 'ניהול תיק אישי',
    description: 'מעקב וניהול לקוחות מגויסים',
    accent: 'var(--tab-recruits)',
    accentGlow: 'var(--tab-recruits-wash)',
    ink: 'var(--tab-recruits-ink)',
  },
  {
    id: 'portal',
    label: 'פורטל לקוחות',
    description: 'יצירת ושיתוף פורטלים ללקוחות',
    accent: 'var(--tab-portal)',
    accentGlow: 'var(--tab-portal-wash)',
    ink: 'var(--tab-portal-ink)',
  },
  {
    id: 'ai-library',
    label: 'ספריית AI',
    description: 'הקבצים והנתונים שה-AI מכיר',
    accent: 'var(--tab-ai)',
    accentGlow: 'var(--tab-ai-wash)',
    ink: 'var(--tab-ai-ink)',
  },
  {
    id: 'portal-automation',
    label: 'אוטומציה',
    description: 'התחברות אוטומטית לפורטלים והורדת דוחות',
    accent: 'var(--tab-automation)',
    accentGlow: 'var(--tab-automation-wash)',
    ink: 'var(--tab-automation)',
  },
]
</script>

<style scoped>
/* ═══════════════════════════════════
   HOME MODE — Cards
   ═══════════════════════════════════ */
.home-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 36px 24px 16px;
  animation: fadeInUp 0.5s var(--transition) both;
}

.cards-grid {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 14px;
  direction: rtl;
  max-width: 920px;
}

/* ── Card ── */
.card {
  position: relative;
  width: 210px;
  height: 170px;
  border-radius: 14px;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  overflow: hidden;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  text-align: start;
  padding: 0;
  color: var(--text);
  transition: transform 0.35s var(--transition),
              border-color 0.3s ease,
              box-shadow 0.35s ease,
              background 0.3s ease;
  animation: cardEnter 0.45s var(--transition) both;
  animation-delay: calc(var(--i) * 70ms);
}

.card:hover {
  transform: translateY(-8px) scale(1.06);
  border-color: var(--accent);
  background: #fff;
  box-shadow:
    0 20px 56px var(--accent-glow),
    0 0 0 1px var(--accent-glow),
    0 6px 20px rgba(0, 0, 0, 0.07);
}

/* Ambient loop layer: fills the card, sits above the noise/accent-line but
   below the content (card-body is z-index:1). Clipped by the card's overflow. */
.card-anim-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
  border-radius: inherit;
  overflow: hidden;
  pointer-events: none;
}

/* Fade the loop in/out as the card is entered/left. */
.cardfade-enter-active,
.cardfade-leave-active {
  transition: opacity 0.35s ease;
}
.cardfade-enter-from,
.cardfade-leave-to {
  opacity: 0;
}

.card:active {
  transform: translateY(-2px) scale(0.99);
  transition-duration: 0.1s;
}

/* Noise texture */
.card-noise {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  opacity: 0.4;
  pointer-events: none;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
  background-size: 128px 128px;
  mix-blend-mode: multiply;
}

/* Top accent line */
.card-accent-line {
  position: relative;
  z-index: 1; /* stay above the ambient loop layer */
  height: 3px;
  width: 100%;
  background: var(--accent);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.card:hover .card-accent-line {
  opacity: 1;
}

/* Body */
.card-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 18px 18px 14px;
  position: relative;
  z-index: 1;
}

.card-icon-wrap {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: var(--accent-glow);
  border: 1px solid var(--accent-glow);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 14px;
  color: var(--accent-ink, var(--accent));
  transition: background 0.3s ease, box-shadow 0.3s ease, transform 0.3s ease;
}

.card:hover .card-icon-wrap {
  background: var(--accent);
  color: #fff;
  box-shadow: 0 4px 16px var(--accent-glow);
  transform: scale(1.05);
}

.card-label {
  font-size: 14px;
  font-weight: 650;
  color: var(--text);
  margin-bottom: 4px;
  letter-spacing: -0.3px;
}

.card-desc {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-muted);
  line-height: 1.45;
  transition: color 0.3s ease;
}

.card:hover .card-desc {
  color: var(--text-secondary);
}

/* Arrow indicator */
.card-arrow {
  position: absolute;
  bottom: 14px;
  left: 14px;
  width: 28px;
  height: 28px;
  border-radius: 7px;
  background: var(--bg);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  opacity: 0;
  transform: translateX(6px);
  transition: opacity 0.25s ease, transform 0.25s ease, color 0.25s ease, background 0.25s ease;
}

.card:hover .card-arrow {
  opacity: 1;
  transform: translateX(0);
  color: var(--accent-ink, var(--accent));
  background: var(--accent-glow);
}


/* ═══════════════════════════════════
   CONTENT MODE — Mini Strip
   ═══════════════════════════════════ */
.strip-container {
  display: flex;
  justify-content: center;
  padding: 10px 16px 6px;
  position: sticky;
  top: 32px; /* just under the StockTicker — the legacy WorkspaceHeader is no longer rendered */
  z-index: 90;
  background: var(--bg);
  animation: stripSlideDown 0.3s var(--transition) both;
}
@media (max-width: 720px) {
  /* StockTicker hides under 720px → tabs stick to the top edge. */
  .strip-container { top: 0; }
}

.strip {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  background: var(--card-bg);
  border: 1px solid var(--glass-border);
  border-radius: 12px;
  padding: 3px;
  box-shadow: var(--shadow-sm);
}

.strip-pill {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 7px 16px;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 500;
  font-family: inherit;
  color: var(--text-muted);
  background: transparent;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
  position: relative;
}

.strip-pill:hover:not(.active) {
  color: var(--text-secondary);
  background: rgba(0, 0, 0, 0.03);
}

.strip-pill.active {
  background: var(--accent-wash);
  color: var(--accent-ink, var(--accent));
  font-weight: 600;
  box-shadow: inset 0 -2px 0 var(--accent);
}

.strip-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.strip-divider {
  width: 1px;
  height: 20px;
  background: var(--border-subtle);
  margin: 0 4px;
  flex-shrink: 0;
}

.home-pill {
  padding: 7px 10px;
  color: var(--text-muted);
}

.home-pill:hover {
  color: var(--primary);
  background: var(--primary-glow);
}


/* ═══════════════════════════════════
   RESPONSIVE
   ═══════════════════════════════════ */
@media (max-width: 960px) {
  .cards-grid {
    max-width: 700px;
    padding: 0 16px;
  }

  .card {
    width: 200px;
    height: 155px;
  }

  .card-body {
    padding: 14px 14px 12px;
  }

  .card-icon-wrap {
    width: 34px;
    height: 34px;
    margin-bottom: 10px;
  }

  .card-icon-wrap svg {
    width: 17px;
    height: 17px;
  }

  .card-label {
    font-size: 13px;
  }

  .card-desc {
    font-size: 11px;
  }

  .strip-pill {
    padding: 7px 12px;
    gap: 5px;
  }

  .strip-label {
    font-size: 12px;
  }
}

@media (max-width: 700px) {
  .home-container {
    padding: 24px 16px 12px;
  }

  .cards-grid {
    max-width: 460px;
    gap: 10px;
  }

  .card {
    width: calc(50% - 5px);
    height: 140px;
  }

  .card-body {
    padding: 14px 12px 10px;
  }

  .card-icon-wrap {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    margin-bottom: 10px;
  }

  .card-icon-wrap svg {
    width: 17px;
    height: 17px;
  }

  .card-label {
    font-size: 13px;
  }

  .card-desc {
    font-size: 11px;
  }

  .card-arrow {
    display: none;
  }

  .strip-label {
    display: none;
  }

  .strip-pill {
    padding: 7px 10px;
  }

  .strip-divider {
    display: none;
  }
}
</style>
