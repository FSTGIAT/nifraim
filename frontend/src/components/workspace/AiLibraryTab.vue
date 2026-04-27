<template>
  <div class="ai-library">
    <!-- Floating blur circles (brand ambient) -->
    <div class="float-circle fc-1" aria-hidden="true"></div>
    <div class="float-circle fc-2" aria-hidden="true"></div>
    <div class="float-circle fc-3" aria-hidden="true"></div>
    <div class="float-circle fc-4" aria-hidden="true"></div>
    <div class="float-circle fc-5" aria-hidden="true"></div>
    <div class="float-circle fc-6" aria-hidden="true"></div>
    <div class="float-circle fc-7" aria-hidden="true"></div>

    <!-- Animated waves at bottom -->
    <div class="wave-bg" aria-hidden="true">
      <div class="shimmer"></div>
      <svg class="wave wave-1" viewBox="0 0 1440 200" preserveAspectRatio="none">
        <defs>
          <linearGradient id="ailwg1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#F57C00" stop-opacity="0.10"/>
            <stop offset="30%" stop-color="#FF9800" stop-opacity="0.06"/>
            <stop offset="60%" stop-color="#FFB74D" stop-opacity="0.10"/>
            <stop offset="100%" stop-color="#F57C00" stop-opacity="0.05"/>
          </linearGradient>
        </defs>
        <path fill="url(#ailwg1)" d="M0,100L60,90C120,80,240,60,360,66.7C480,73,600,107,720,113.3C840,120,960,100,1080,86.7C1200,73,1320,67,1380,63.3L1440,60L1440,200L0,200Z"/>
      </svg>
      <svg class="wave wave-2" viewBox="0 0 1440 200" preserveAspectRatio="none">
        <defs>
          <linearGradient id="ailwg2" x1="100%" y1="0%" x2="0%" y2="0%">
            <stop offset="0%" stop-color="#FFB74D" stop-opacity="0.08"/>
            <stop offset="40%" stop-color="#F57C00" stop-opacity="0.05"/>
            <stop offset="70%" stop-color="#FF9800" stop-opacity="0.08"/>
            <stop offset="100%" stop-color="#FFB74D" stop-opacity="0.04"/>
          </linearGradient>
        </defs>
        <path fill="url(#ailwg2)" d="M0,120L60,126.7C120,133,240,147,360,140C480,133,600,107,720,100C840,93,960,107,1080,120C1200,133,1320,147,1380,153.3L1440,160L1440,200L0,200Z"/>
      </svg>
      <svg class="wave wave-3" viewBox="0 0 1440 200" preserveAspectRatio="none">
        <defs>
          <linearGradient id="ailwg3" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#FF9800" stop-opacity="0.06"/>
            <stop offset="50%" stop-color="#FFB74D" stop-opacity="0.04"/>
            <stop offset="100%" stop-color="#F57C00" stop-opacity="0.07"/>
          </linearGradient>
        </defs>
        <path fill="url(#ailwg3)" d="M0,150L60,143.3C120,137,240,123,360,126.7C480,130,600,150,720,153.3C840,157,960,143,1080,133.3C1200,123,1320,117,1380,113.3L1440,110L1440,200L0,200Z"/>
      </svg>
    </div>

    <!-- Intro -->
    <header class="lib-intro">
      <div class="lib-intro-icon" aria-hidden="true">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M4 19.5A2.5 2.5 0 016.5 17H20"/>
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/>
          <path d="M13 7l1 2 2 1-2 1-1 2-1-2-2-1 2-1z"/>
        </svg>
      </div>
      <div class="lib-intro-text">
        <h2 class="lib-title">ספריית AI</h2>
        <p class="lib-sub">כל הקבצים, הטבלאות והנתונים שהעוזר החכם משתמש בהם כדי לענות על השאלות שלך. כל הנתונים שייכים לך ולתיק שלך בלבד.</p>
      </div>
      <button class="lib-refresh" :disabled="loading" @click="load" type="button" title="רענן">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" :class="{ spinning: loading }">
          <polyline points="23 4 23 10 17 10"/>
          <polyline points="1 20 1 14 7 14"/>
          <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
        </svg>
        <span>רענן</span>
      </button>
    </header>

    <!-- Error banner with retry -->
    <div v-if="error && !loading" class="lib-error">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
      <span class="lib-error-text">{{ error }}</span>
      <button class="lib-error-retry" @click="load" type="button">נסה שוב</button>
    </div>

    <!-- Search (shown once we have data) -->
    <div v-if="data && !isCompletelyEmpty" class="lib-search">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
      </svg>
      <input
        v-model="searchRaw"
        class="lib-search-input"
        type="search"
        placeholder="חפש קובץ או חברה…"
        aria-label="חפש בספרייה"
      />
      <button
        v-if="searchRaw"
        class="lib-search-clear"
        @click="searchRaw = ''"
        type="button"
        aria-label="נקה חיפוש"
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
    </div>

    <!-- Summary strip -->
    <section v-if="data && !loading" class="lib-summary-strip">
      <div class="lib-chip">
        <span class="lib-chip-value ltr-number">{{ productionTotal }}</span>
        <span class="lib-chip-label">קבצי פרודוקציה</span>
      </div>
      <div class="lib-chip">
        <span class="lib-chip-value ltr-number">{{ commissionTotal }}</span>
        <span class="lib-chip-label">קבצי נפרעים</span>
      </div>
      <div class="lib-chip" v-if="data.myfile">
        <span class="lib-chip-value ltr-number">{{ data.myfile.count.toLocaleString() }}</span>
        <span class="lib-chip-label">לקוחות בתיק אישי</span>
      </div>
      <div class="lib-chip" v-if="data.rates">
        <span class="lib-chip-value ltr-number">{{ ratesTotal }}</span>
        <span class="lib-chip-label">שורות עמלות</span>
      </div>
    </section>

    <!-- Loading skeleton -->
    <div v-if="loading && !data" class="lib-skeleton" aria-hidden="true">
      <div class="sk-intro"></div>
      <div class="sk-chips">
        <div class="sk-chip" v-for="n in 4" :key="n"></div>
      </div>
      <div class="sk-section" v-for="n in 2" :key="n">
        <div class="sk-row sk-row-lg"></div>
        <div class="sk-row" v-for="r in 3" :key="r"></div>
      </div>
    </div>

    <template v-else-if="data">
      <!-- Quick collapse / expand all -->
      <div v-if="!isCompletelyEmpty" class="lib-toolbar">
        <button
          class="lib-toolbar-btn"
          type="button"
          @click="toggleAllSections"
          :title="allSectionsOpen ? 'צמצם את כל הספרייה' : 'הרחב את כל הספרייה'"
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" :class="{ 'is-rotated': !allSectionsOpen }">
            <polyline points="18 15 12 9 6 15"/>
          </svg>
          <span>{{ allSectionsOpen ? 'צמצם הכל' : 'הרחב הכל' }}</span>
        </button>
      </div>

      <!-- Production -->
      <section class="lib-section" :class="{ 'is-collapsed': !sectionOpen.production }">
        <button
          class="lib-section-head lib-section-head-btn"
          type="button"
          :aria-expanded="sectionOpen.production"
          aria-controls="lib-body-production"
          @click="toggleSection('production')"
        >
          <div class="lib-section-icon lib-icon--prod" aria-hidden="true">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
          </div>
          <div class="lib-section-titles">
            <h3 class="lib-section-title">קבצי פרודוקציה</h3>
            <span class="lib-section-desc">כל קובץ שהעלית — ה-AI רואה את הפעיל + את ההיסטוריה</span>
          </div>
          <span class="lib-section-badge ltr-number">
            <template v-if="searchQuery">{{ filteredProduction.length }} / </template>{{ productionTotal }}
          </span>
          <svg
            class="lib-section-chevron"
            :class="{ 'is-closed': !sectionOpen.production }"
            width="14" height="14" viewBox="0 0 24 24"
            fill="none" stroke="currentColor" stroke-width="2.5"
            stroke-linecap="round" stroke-linejoin="round"
            aria-hidden="true"
          >
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </button>

        <transition name="lib-collapse">
          <div v-show="sectionOpen.production" class="lib-section-body" id="lib-body-production">
        <div v-if="!filteredProduction.length && !productionTotal" class="lib-empty">אין קבצי פרודוקציה — העלה קובץ בלשונית "פרודוקציה".</div>
        <div v-else-if="!filteredProduction.length" class="lib-empty">אין תוצאות חיפוש.</div>
        <template v-else>
          <ul class="lib-list">
            <li
              v-for="f in visibleProduction"
              :key="f.id"
              class="lib-item"
              :class="{ 'is-active': f.is_active }"
            >
              <div class="lib-item-mark" aria-hidden="true"></div>
              <div class="lib-item-main">
                <div class="lib-item-top">
                  <span class="lib-item-title" :title="f.filename">{{ f.period_label || cleanFilename(f.filename) }}</span>
                  <span v-if="f.is_active" class="lib-pill lib-pill--active">פעיל</span>
                  <span v-else class="lib-pill lib-pill--historic">היסטורי</span>
                </div>
                <div class="lib-item-meta">
                  <span v-if="f.uploaded_at">הועלה {{ formatDate(f.uploaded_at) }}</span>
                  <span v-if="f.record_count">· <span class="ltr-number">{{ f.record_count.toLocaleString() }}</span> רשומות</span>
                  <span v-if="f.unique_clients">· <span class="ltr-number">{{ f.unique_clients.toLocaleString() }}</span> לקוחות ייחודיים</span>
                </div>
                <div v-if="f.total_premium || f.total_accumulation" class="lib-item-metrics">
                  <span v-if="f.total_premium"><span class="lib-metric-label">פרמיה</span> <span class="ltr-number">{{ formatAmount(f.total_premium) }}</span></span>
                  <span v-if="f.total_accumulation"><span class="lib-metric-label">צבירה</span> <span class="ltr-number">{{ formatAmount(f.total_accumulation) }}</span></span>
                </div>
              </div>
            </li>
          </ul>
          <button
            v-if="filteredProduction.length > productionVisibleLimit && !productionExpanded"
            class="lib-show-more"
            type="button"
            @click="productionExpanded = true"
          >
            <span>הצג את כל {{ filteredProduction.length }} הקבצים</span>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="6 9 12 15 18 9"/>
            </svg>
          </button>
          <button
            v-else-if="productionExpanded && filteredProduction.length > productionVisibleLimit"
            class="lib-show-more lib-show-more--collapse"
            type="button"
            @click="productionExpanded = false"
          >
            <span>הצג פחות</span>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="18 15 12 9 6 15"/>
            </svg>
          </button>
        </template>
          </div>
        </transition>
      </section>

      <!-- Commission / נפרעים -->
      <section class="lib-section" :class="{ 'is-collapsed': !sectionOpen.commission }">
        <button
          class="lib-section-head lib-section-head-btn"
          type="button"
          :aria-expanded="sectionOpen.commission"
          aria-controls="lib-body-commission"
          @click="toggleSection('commission')"
        >
          <div class="lib-section-icon lib-icon--comm" aria-hidden="true">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="8" cy="8" r="6"/>
              <path d="M18.09 10.37A6 6 0 1110.34 18"/>
            </svg>
          </div>
          <div class="lib-section-titles">
            <h3 class="lib-section-title">קבצי נפרעים (עמלות)</h3>
            <span class="lib-section-desc">מקובצים לפי חברת ביטוח</span>
          </div>
          <span class="lib-section-badge ltr-number">
            <template v-if="searchQuery">{{ filteredCommissionCount }} / </template>{{ commissionTotal }}
          </span>
          <svg
            class="lib-section-chevron"
            :class="{ 'is-closed': !sectionOpen.commission }"
            width="14" height="14" viewBox="0 0 24 24"
            fill="none" stroke="currentColor" stroke-width="2.5"
            stroke-linecap="round" stroke-linejoin="round"
            aria-hidden="true"
          >
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </button>

        <transition name="lib-collapse">
          <div v-show="sectionOpen.commission" class="lib-section-body" id="lib-body-commission">
        <div v-if="!filteredCommission.length && !commissionTotal" class="lib-empty">אין קבצי נפרעים — העלה בלשונית "השוואת נפרעים".</div>
        <div v-else-if="!filteredCommission.length" class="lib-empty">אין תוצאות חיפוש.</div>
        <ul v-else class="lib-list lib-list--grouped">
          <li v-for="group in filteredCommission" :key="group.company" class="lib-group">
            <button
              class="lib-group-head"
              type="button"
              :aria-expanded="isGroupOpen(group)"
              @click="toggleGroup(group.company)"
            >
              <svg
                class="lib-group-chevron"
                :class="{ 'is-open': isGroupOpen(group) }"
                width="14" height="14" viewBox="0 0 24 24"
                fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"
                aria-hidden="true"
              >
                <polyline points="9 18 15 12 9 6"/>
              </svg>
              <span class="lib-group-name" :title="group.company">{{ group.company }}</span>
              <span class="lib-group-count ltr-number">{{ group.files.length }} קבצים</span>
            </button>
            <transition name="lib-collapse">
              <div v-if="isGroupOpen(group)" class="lib-group-items">
                <div v-for="f in group.files" :key="f.id" class="lib-subitem">
                  <span class="lib-subitem-title" :title="f.filename">{{ cleanFilename(f.filename) }}</span>
                  <span class="lib-subitem-meta">
                    <span v-if="f.uploaded_at">{{ formatDate(f.uploaded_at) }}</span>
                    <span v-if="f.record_count"> · <span class="ltr-number">{{ f.record_count.toLocaleString() }}</span> רשומות</span>
                  </span>
                </div>
              </div>
            </transition>
          </li>
        </ul>
          </div>
        </transition>
      </section>

      <!-- My File -->
      <section class="lib-section" v-if="data.myfile" :class="{ 'is-collapsed': !sectionOpen.myfile }">
        <button
          class="lib-section-head lib-section-head-btn"
          type="button"
          :aria-expanded="sectionOpen.myfile"
          aria-controls="lib-body-myfile"
          @click="toggleSection('myfile')"
        >
          <div class="lib-section-icon lib-icon--myfile" aria-hidden="true">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
              <path d="M23 21v-2a4 4 0 00-3-3.87"/>
              <path d="M16 3.13a4 4 0 010 7.75"/>
            </svg>
          </div>
          <div class="lib-section-titles">
            <h3 class="lib-section-title">קובץ אישי (תיק גיוסים)</h3>
            <span class="lib-section-desc">לקוחות שגייסת — כולל תאריכי חתימה</span>
          </div>
          <span class="lib-section-badge ltr-number">{{ data.myfile.count.toLocaleString() }}</span>
          <svg
            class="lib-section-chevron"
            :class="{ 'is-closed': !sectionOpen.myfile }"
            width="14" height="14" viewBox="0 0 24 24"
            fill="none" stroke="currentColor" stroke-width="2.5"
            stroke-linecap="round" stroke-linejoin="round"
            aria-hidden="true"
          >
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </button>
        <transition name="lib-collapse">
          <div v-show="sectionOpen.myfile" class="lib-section-body" id="lib-body-myfile">
        <!-- Per-category split: each category (financial / insurance) is replaced
             independently on file upload. Total = sum of both. -->
        <div v-if="myfileCategoryBreakdown.length > 1" class="lib-cat-strip">
          <div
            v-for="c in myfileCategoryBreakdown"
            :key="c.category"
            class="lib-cat-chip"
            :class="'lib-cat-chip--' + c.category"
          >
            <span class="lib-cat-chip-label">{{ c.label }}</span>
            <span class="lib-cat-chip-value ltr-number">{{ c.count.toLocaleString() }}</span>
          </div>
          <span class="lib-cat-note">כל קטגוריה מוחלפת בנפרד בהעלאת קובץ חדש</span>
        </div>

        <div class="lib-stats-row">
          <div class="lib-stat">
            <span class="lib-stat-value ltr-number">{{ data.myfile.count.toLocaleString() }}</span>
            <span class="lib-stat-label">סה"כ לקוחות</span>
          </div>
          <div class="lib-stat">
            <span class="lib-stat-value ltr-number">{{ data.myfile.companies }}</span>
            <span class="lib-stat-label">חברות ייחודיות</span>
          </div>
          <div class="lib-stat" v-if="data.myfile.sign_date_min">
            <span class="lib-stat-value ltr-number">{{ formatDate(data.myfile.sign_date_min) }}</span>
            <span class="lib-stat-label">חתימה ראשונה</span>
          </div>
          <div class="lib-stat" v-if="data.myfile.sign_date_max">
            <span class="lib-stat-value ltr-number">{{ formatDate(data.myfile.sign_date_max) }}</span>
            <span class="lib-stat-label">חתימה אחרונה</span>
          </div>
        </div>
          </div>
        </transition>
      </section>

      <!-- Rates -->
      <section class="lib-section" v-if="data.rates" :class="{ 'is-collapsed': !sectionOpen.rates }">
        <button
          class="lib-section-head lib-section-head-btn"
          type="button"
          :aria-expanded="sectionOpen.rates"
          aria-controls="lib-body-rates"
          @click="toggleSection('rates')"
        >
          <div class="lib-section-icon lib-icon--rates" aria-hidden="true">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
              <line x1="3" y1="9" x2="21" y2="9"/>
              <line x1="3" y1="15" x2="21" y2="15"/>
              <line x1="9" y1="3" x2="9" y2="21"/>
              <line x1="15" y1="3" x2="15" y2="21"/>
            </svg>
          </div>
          <div class="lib-section-titles">
            <h3 class="lib-section-title">טבלאות עמלות</h3>
            <span class="lib-section-desc">שיעורי עמלה לנפרעים וליקפים — ה-AI משתמש בהם לחישובים</span>
          </div>
          <span class="lib-section-badge ltr-number">{{ ratesTotal }}</span>
          <svg
            class="lib-section-chevron"
            :class="{ 'is-closed': !sectionOpen.rates }"
            width="14" height="14" viewBox="0 0 24 24"
            fill="none" stroke="currentColor" stroke-width="2.5"
            stroke-linecap="round" stroke-linejoin="round"
            aria-hidden="true"
          >
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </button>
        <transition name="lib-collapse">
          <div v-show="sectionOpen.rates" class="lib-section-body" id="lib-body-rates">
        <div class="lib-stats-row">
          <div class="lib-stat">
            <span class="lib-stat-value ltr-number">{{ data.rates.nifraim.count.toLocaleString() }}</span>
            <span class="lib-stat-label">שורות נפרעים</span>
          </div>
          <div class="lib-stat" v-if="data.rates.nifraim.companies">
            <span class="lib-stat-value ltr-number">{{ data.rates.nifraim.companies }}</span>
            <span class="lib-stat-label">חברות (נפרעים)</span>
          </div>
          <div class="lib-stat">
            <span class="lib-stat-value ltr-number">{{ data.rates.volume.count.toLocaleString() }}</span>
            <span class="lib-stat-label">שורות היקפים</span>
          </div>
          <div class="lib-stat" v-if="data.rates.volume.companies">
            <span class="lib-stat-value ltr-number">{{ data.rates.volume.companies }}</span>
            <span class="lib-stat-label">חברות (היקפים)</span>
          </div>
        </div>
          </div>
        </transition>
      </section>

      <!-- ─── תיקיות סוכנים — only for super-users (when scope=agency) ─── -->
      <section
        class="lib-section"
        v-if="agencyAgents.length"
        :class="{ 'is-collapsed': !sectionOpen.agents }"
      >
        <button
          class="lib-section-head lib-section-head-btn"
          type="button"
          :aria-expanded="sectionOpen.agents"
          aria-controls="lib-body-agents"
          @click="toggleSection('agents')"
        >
          <div class="lib-section-icon lib-icon--agents" aria-hidden="true">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
            </svg>
          </div>
          <div class="lib-section-titles">
            <h3 class="lib-section-title">תיקיות סוכנים</h3>
            <span class="lib-section-desc">תיקייה לכל סוכן בסוכנות — קבצים שהעלה</span>
          </div>
          <span class="lib-section-badge ltr-number">
            <template v-if="searchQuery">{{ filteredAgentFolders.length }} / </template>{{ agencyAgents.length }}
          </span>
          <svg
            class="lib-section-chevron"
            :class="{ 'is-closed': !sectionOpen.agents }"
            width="14" height="14" viewBox="0 0 24 24"
            fill="none" stroke="currentColor" stroke-width="2.5"
            stroke-linecap="round" stroke-linejoin="round"
            aria-hidden="true"
          >
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </button>
        <transition name="lib-collapse">
          <div v-show="sectionOpen.agents" class="lib-section-body" id="lib-body-agents">
            <div v-if="!filteredAgentFolders.length" class="lib-empty">אין תוצאות חיפוש.</div>
            <ul v-else class="lib-list lib-list--grouped">
              <li
                v-for="agent in filteredAgentFolders"
                :key="agent.user_id"
                class="lib-group"
              >
                <button
                  class="lib-group-head"
                  type="button"
                  :aria-expanded="isAgentOpen(agent.user_id)"
                  @click="toggleAgent(agent.user_id)"
                >
                  <svg
                    class="lib-group-chevron"
                    :class="{ 'is-open': isAgentOpen(agent.user_id) }"
                    width="14" height="14" viewBox="0 0 24 24"
                    fill="none" stroke="currentColor" stroke-width="2.5"
                    stroke-linecap="round" stroke-linejoin="round"
                    aria-hidden="true"
                  >
                    <polyline points="9 18 15 12 9 6"/>
                  </svg>
                  <span class="lib-agent-avatar" aria-hidden="true">{{ agentInitials(agent.name) }}</span>
                  <div class="lib-agent-info">
                    <span class="lib-agent-name">{{ agent.name }}</span>
                    <span class="lib-agent-email ltr-number">{{ agent.email }}</span>
                  </div>
                  <span class="lib-agent-tags">
                    <span v-if="agent.production?.length" class="lib-agent-tag tag-prod">
                      <span class="ltr-number">{{ agent.production.length }}</span> פרודוקציה
                    </span>
                    <span v-if="agent.commission?.length" class="lib-agent-tag tag-comm">
                      <span class="ltr-number">{{ commissionFileCount(agent.commission) }}</span> נפרעים
                    </span>
                    <span v-if="agent.myfile?.count" class="lib-agent-tag tag-myfile">
                      <span class="ltr-number">{{ agent.myfile.count.toLocaleString() }}</span> תיק
                    </span>
                    <span v-if="ratesCount(agent.rates)" class="lib-agent-tag tag-rates">
                      <span class="ltr-number">{{ ratesCount(agent.rates) }}</span> עמלות
                    </span>
                    <span v-if="!agent.production?.length && !agent.commission?.length && !agent.myfile?.count && !ratesCount(agent.rates)" class="lib-agent-tag tag-empty">
                      ללא קבצים
                    </span>
                  </span>
                </button>

                <transition name="lib-collapse">
                  <div v-show="isAgentOpen(agent.user_id)" class="lib-agent-body">
                    <!-- Production files -->
                    <div v-if="agent.production?.length" class="lib-agent-block">
                      <div class="lib-agent-block-h">קבצי פרודוקציה</div>
                      <ul class="lib-list">
                        <li
                          v-for="f in agent.production"
                          :key="'p-'+f.id"
                          class="lib-item"
                          :class="{ 'is-active': f.is_active }"
                        >
                          <div class="lib-item-mark" aria-hidden="true"></div>
                          <div class="lib-item-main">
                            <div class="lib-item-top">
                              <span class="lib-item-title" :title="f.filename">{{ f.period_label || cleanFilename(f.filename) }}</span>
                              <span v-if="f.is_active" class="lib-pill lib-pill--active">פעיל</span>
                              <span v-else class="lib-pill lib-pill--historic">היסטורי</span>
                            </div>
                            <div class="lib-item-meta">
                              <span v-if="f.uploaded_at">הועלה {{ formatDate(f.uploaded_at) }}</span>
                              <span v-if="f.record_count">· <span class="ltr-number">{{ f.record_count.toLocaleString() }}</span> רשומות</span>
                              <span v-if="f.unique_clients">· <span class="ltr-number">{{ f.unique_clients.toLocaleString() }}</span> לקוחות</span>
                            </div>
                          </div>
                        </li>
                      </ul>
                    </div>

                    <!-- Commission files grouped by company -->
                    <div v-if="agent.commission?.length" class="lib-agent-block">
                      <div class="lib-agent-block-h">קבצי נפרעים (עמלות)</div>
                      <ul class="lib-list">
                        <li v-for="g in agent.commission" :key="'c-'+g.company" class="lib-item">
                          <div class="lib-item-mark" aria-hidden="true"></div>
                          <div class="lib-item-main">
                            <div class="lib-item-top">
                              <span class="lib-item-title">{{ g.company }}</span>
                              <span class="lib-pill lib-pill--historic ltr-number">{{ g.files.length }}</span>
                            </div>
                            <div class="lib-item-meta">
                              <span v-for="(f, idx) in g.files.slice(0, 3)" :key="f.id">
                                <span v-if="idx > 0">· </span>
                                {{ cleanFilename(f.filename) }}
                              </span>
                              <span v-if="g.files.length > 3">· +{{ g.files.length - 3 }} נוספים</span>
                            </div>
                          </div>
                        </li>
                      </ul>
                    </div>

                    <!-- My file (recruits) -->
                    <div v-if="agent.myfile?.count" class="lib-agent-block">
                      <div class="lib-agent-block-h">תיק אישי</div>
                      <div class="lib-stats-row">
                        <div class="lib-stat">
                          <span class="lib-stat-value ltr-number">{{ agent.myfile.count.toLocaleString() }}</span>
                          <span class="lib-stat-label">לקוחות</span>
                        </div>
                        <div class="lib-stat" v-if="agent.myfile.companies">
                          <span class="lib-stat-value ltr-number">{{ agent.myfile.companies }}</span>
                          <span class="lib-stat-label">חברות</span>
                        </div>
                      </div>
                    </div>

                    <!-- Rates -->
                    <div v-if="ratesCount(agent.rates)" class="lib-agent-block">
                      <div class="lib-agent-block-h">טבלאות עמלות</div>
                      <div class="lib-stats-row">
                        <div class="lib-stat" v-if="agent.rates?.nifraim?.count">
                          <span class="lib-stat-value ltr-number">{{ agent.rates.nifraim.count.toLocaleString() }}</span>
                          <span class="lib-stat-label">נפרעים</span>
                        </div>
                        <div class="lib-stat" v-if="agent.rates?.volume?.count">
                          <span class="lib-stat-value ltr-number">{{ agent.rates.volume.count.toLocaleString() }}</span>
                          <span class="lib-stat-label">היקפים</span>
                        </div>
                      </div>
                    </div>

                    <div
                      v-if="!agent.production?.length && !agent.commission?.length && !agent.myfile?.count && !ratesCount(agent.rates)"
                      class="lib-empty"
                    >
                      הסוכן עדיין לא העלה קבצים.
                    </div>
                  </div>
                </transition>
              </li>
            </ul>
          </div>
        </transition>
      </section>

      <!-- Complete empty state -->
      <div v-if="isCompletelyEmpty" class="lib-empty-all">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
        </svg>
        <p>אין עדיין נתונים בספרייה. ברגע שתעלה קובץ פרודוקציה, נפרעים או תגייס לקוחות — ה-AI יראה אותם כאן.</p>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import api from '../../api/client.js'

