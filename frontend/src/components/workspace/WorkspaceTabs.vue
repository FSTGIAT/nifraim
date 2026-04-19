<template>
  <!-- HOME MODE: Premium card grid -->
  <div v-if="viewMode === 'home'" class="home-container">
    <div class="cards-grid">
      <button
        v-for="(tab, idx) in tabs"
        :key="tab.id"
        :data-tour="'tab-' + tab.id"
        class="card"
        :style="{ '--i': idx, '--accent': tab.accent, '--accent-glow': tab.accentGlow }"
        @click="$emit('select-card', tab.id)"
      >
        <!-- Noise texture overlay -->
        <div class="card-noise"></div>
        <!-- Subtle gradient accent at top -->
        <div class="card-accent-line"></div>
        <!-- Content -->
        <div class="card-body">
          <span class="card-icon-wrap">
            <svg v-if="tab.id === 'production'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
            <svg v-else-if="tab.id === 'comparison'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
            </svg>
            <svg v-else-if="tab.id === 'commission-rates'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
              <line x1="3" y1="9" x2="21" y2="9"/>
              <line x1="3" y1="15" x2="21" y2="15"/>
              <line x1="9" y1="3" x2="9" y2="21"/>
              <line x1="15" y1="3" x2="15" y2="21"/>
            </svg>
            <svg v-else-if="tab.id === 'company-emails'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
              <polyline points="22,6 12,13 2,6"/>
            </svg>
            <svg v-else-if="tab.id === 'recruits'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
              <path d="M23 21v-2a4 4 0 00-3-3.87"/>
              <path d="M16 3.13a4 4 0 010 7.75"/>
            </svg>
            <svg v-else-if="tab.id === 'portal'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/>
              <polyline points="15 3 21 3 21 9"/>
              <line x1="10" y1="14" x2="21" y2="3"/>
            </svg>
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
        :data-tour="'tab-' + tab.id"
        class="strip-pill"
        :class="{ active: modelValue === tab.id }"
        :style="{ '--accent': tab.accent }"
        @click="$emit('update:modelValue', tab.id)"
      >
        <span class="strip-icon">
          <svg v-if="tab.id === 'production'" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
          <svg v-else-if="tab.id === 'comparison'" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
          </svg>
          <svg v-else-if="tab.id === 'commission-rates'" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
            <line x1="3" y1="9" x2="21" y2="9"/>
            <line x1="3" y1="15" x2="21" y2="15"/>
            <line x1="9" y1="3" x2="9" y2="21"/>
            <line x1="15" y1="3" x2="15" y2="21"/>
          </svg>
          <svg v-else-if="tab.id === 'company-emails'" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
            <polyline points="22,6 12,13 2,6"/>
          </svg>
          <svg v-else-if="tab.id === 'recruits'" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
            <circle cx="9" cy="7" r="4"/>
            <path d="M23 21v-2a4 4 0 00-3-3.87"/>
            <path d="M16 3.13a4 4 0 010 7.75"/>
          </svg>
          <svg v-else-if="tab.id === 'portal'" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/>
            <polyline points="15 3 21 3 21 9"/>
            <line x1="10" y1="14" x2="21" y2="3"/>
          </svg>
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
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: String, required: true },
  viewMode: { type: String, default: 'home' },
})
defineEmits(['update:modelValue', 'select-card', 'go-home'])

const tabs = [
  {
    id: 'production',
    label: 'פרודוקציה',
    description: 'העלאה וניתוח קבצי פרודוקציה',
    accent: '#6366f1',
    accentGlow: 'rgba(99, 102, 241, 0.15)',
  },
  {
    id: 'comparison',
    label: 'השוואת נפרעים',
    description: 'השוואת נפרעים מול פרודוקציה',
    accent: '#22d3ee',
    accentGlow: 'rgba(34, 211, 238, 0.15)',
  },
  {
    id: 'commission-rates',
    label: 'טבלת עמלות',
    description: 'ניהול שיעורי עמלות',
    accent: '#f59e0b',
    accentGlow: 'rgba(245, 158, 11, 0.15)',
  },
  {
    id: 'company-emails',
    label: 'אימיילים לחברות',
    description: 'אנשי קשר בחברות ביטוח',
    accent: '#3b82f6',
    accentGlow: 'rgba(59, 130, 246, 0.15)',
  },
  {
    id: 'recruits',
    label: 'ניהול תיק אישי',
    description: 'מעקב וניהול לקוחות מגויסים',
    accent: '#a78bfa',
    accentGlow: 'rgba(167, 139, 250, 0.15)',
  },
  {
    id: 'portal',
    label: 'פורטל לקוחות',
    description: 'יצירת ושיתוף פורטלים ללקוחות',
    accent: '#10b981',
    accentGlow: 'rgba(16, 185, 129, 0.15)',
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
  transform: translateY(-6px) scale(1.03);
  border-color: var(--primary);
  background: #fff;
  box-shadow:
    0 16px 48px rgba(245, 124, 0, 0.10),
    0 0 0 1px rgba(245, 124, 0, 0.15),
    0 4px 16px rgba(0, 0, 0, 0.06);
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
  height: 3px;
  width: 100%;
  background: linear-gradient(90deg, var(--primary), var(--accent), var(--primary));
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
  background: var(--primary-light);
  border: 1px solid rgba(245, 124, 0, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 14px;
  color: var(--primary);
  transition: background 0.3s ease, box-shadow 0.3s ease, transform 0.3s ease;
}

.card:hover .card-icon-wrap {
  background: var(--primary);
  color: #fff;
  box-shadow: 0 4px 16px rgba(245, 124, 0, 0.25);
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
  color: var(--primary);
  background: var(--primary-light);
}


/* ═══════════════════════════════════
   CONTENT MODE — Mini Strip
   ═══════════════════════════════════ */
.strip-container {
  display: flex;
  justify-content: center;
  padding: 10px 16px 6px;
  position: sticky;
  top: 56px;
  z-index: 90;
  background: var(--bg);
  animation: stripSlideDown 0.3s var(--transition) both;
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
  background: var(--text);
  color: #fff;
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
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