const props = defineProps({
  // 'agent' (default) → /api/ai/knowledge          (user's own files)
  // 'agency' (super-user only) → /api/ai/knowledge?scope=agency
  //   adds an `agents:[]` array → renders a "תיקיות סוכנים" section
  scope: { type: String, default: 'agent' },
})

const data = ref(null)
const loading = ref(false)
const error = ref(null)

// Search (debounced)
const searchRaw = ref('')
const searchQuery = ref('')
let searchTimer = null
watch(searchRaw, (v) => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { searchQuery.value = v.trim().toLowerCase() }, 150)
})

// Production show-more
const productionVisibleLimit = 6
const productionExpanded = ref(false)

// Section open/closed state — persisted to localStorage
const SECTION_STORAGE_KEY = 'ai_library_sections'
const sectionOpen = reactive({
  production: true,
  commission: true,
  myfile: true,
  rates: true,
  agents: true,
})
try {
  const stored = JSON.parse(localStorage.getItem(SECTION_STORAGE_KEY) || '{}')
  Object.assign(sectionOpen, stored)
} catch { /* ignore */ }

function toggleSection(id) {
  sectionOpen[id] = !sectionOpen[id]
  try {
    localStorage.setItem(SECTION_STORAGE_KEY, JSON.stringify(sectionOpen))
  } catch { /* ignore */ }
}
const allSectionsOpen = computed(() =>
  Object.values(sectionOpen).every(Boolean)
)
function toggleAllSections() {
  const target = !allSectionsOpen.value
  for (const k of Object.keys(sectionOpen)) sectionOpen[k] = target
  try {
    localStorage.setItem(SECTION_STORAGE_KEY, JSON.stringify(sectionOpen))
  } catch { /* ignore */ }
}

// Commission group open/closed
const manualGroupState = reactive({}) // company -> bool (user override)
function autoGroupOpen(group, groupCount) {
  // expanded if <=3 files; or if only one group; or if filtering
  if (searchQuery.value) return true
  if (group.files.length <= 3) return true
  if (groupCount <= 2) return true
  // first group of many stays open by default
  return group === filteredCommission.value[0]
}
function isGroupOpen(group) {
  if (group.company in manualGroupState) return manualGroupState[group.company]
  return autoGroupOpen(group, filteredCommission.value.length)
}
function toggleGroup(company) {
  const group = filteredCommission.value.find(g => g.company === company)
  const current = group ? isGroupOpen(group) : false
  manualGroupState[company] = !current
}

async function load() {
  loading.value = true
  error.value = null

  // Dev-only scale mock
  if (import.meta.env?.DEV && typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('mock') === 'scale') {
    await new Promise(r => setTimeout(r, 450)) // show skeleton
    data.value = buildScaleMock()
    loading.value = false
    return
  }

  try {
    const url = props.scope === 'agency' ? '/ai/knowledge?scope=agency' : '/ai/knowledge'
    const res = await api.get(url)
    data.value = res.data
    productionExpanded.value = false
  } catch (e) {
    error.value = e.response?.data?.detail || 'שגיאה בטעינת הספרייה'
  } finally {
    loading.value = false
  }
}

onMounted(load)

const CATEGORY_LABELS = { financial: 'פיננסי', insurance: 'ביטוח' }
const myfileCategoryBreakdown = computed(() => {
  const arr = data.value?.myfile?.by_category || []
  return arr
    .filter(c => c.count > 0)
    .map(c => ({
      category: c.category,
      label: CATEGORY_LABELS[c.category] || c.category,
      count: c.count,
    }))
})

const productionTotal = computed(() => data.value?.production?.length || 0)
const commissionTotal = computed(() =>
  (data.value?.commission || []).reduce((sum, g) => sum + (g.files?.length || 0), 0)
)
const ratesTotal = computed(() => {
  const r = data.value?.rates
  if (!r) return 0
  return (r.nifraim?.count || 0) + (r.volume?.count || 0)
})
const isCompletelyEmpty = computed(() =>
  productionTotal.value === 0 &&
  commissionTotal.value === 0 &&
  !data.value?.myfile &&
  !data.value?.rates
)

// Filtered production
const filteredProduction = computed(() => {
  const list = data.value?.production || []
  const q = searchQuery.value
  if (!q) return list
  return list.filter(f =>
    (f.filename || '').toLowerCase().includes(q) ||
    (f.period_label || '').toLowerCase().includes(q)
  )
})

const visibleProduction = computed(() =>
  productionExpanded.value
    ? filteredProduction.value
    : filteredProduction.value.slice(0, productionVisibleLimit)
)

// Filtered commission (groups kept only if at least one matching file; company name also matches)
const filteredCommission = computed(() => {
  const groups = data.value?.commission || []
  const q = searchQuery.value
  if (!q) return groups
  const out = []
  for (const g of groups) {
    const companyMatch = (g.company || '').toLowerCase().includes(q)
    const fileMatches = (g.files || []).filter(f => (f.filename || '').toLowerCase().includes(q))
    if (companyMatch && !fileMatches.length) {
      out.push(g) // company matched: show all its files
    } else if (fileMatches.length) {
      out.push({ ...g, files: fileMatches })
    }
  }
  return out
})

const filteredCommissionCount = computed(() =>
  filteredCommission.value.reduce((s, g) => s + g.files.length, 0)
)

// ── Agency-scope: per-agent folders ─────────────────────────────────────
const agencyAgents = computed(() => data.value?.agents || [])
const filteredAgentFolders = computed(() => {
  const list = agencyAgents.value
  const q = searchQuery.value
  if (!q) return list
  return list.filter((a) => {
    if ((a.name || '').toLowerCase().includes(q)) return true
    if ((a.email || '').toLowerCase().includes(q)) return true
    if ((a.production || []).some(f => (f.filename || '').toLowerCase().includes(q))) return true
    if ((a.commission || []).some(g =>
      (g.company || '').toLowerCase().includes(q) ||
      (g.files || []).some(f => (f.filename || '').toLowerCase().includes(q))
    )) return true
    return false
  })
})
const openAgents = reactive(new Set())
function isAgentOpen(uid) {
  if (searchQuery.value) return true // expand all matching agents while searching
  return openAgents.has(uid)
}
function toggleAgent(uid) {
  if (openAgents.has(uid)) openAgents.delete(uid)
  else openAgents.add(uid)
}
function agentInitials(name) {
  if (!name) return '?'
  return name.split(/\s+/).slice(0, 2).map(p => (p || '')[0] || '').join('').toUpperCase()
}
function commissionFileCount(groups) {
  return (groups || []).reduce((s, g) => s + (g.files?.length || 0), 0)
}
function ratesCount(rates) {
  if (!rates) return 0
  return (rates.nifraim?.count || 0) + (rates.volume?.count || 0)
}

// Reset pagination whenever the search changes
watch(searchQuery, () => { productionExpanded.value = false })

function cleanFilename(name) {
  if (!name) return ''
  return name.replace(/\.(xlsx|xls)$/i, '')
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return ''
  return d.toLocaleDateString('he-IL', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

function formatAmount(val) {
  if (!val) return '₪0'
  const num = Math.round(val)
  return '₪' + num.toLocaleString('en-US')
}

// ---------- Dev-only scale mock ----------
function buildScaleMock() {
  const months = ['ינואר','פברואר','מרץ','אפריל','מאי','יוני','יולי','אוגוסט','ספטמבר','אוקטובר','נובמבר','דצמבר']
  const today = new Date()
  const production = []
  // 14 files — one active, one with long filename, some missing period_label
  for (let i = 0; i < 14; i++) {
    const d = new Date(today); d.setMonth(today.getMonth() - i)
    const mi = d.getMonth()
    production.push({
      id: 'prod-' + i,
      filename: i === 3
        ? 'דוח פרודוקציה מלא ומפורט של אפריל 2025 עם פירוט לפי חברה וסוג מוצר.xlsx'
        : `דוח פרודוקציה ${months[mi]} ${String(d.getFullYear()).slice(2)}.xlsx`,
      is_active: i === 0,
      uploaded_at: d.toISOString(),
      record_count: 1800 + i * 37,
      unique_clients: 540 + i * 4,
      total_premium: 120000 + i * 3500,
      total_accumulation: 280000000 + i * 1500000,
      period_label: i % 5 === 0 ? null : `${d.getFullYear()}-${String(mi + 1).padStart(2, '0')}`,
    })
  }
  const companies = ['מור','הפניקס','מגדל','מנורה','כלל חיים','אלטשולר','איילון','הראל','הכשרה','חברת ביטוח עם שם ארוך במיוחד שצריך לקצר']
  const commission = companies.map((c, i) => {
    const n = (i === 2) ? 9 : (3 + (i % 4)) // one company with 9 files
    return {
      company: c,
      files: Array.from({ length: n }, (_, j) => {
        const d = new Date(today); d.setMonth(today.getMonth() - j)
        return {
          id: `comm-${i}-${j}`,
          filename: `${c} עמלות ${months[d.getMonth()]} ${String(d.getFullYear()).slice(2)}.xlsx`,
          uploaded_at: d.toISOString(),
          record_count: 200 + j * 17,
          format_type: 'nifraim',
        }
      })
    }
  })
  return {
    production,
    commission,
    myfile: { count: 1247, companies: 22, sign_date_min: '2017-04-20', sign_date_max: today.toISOString().slice(0, 10) },
    rates: { nifraim: { count: 18, companies: 14 }, volume: { count: 15, companies: 12 } },
  }
}
</script>

<style scoped>
.ai-library {
  position: relative;
  max-width: 1100px;
  margin: 0 auto;
  padding: 24px 24px 48px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  z-index: 1; /* keep content above the ambient bg layer */
}

/* ===== Ambient brand background (floating circles + waves) ===== */
.float-circle {
  position: fixed;
  border-radius: 50%;
  pointer-events: none;
  z-index: 0;
}
.fc-1 {
  width: 220px; height: 220px;
  top: 10%; right: -60px;
  background: rgba(245, 124, 0, 0.045);
  border: 1px solid rgba(245, 124, 0, 0.06);
  animation: floatBob 8s ease-in-out infinite;
}
.fc-2 {
  width: 160px; height: 160px;
  bottom: 25%; left: -40px;
  background: rgba(245, 124, 0, 0.035);
  border: 1px solid rgba(245, 124, 0, 0.05);
  animation: floatBob 6.5s ease-in-out infinite reverse;
}
.fc-3 {
  width: 90px; height: 90px;
  top: 30%; left: 8%;
  background: rgba(245, 124, 0, 0.05);
  animation: floatBob 10s ease-in-out infinite 2s;
}
.fc-4 {
  width: 120px; height: 120px;
  top: 55%; right: 6%;
  background: rgba(245, 124, 0, 0.03);
  border: 1px solid rgba(245, 124, 0, 0.04);
  animation: floatBob 9s ease-in-out infinite 1s;
}
.fc-5 {
  width: 50px; height: 50px;
  top: 18%; right: 22%;
  background: rgba(255, 152, 0, 0.055);
  animation: floatBob 7s ease-in-out infinite 3s;
}
.fc-6 {
  width: 280px; height: 280px;
  bottom: 8%; right: -90px;
  background: rgba(245, 124, 0, 0.025);
  border: 1px solid rgba(245, 124, 0, 0.035);
  animation: floatBob 12s ease-in-out infinite 0.5s;
}
.fc-7 {
  width: 65px; height: 65px;
  bottom: 35%; left: 18%;
  background: rgba(255, 183, 77, 0.06);
  border: 1px solid rgba(255, 183, 77, 0.05);
  animation: floatBob 8.5s ease-in-out infinite reverse 1.5s;
}

@keyframes floatBob {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  33% { transform: translateY(-16px) rotate(2deg); }
  66% { transform: translateY(8px) rotate(-1deg); }
}

/* Waves fixed to bottom */
.wave-bg {
  position: fixed;
  left: 0; right: 0; bottom: 0;
  height: 200px;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
}
.shimmer {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 100%;
  z-index: 1;
  overflow: hidden;
  mask-image: linear-gradient(to top, rgba(0,0,0,1) 30%, rgba(0,0,0,0.3) 60%, transparent 100%);
  -webkit-mask-image: linear-gradient(to top, rgba(0,0,0,1) 30%, rgba(0,0,0,0.3) 60%, transparent 100%);
}
.shimmer::after {
  content: '';
  position: absolute;
  top: 0; left: -80%;
  width: 50%; height: 100%;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 200, 100, 0.1) 35%,
    rgba(255, 255, 255, 0.15) 50%,
    rgba(255, 200, 100, 0.1) 65%,
    transparent 100%
  );
  animation: shimmerSweep 7s ease-in-out infinite;
}
@keyframes shimmerSweep {
  0%   { left: -80%; }
  100% { left: 180%; }
}
.wave {
  position: absolute;
  bottom: 0; left: 0;
  width: 200%; height: 100%;
}
.wave-1 { animation: waveSlide 14s linear infinite; }
.wave-2 { animation: waveSlide 18s linear infinite reverse; }
.wave-3 { animation: waveSlide 22s linear infinite; }

@keyframes waveSlide {
  0%   { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}

/* ===== Intro ===== */
.lib-intro {
  position: relative;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 22px;
  border-radius: var(--radius-lg);
  background:
    linear-gradient(145deg, rgba(245, 124, 0, 0.07) 0%, rgba(245, 124, 0, 0.02) 45%, #ffffff 100%),
    #ffffff;
  border: 1px solid rgba(245, 124, 0, 0.18);
  box-shadow: 0 6px 22px rgba(245, 124, 0, 0.07), 0 1px 2px rgba(17, 12, 6, 0.04);
  overflow: hidden;
}
.lib-intro::before {
  content: '';
  position: absolute;
  inset-inline-start: -60px;
  top: -60px;
  width: 220px;
  height: 220px;
  background: radial-gradient(circle, rgba(245, 124, 0, 0.22), transparent 70%);
  border-radius: 50%;
  filter: blur(4px);
  pointer-events: none;
}
.lib-intro-icon {
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: linear-gradient(135deg, #F57C00, #FF9800);
  color: #ffffff;
  box-shadow: 0 6px 16px rgba(245, 124, 0, 0.32);
  flex-shrink: 0;
}
.lib-intro-text { position: relative; z-index: 1; flex: 1; min-width: 0; }
.lib-title { margin: 0; font-size: 20px; font-weight: 800; color: var(--text); }
.lib-sub { margin: 4px 0 0; font-size: 13px; color: var(--text-muted); line-height: 1.55; }

.lib-refresh {
  position: relative;
  z-index: 1;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid rgba(245, 124, 0, 0.32);
  color: var(--primary-deep);
  font-family: inherit;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.18s var(--transition);
  flex-shrink: 0;
}
.lib-refresh:hover:not(:disabled) {
  background: linear-gradient(135deg, #F57C00, #FF9800);
  color: #ffffff;
  border-color: transparent;
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(245, 124, 0, 0.28);
}
.lib-refresh:disabled { opacity: 0.5; cursor: default; }
.spinning { animation: spin 0.9s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ===== Search ===== */
.lib-search {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: #ffffff;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  transition: border-color 0.15s, box-shadow 0.15s;
}
.lib-search:focus-within {
  border-color: rgba(245, 124, 0, 0.4);
  box-shadow: 0 0 0 3px rgba(245, 124, 0, 0.12);
}
.lib-search svg { color: var(--text-muted); flex-shrink: 0; }
.lib-search-input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  font-family: inherit;
  font-size: 13px;
  color: var(--text);
  background: transparent;
}
.lib-search-input::-webkit-search-cancel-button { display: none; }
.lib-search-clear {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--bg);
  color: var(--text-muted);
  border: none;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.lib-search-clear:hover { background: var(--primary-light); color: var(--primary-deep); }

/* ===== Summary chips ===== */
.lib-summary-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 10px;
}
.lib-chip {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: 12px 14px;
  border-radius: var(--radius-md);
  background: #ffffff;
  border: 1px solid var(--border-subtle);
  box-shadow: var(--shadow-sm);
  transition: transform 0.18s, box-shadow 0.18s;
  min-width: 0;
}
.lib-chip:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
.lib-chip-value { font-size: 22px; font-weight: 800; color: var(--text); line-height: 1; }
.lib-chip-label {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-muted);
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ===== Sections ===== */
.lib-section {
  background: #ffffff;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  padding: 0;
  box-shadow: var(--shadow-sm);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: box-shadow 0.18s var(--transition);
}
.lib-section.is-collapsed { box-shadow: none; }

.lib-section-head {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  padding: 16px 18px;
}

/* Clickable section header: button reset + focus + hover */
.lib-section-head-btn {
  width: 100%;
  background: transparent;
  border: none;
  font-family: inherit;
  color: inherit;
  text-align: inherit;
  cursor: pointer;
  transition: background 0.15s;
}
.lib-section-head-btn:hover { background: rgba(245, 124, 0, 0.03); }
.lib-section-head-btn:focus-visible {
  outline: none;
  box-shadow: inset 0 0 0 2px rgba(245, 124, 0, 0.32);
}
.lib-section-chevron {
  flex-shrink: 0;
  color: var(--text-muted);
  transition: transform 0.22s var(--transition), color 0.15s;
}
.lib-section-chevron.is-closed { transform: rotate(-90deg); color: var(--primary-deep); }
.lib-section-head-btn:hover .lib-section-chevron { color: var(--primary-deep); }

/* Section body — wrapper that holds content under the collapsible head */
.lib-section-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 0 18px 18px;
}

/* Toolbar ("collapse all / expand all") */
.lib-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-top: -8px;
}
.lib-toolbar-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: 999px;
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-muted);
  font-family: inherit;
  font-size: 11.5px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s var(--transition);
}
.lib-toolbar-btn:hover {
  background: var(--primary-light);
  color: var(--primary-deep);
  border-color: rgba(245, 124, 0, 0.22);
}
.lib-toolbar-btn svg {
  transition: transform 0.22s var(--transition);
}
.lib-toolbar-btn svg.is-rotated { transform: rotate(180deg); }
.lib-section-icon {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  flex-shrink: 0;
}
.lib-icon--prod   { background: rgba(99, 102, 241, 0.12); color: #4f46e5; }
.lib-icon--comm   { background: rgba(245, 124, 0, 0.12); color: var(--primary-deep); }
.lib-icon--myfile { background: rgba(167, 139, 250, 0.14); color: #7c3aed; }
.lib-icon--rates  { background: rgba(34, 211, 238, 0.14); color: #0891b2; }
.lib-icon--agents { background: rgba(232, 102, 10, 0.14); color: #C85A00; }

.lib-section-titles { display: flex; flex-direction: column; gap: 2px; flex: 1; min-width: 0; }
.lib-section-title { margin: 0; font-size: 15px; font-weight: 800; color: var(--text); }
.lib-section-desc {
  font-size: 12px;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.lib-section-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--primary-light);
  color: var(--primary-deep);
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
  white-space: nowrap;
}

/* ===== Lists ===== */
.lib-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.lib-item {
  position: relative;
  display: flex;
  align-items: stretch;
  gap: 12px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: var(--bg);
  border: 1px solid transparent;
  transition: background 0.15s, border-color 0.15s;
  min-width: 0;
}
.lib-item:hover { background: #ffffff; border-color: var(--border-subtle); }
.lib-item.is-active {
  background: rgba(245, 124, 0, 0.06);
  border-color: rgba(245, 124, 0, 0.2);
}
.lib-item-mark {
  width: 3px;
  border-radius: 3px;
  background: var(--border);
  flex-shrink: 0;
}
.lib-item.is-active .lib-item-mark { background: linear-gradient(180deg, #F57C00, #FF9800); }

.lib-item-main { display: flex; flex-direction: column; gap: 4px; flex: 1; min-width: 0; }
.lib-item-top { display: flex; align-items: center; gap: 8px; min-width: 0; }
.lib-item-title {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
  flex: 1;
}

.lib-pill {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.3px;
  flex-shrink: 0;
}
.lib-pill--active {
  background: linear-gradient(135deg, #F57C00, #FF9800);
  color: #ffffff;
  box-shadow: 0 2px 6px rgba(245, 124, 0, 0.3);
}
.lib-pill--historic { background: var(--bg-surface); color: var(--text-muted); border: 1px solid var(--border-subtle); }

.lib-item-meta { font-size: 11.5px; color: var(--text-muted); line-height: 1.4; }
.lib-item-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 2px;
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 600;
}
.lib-metric-label { color: var(--text-muted); font-weight: 500; margin-inline-end: 3px; }

/* Show more/less button */
.lib-show-more {
  align-self: center;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  margin-top: 4px;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid var(--border-subtle);
  color: var(--primary-deep);
  font-family: inherit;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.18s var(--transition);
}
.lib-show-more:hover {
  background: var(--primary-light);
  border-color: rgba(245, 124, 0, 0.32);
  transform: translateY(-1px);
}
.lib-show-more--collapse { color: var(--text-muted); }

/* Grouped list (commission by company) */
.lib-list--grouped { gap: 8px; }
.lib-group {
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 0;
  overflow: hidden;
  list-style: none;
}
.lib-group-head {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: transparent;
  border: none;
  cursor: pointer;
  font-family: inherit;
  color: inherit;
  text-align: inherit;
  transition: background 0.15s;
}
.lib-group-head:hover { background: #ffffff; }
.lib-group-head:focus-visible {
  outline: none;
  box-shadow: inset 0 0 0 2px rgba(245, 124, 0, 0.3);
}
.lib-group-chevron {
  color: var(--text-muted);
  flex-shrink: 0;
  transition: transform 0.2s var(--transition);
}
/* In RTL, a closed-right chevron points to the start; rotate down when open */
.lib-group-chevron.is-open { transform: rotate(90deg); color: var(--primary-deep); }

.lib-group-name {
  font-size: 13.5px;
  font-weight: 800;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
  flex: 1;
}
.lib-group-count {
  font-size: 11.5px;
  color: var(--text-muted);
  font-weight: 600;
  flex-shrink: 0;
  white-space: nowrap;
}
.lib-group-items {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 2px 10px 10px;
}
.lib-subitem {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  padding: 6px 10px;
  background: #ffffff;
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  transition: border-color 0.15s;
  min-width: 0;
}
.lib-subitem:hover { border-color: var(--border-subtle); }
.lib-subitem-title {
  font-size: 12.5px;
  color: var(--text);
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}
.lib-subitem-meta { font-size: 11px; color: var(--text-muted); flex-shrink: 0; white-space: nowrap; }

/* Group collapse transition */
.lib-collapse-enter-active,
.lib-collapse-leave-active {
  transition: opacity 0.18s ease, max-height 0.22s ease;
  overflow: hidden;
}
.lib-collapse-enter-from,
.lib-collapse-leave-to { opacity: 0; max-height: 0; }
.lib-collapse-enter-to,
.lib-collapse-leave-from { opacity: 1; max-height: 800px; }

/* Stats row */
/* Per-category breakdown (myfile: financial / insurance) */
.lib-cat-strip {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 10px;
  padding: 10px 12px;
  background: rgba(245, 124, 0, 0.04);
  border: 1px solid rgba(245, 124, 0, 0.14);
  border-radius: var(--radius-md);
}
.lib-cat-chip {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  padding: 5px 12px;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid var(--border-subtle);
  font-size: 12px;
  font-weight: 600;
}
.lib-cat-chip-label { color: var(--text-secondary); }
.lib-cat-chip-value { font-size: 14px; font-weight: 800; color: var(--text); }
.lib-cat-chip--financial { border-color: rgba(99, 102, 241, 0.3); }
.lib-cat-chip--financial .lib-cat-chip-value { color: #4f46e5; }
.lib-cat-chip--insurance { border-color: rgba(46, 132, 74, 0.3); }
.lib-cat-chip--insurance .lib-cat-chip-value { color: var(--accent-emerald); }
.lib-cat-note {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
  margin-inline-start: auto;
}

.lib-stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
}
.lib-stat {
  padding: 12px 14px;
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}
.lib-stat-value { font-size: 18px; font-weight: 800; color: var(--text); line-height: 1.1; }
.lib-stat-label {
  font-size: 11.5px;
  color: var(--text-muted);
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Empty states */
.lib-empty {
  padding: 16px 12px;
  text-align: center;
  font-size: 12.5px;
  color: var(--text-muted);
  background: var(--bg);
  border-radius: var(--radius-md);
  border: 1px dashed var(--border);
}
.lib-empty-all {
  text-align: center;
  padding: 40px 20px;
  color: var(--text-muted);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  background: #ffffff;
  border-radius: var(--radius-lg);
  border: 1px dashed var(--border);
}
.lib-empty-all svg { color: var(--primary); opacity: 0.6; }
.lib-empty-all p { margin: 0; font-size: 13px; max-width: 400px; line-height: 1.55; }

/* Error */
.lib-error {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  font-size: 12.5px;
  color: #8A1111;
  background: rgba(234, 0, 30, 0.06);
  border: 1px solid rgba(234, 0, 30, 0.2);
  border-radius: var(--radius-md);
}
.lib-error-text { flex: 1; }
.lib-error-retry {
  padding: 5px 12px;
  border-radius: 999px;
  background: #ffffff;
  border: 1px solid rgba(234, 0, 30, 0.35);
  color: #8A1111;
  font-family: inherit;
  font-size: 11.5px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  flex-shrink: 0;
}
.lib-error-retry:hover { background: #8A1111; color: #ffffff; }

/* ===== Skeleton ===== */
.lib-skeleton { display: flex; flex-direction: column; gap: 20px; }
.sk-intro {
  height: 86px;
  border-radius: var(--radius-lg);
  background: linear-gradient(90deg, rgba(245, 124, 0, 0.08), rgba(245, 124, 0, 0.03), rgba(245, 124, 0, 0.08));
  background-size: 200% 100%;
  animation: shimmer 1.6s linear infinite;
}
.sk-chips {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 10px;
}
.sk-chip {
  height: 58px;
  border-radius: var(--radius-md);
  background: linear-gradient(90deg, rgba(0, 0, 0, 0.04), rgba(0, 0, 0, 0.08), rgba(0, 0, 0, 0.04));
  background-size: 200% 100%;
  animation: shimmer 1.6s linear infinite;
}
.sk-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 18px;
  background: #ffffff;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
}
.sk-row {
  height: 44px;
  border-radius: var(--radius-md);
  background: linear-gradient(90deg, rgba(0, 0, 0, 0.035), rgba(0, 0, 0, 0.07), rgba(0, 0, 0, 0.035));
  background-size: 200% 100%;
  animation: shimmer 1.6s linear infinite;
}
.sk-row-lg { height: 54px; margin-bottom: 4px; }
@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ===== Responsive ===== */
@media (max-width: 860px) {
  .ai-library { padding: 18px 16px 32px; gap: 16px; }
  .lib-intro {
    flex-wrap: wrap;
    padding: 16px 18px;
  }
  .lib-refresh {
    order: 3;
    margin-inline-start: auto;
  }
  .lib-section-desc { white-space: normal; }
  .lib-stats-row { grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); }
}

@media (max-width: 520px) {
  .ai-library { padding: 14px 12px 28px; gap: 14px; }
  .lib-intro-icon { width: 36px; height: 36px; border-radius: 10px; }
  .lib-title { font-size: 17px; }
  .lib-sub { font-size: 12px; }
  .lib-summary-strip {
    display: flex;
    gap: 8px;
    overflow-x: auto;
    padding-bottom: 4px;
    margin-inline: -12px;
    padding-inline: 12px;
    scrollbar-width: none;
  }
  .lib-summary-strip::-webkit-scrollbar { display: none; }
  .lib-chip {
    flex-shrink: 0;
    min-width: 150px;
  }
  .lib-section-head { padding: 14px; }
  .lib-section-body { padding: 0 14px 14px; }
  .lib-section-title { font-size: 14px; }
  .lib-item {
    flex-direction: row;
    padding: 10px;
  }
  .lib-item-metrics {
    gap: 8px;
    font-size: 11.5px;
  }
  .lib-stats-row { grid-template-columns: 1fr 1fr; }
  .lib-stat-value { font-size: 16px; }
  .lib-search { padding: 8px 12px; }
  .lib-search-input { font-size: 14px; /* prevents iOS zoom */ }
}

@media (prefers-reduced-motion: reduce) {
  .spinning,
  .sk-intro, .sk-chip, .sk-row,
  .float-circle, .wave-1, .wave-2, .wave-3, .shimmer::after {
    animation: none;
  }
  .lib-chip:hover { transform: none; }
  .lib-show-more:hover { transform: none; }
  .lib-collapse-enter-active,
  .lib-collapse-leave-active { transition: none; }
}

/* ─── Agent folders (super-only "תיקיות סוכנים" section) ─── */
.lib-agent-avatar {
  flex-shrink: 0;
  width: 32px; height: 32px; border-radius: 50%;
  background: linear-gradient(135deg, #FFD180 0%, #E8660A 100%);
  color: #fff;
  display: inline-flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 12px;
  letter-spacing: -0.3px;
  box-shadow: 0 4px 8px rgba(232, 102, 10, 0.32);
}
.lib-agent-info {
  flex: 1; min-width: 0;
  display: flex; flex-direction: column; gap: 2px; align-items: flex-start;
}
.lib-agent-name {
  font-size: 13.5px; font-weight: 700; color: var(--text);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%;
}
.lib-agent-email {
  font-size: 11px; color: var(--text-muted);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%;
}
.lib-agent-tags {
  display: inline-flex; gap: 5px; align-items: center; flex-wrap: wrap;
  flex-shrink: 0;
}
.lib-agent-tag {
  font-size: 10.5px; font-weight: 700;
  padding: 3px 9px; border-radius: 999px;
  white-space: nowrap;
}
.tag-prod    { background: rgba(99, 102, 241, 0.10); color: #4f46e5; }
.tag-comm    { background: rgba(245, 124, 0, 0.12); color: var(--primary-deep); }
.tag-myfile  { background: rgba(167, 139, 250, 0.12); color: #7c3aed; }
.tag-rates   { background: rgba(34, 211, 238, 0.12); color: #0891b2; }
.tag-empty   { background: rgba(45, 37, 34, 0.06); color: var(--text-muted); font-weight: 600; }

.lib-agent-body {
  padding: 12px 14px 14px;
  background: rgba(245, 240, 235, 0.4);
  border-radius: 0 0 10px 10px;
  display: flex; flex-direction: column; gap: 14px;
}
.lib-agent-block {
  display: flex; flex-direction: column; gap: 6px;
}
.lib-agent-block-h {
  font-size: 11px; font-weight: 700; letter-spacing: 0.6px;
  text-transform: uppercase; color: var(--text-muted);
  padding-right: 4px;
}
</style>
