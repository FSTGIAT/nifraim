<template>
  <div class="rate-shelf">
    <!-- ── Hero (reference's left text + CTA) ── -->
    <header class="shelf-hero">
      <div class="hero-copy">
        <span class="hero-eyebrow">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="4" rx="1"/><rect x="3" y="10" width="18" height="4" rx="1"/><rect x="3" y="16" width="18" height="4" rx="1"/></svg>
          עמלות נפרעים
        </span>
        <h2 class="hero-title">מדף ההסכמים שלך</h2>
        <p v-if="!rates.length" class="hero-sub">העלו הסכם עמלות והשיעורים יופיעו כאן על המדף.</p>
        <div class="hero-actions">
          <button class="btn-accent" @click="triggerUpload" :disabled="queueBusy">
            <svg v-if="!queueBusy" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            <span v-if="queueBusy" class="btn-spin" aria-hidden="true"></span>
            <template v-if="queueBusy">מעבד הסכמים <span class="ltr-number">{{ queueDone }}/{{ docQueue.length }}</span></template>
            <template v-else>העלאת הסכמי עמלות</template>
          </button>
          <!-- Opens the agreement bookcase. It lives behind a button rather
               than on the page: at 12 insurers the shelf was taller than the
               rates it exists to explain. -->
          <button v-if="agreementCompanies.length" class="btn-icon" @click="shelfOpen = true"
                  title="מסמכי ההסכמים" aria-label="מסמכי ההסכמים">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 4v16"/><path d="M8 7v13"/><path d="M12 5v15"/><path d="m16.5 6.5 4 13.5"/></svg>
            <span class="btn-icon-count ltr-number">{{ agreementDocTotal }}</span>
          </button>
          <button v-if="rates.length > 0 && !addingNew" class="btn-ghost" @click="startNew">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            הוסף שורה ידנית
          </button>
          <button v-if="rates.length === 0" class="btn-ghost" @click="seedRates" :disabled="seeding">{{ seeding ? 'טוען…' : 'טען ברירת מחדל' }}</button>
          <input ref="fileInput" type="file" accept="application/pdf" multiple class="hidden-file" @change="onAgreementFile" />
        </div>
        <!-- One row per agreement in the batch. Each takes 1–4 minutes to read,
             so the row shows a real elapsed clock instead of a bar that pretends
             to know how far along the model is. -->
        <Transition name="fade">
          <div v-if="docQueue.length" class="up-queue">
            <ul class="uq-list" aria-live="polite">
              <li v-for="it in docQueue" :key="it.key" class="uq-row" :class="'uq-row--' + it.status">
                <span class="uq-icon" aria-hidden="true">
                  <span v-if="it.status === 'extracting'" class="uq-spin"></span>
                  <svg v-else-if="it.status === 'done'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                  <svg v-else-if="it.status === 'error'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                  <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                </span>
                <span class="uq-name" :title="it.name">{{ it.name.replace(/\.pdf$/i, '') }}</span>
                <span class="uq-meta">{{ queueMeta(it) }}</span>
              </li>
            </ul>
            <p v-if="queueBusy" class="uq-note">קריאת הסכם לוקחת עד כ-2 דקות. אפשר לעבור לטאב אחר בינתיים.</p>
            <button v-else-if="docQueue.length > 1" class="uq-clear" @click="chat.clearDocQueue()">נקה רשימה</button>
          </div>
        </Transition>
        <Transition name="fade"><p v-if="uploadError" class="hero-upload-error">שגיאה בהעלאה: {{ uploadError }}</p></Transition>

        <!-- What the last upload actually did. A PDF that yields no rates used
             to leave this whole area unchanged, so a correct "this agreement
             holds no rate table" was indistinguishable from a broken upload. -->
        <Transition name="fade">
          <div v-if="lastUpload" class="up-result" :class="'up-result--' + lastUpload.tone">
            <div class="up-result-head">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                   stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <template v-if="lastUpload.tone === 'ok'">
                  <path d="M20 6L9 17l-5-5" />
                </template>
                <template v-else>
                  <circle cx="12" cy="12" r="9" /><line x1="12" y1="8" x2="12" y2="13" />
                  <line x1="12" y1="16.5" x2="12.01" y2="16.5" />
                </template>
              </svg>
              <span>{{ lastUpload.headline }}</span>
              <button class="up-result-x" @click="lastUpload = null" aria-label="סגור">&times;</button>
            </div>
            <p v-if="lastUpload.detail" class="up-result-detail">{{ lastUpload.detail }}</p>
            <ul v-if="lastUpload.dropped.length" class="up-dropped">
              <li v-for="(d, i) in lastUpload.dropped.slice(0, 8)" :key="i">
                <span class="up-dropped-name">{{ d.product || d.company || '—' }}</span>
                <span class="up-dropped-why">{{ dropReasonLabel(d.reason) }}</span>
              </li>
              <li v-if="lastUpload.dropped.length > 8" class="up-dropped-more">
                ועוד {{ lastUpload.dropped.length - 8 }}…
              </li>
            </ul>
          </div>
        </Transition>
      </div>
      <TabHeroLoop scene="commission-shelf" class="shelf-art" />
    </header>

    <!-- ── Coverage: does the shelf actually price the portfolio? ── -->
    <section v-if="coverage?.has_production && coverage.total_records" class="cov" :class="{ 'cov--thin': coveragePct < 50 }">
      <div class="cov-head">
        <span class="cov-icon" aria-hidden="true">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
        </span>
        <div class="cov-headline">
          <strong><span class="ltr-number">{{ coverage.covered_records }}</span> מתוך <span class="ltr-number">{{ coverage.total_records }}</span> רשומות מתומחרות לפי ההסכמים</strong>
          <span class="cov-sub">
            עמלה צפויה <span class="ltr-number">{{ fmtMoney(coverage.expected_total) }}</span>
            <template v-if="coverageApprox"> · <span class="ltr-number">{{ coverageApprox }}</span> רשומות מוערכות משיעור כללי של החברה</template>
            <template v-if="coverageSeeded"> · <span class="ltr-number">{{ coverageSeeded }}</span> לפי שיעורי ברירת מחדל ולא לפי הסכם שהעליתם</template>
          </span>
        </div>
        <span class="cov-pct ltr-number">{{ coveragePct }}%</span>
      </div>
      <div class="cov-bar"><div class="cov-fill" :style="{ width: coveragePct + '%' }"></div></div>

      <template v-if="coverageGaps.length">
        <button type="button" class="cov-toggle" :aria-expanded="coverageOpen" @click="coverageOpen = !coverageOpen">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" :style="{ transform: coverageOpen ? 'rotate(90deg)' : 'none' }"><polyline points="15 18 9 12 15 6"/></svg>
          <span><span class="ltr-number">{{ coverageGaps.length }}</span> חברות ללא תמחור מלא</span>
        </button>
        <Transition name="fade">
          <ul v-if="coverageOpen" class="cov-gaps">
            <li v-for="g in coverageGaps" :key="g.company" class="cov-gap">
              <span class="cov-gap-co">{{ g.company }}</span>
              <span class="cov-gap-n"><span class="ltr-number">{{ g.records }}</span> רשומות</span>
              <span class="cov-gap-why">{{ g.reason_label }}</span>
            </li>
          </ul>
        </Transition>
      </template>
    </section>

    <div v-if="rates.length" class="shelf-toolbar">
      <label class="rate-search">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input v-model="search" type="search" placeholder="חיפוש חברה או מוצר…" />
      </label>
      <nav v-if="availableYears.length > 1" class="year-chips" aria-label="סינון לפי שנה">
        <button v-for="chip in availableYears" :key="chip.key" type="button" class="year-chip" :class="{ 'year-chip--active': yearFilter === chip.key }" :data-tone="chip.tone" @click="yearFilter = chip.key">
          <span>{{ chip.label }}</span><span class="year-chip-count ltr-number">{{ chip.count }}</span>
        </button>
      </nav>
    </div>

    <!-- ── First run (no agreements yet): under the hero, not inside it. A
         picture and one classic serif welcome line, and the
         whole AI story in three word-long steps. The hero above keeps the
         actions, so this adds no second primary button. ── -->
    <section v-if="isWelcome" class="shelf-welcome">
      <!-- Realistic photo as the section's own background (left, RTL end),
           fading into the white under the text — no frame around it. -->
      <div v-if="welcomeArt.still" class="sw-photo" aria-hidden="true">
        <video v-if="welcomeArt.video && !reducedMotion" :src="welcomeArt.video" :poster="welcomeArt.still"
               autoplay muted loop playsinline preload="auto" disablepictureinpicture></video>
        <img v-else :src="welcomeArt.still" alt="" />
      </div>
      <div class="sw-copy">
          <!-- First run: one classic serif welcome line, small Heebo copy, and
               the whole AI story in three words-long steps. -->
            <h2 class="sw-display">ברוכים הבאים<br><span class="sw-display-accent">למדף ההסכמים</span></h2>
            <!-- The AI story as a slider: one step at a time, story-style bars.
               Hover pauses; a bar jumps to its step. Reduced motion shows all
               three lines, still. -->
          <div v-if="!reducedMotion" class="sw-slider" aria-live="polite"
               @mouseenter="swPaused = true" @mouseleave="swPaused = false">
            <div class="sw-slide-track">
              <Transition name="sw-slide" mode="out-in">
                <p :key="swStep" class="sw-slide">
                  <span class="sw-slide-num ltr-number">{{ String(swStep + 1).padStart(2, '0') }}</span>{{ SW_STEPS[swStep] }}
                </p>
              </Transition>
            </div>
            <div class="sw-bars">
              <button v-for="(t, n) in SW_STEPS" :key="n" type="button" class="sw-bar"
                      :class="{ 'sw-bar--done': n < swStep, 'sw-bar--on': n === swStep, 'sw-bar--paused': swPaused }"
                      :aria-label="t" :aria-current="n === swStep ? 'step' : undefined" @click="swGo(n)">
                <span :key="n === swStep ? swCycle : 'x'" class="sw-bar-fill"></span>
              </button>
            </div>
          </div>
          <ol v-else class="sw-steps-static">
            <li v-for="(t, n) in SW_STEPS" :key="n"><span class="sw-slide-num ltr-number">{{ String(n + 1).padStart(2, '0') }}</span>{{ t }}</li>
          </ol>
      </div>
    </section>
    <div v-if="loading" class="loading"><div class="spinner"></div></div>

    <!-- ── The shelf: a row of tall picture panels (your reference).
         Thin panels stand vertical like book spines; hover/click a panel to
         widen it and reveal its big picture. ── -->
    <div v-if="!loading && rates.length > 0 && visibleCategories.length" class="shelf-rack" :class="{ 'shelf-rack--open': !!activeShelf }">
      <button
        v-for="cat in visibleCategories"
        :key="cat.key"
        type="button"
        class="shelf-panel"
        :class="[`tint-${cat.key}`, { 'shelf-panel--active': activeShelf === cat.key }]"
        :aria-expanded="activeShelf === cat.key"
        @click="toggleShelf(cat.key)"
      >
        <span class="shelf-media" :class="{ 'shelf-media--fallback': !artFor(cat.key) }" :style="artFor(cat.key) ? { backgroundImage: `url(${artFor(cat.key)})` } : null"></span>
        <span class="shelf-veil"></span>
        <span class="shelf-caption">
          <span class="shelf-badge" v-html="cat.icon"></span>
          <span class="shelf-name">{{ cat.label }}</span>
          <span class="shelf-meta"><span class="ltr-number">{{ cat.items.length }}</span> שיעורים · <span class="ltr-number">{{ cat.companies.length }}</span> חברות</span>
          <span class="shelf-hint">
            <svg v-if="activeShelf !== cat.key" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14"/></svg>
            <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/></svg>
            {{ activeShelf === cat.key ? 'לחצו לסגירה' : 'לחצו לפתיחה' }}
          </span>
        </span>
      </button>
    </div>

    <!-- ── The agreement shelf: every signed PDF standing on a board ────
         The previous version was a grid of equal cards, so a company with no
         agreement got the same footprint as one with four — live that was 8
         empty boxes out of 12 tiles. On a shelf an absent agreement is an
         empty SLOT: smaller than a binder, and something to act on. -->
    <DataModal :open="shelfOpen" title="מסמכי ההסכמים" size="xl"
               :subtitle="`${agreementDocTotal} מסמכים · ${agreementCompanies.length} חברות`"
               @close="shelfOpen = false">
      <div class="agshelf">
      <div class="agshelf-board">
        <div class="agshelf-row">
          <template v-for="co in agreementCompanies" :key="co.stem">
            <!-- One binder per COMPANY. One per document repeated the same
                 name four times across the shelf and truncated all of them. -->
            <button v-if="co.documents.length" class="binder"
                    :class="{ 'binder--open': openBinder === co.stem }"
                    :title="co.company" @click="clickBinder(co)">
              <span class="binder-art" :style="{ backgroundImage: `url(${binderArt(co.company)})` }"></span>
              <span v-if="co.documents.length > 1" class="binder-count ltr-number">
                {{ co.documents.length }}
              </span>
              <span v-if="co.documents.some(d => !d.rates)" class="binder-flag"
                    title="מסמך שלא חולצו ממנו שיעורים">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="12" y1="8" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/><circle cx="12" cy="12" r="9"/></svg>
              </span>
              <span class="binder-face">
                <span class="binder-rates ltr-number">{{ co.rates_total }}</span>
                <span class="binder-open">שיעורים</span>
              </span>
              <span class="binder-label">{{ co.company }}</span>
            </button>

            <!-- An insurer with rates but nothing signed behind them. -->
            <button v-else class="slot" @click="triggerUpload" :disabled="queueBusy"
                    :title="`העלה הסכם עבור ${co.company}`">
              <span class="slot-plus">
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              </span>
              <span class="slot-note">העלה הסכם</span>
              <span class="binder-label">{{ co.company }}</span>
            </button>
          </template>
        </div>
        <div class="agshelf-edge" aria-hidden="true"></div>
      </div>

      <!-- The picked binder's documents. Opening in place under the board
           keeps the shelf as the index and this as the contents. -->
      <div v-if="openCompanyDocs" class="agpick">
        <div class="agpick-head">
          <strong>{{ openCompanyDocs.company }}</strong>
          <span class="agpick-sub">
            <span class="ltr-number">{{ openCompanyDocs.documents.length }}</span> מסמכים ·
            <span class="ltr-number">{{ openCompanyDocs.rates_total }}</span> שיעורים
          </span>
          <button class="agpick-x" @click="openBinder = null" aria-label="סגור">&times;</button>
        </div>
        <ul class="agpick-list">
          <li v-for="d in openCompanyDocs.documents" :key="d.id">
            <button class="agpick-open" :disabled="!d.has_file || pdfLoading === d.id"
                    :title="d.has_file ? 'פתח את ה-PDF' : 'הקובץ אינו זמין בשרת'"
                    @click="openPdf(d)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              <span class="agpick-name">{{ d.filename }}</span>
            </button>
            <span class="agpick-rates ltr-number" :class="{ 'agpick-rates--zero': !d.rates }">
              {{ d.rates }} שיעורים
            </span>
            <p v-if="!d.rates" class="agpick-why">{{ docReason(d) }}</p>
          </li>
        </ul>
      </div>

      <!-- Why a binder on the shelf carries no rates. Listed under the board
           so the shelf itself stays quiet. -->
      <ul v-if="zeroDocs.length" class="agshelf-notes">
        <li v-for="d in zeroDocs" :key="d.id">
          <strong>{{ d.company }}</strong>
          <span class="agnote-file">{{ d.filename }}</span>
          <span class="agnote-why">{{ docReason(d) }}</span>
        </li>
      </ul>
      <p v-if="pdfError" class="agshelf-err">{{ pdfError }}</p>
      </div>
    </DataModal>

    <!-- ── The opened shelf's agreements (companies + rates) ── -->
    <section v-if="!loading && activeCategory" class="shelf-open" :class="`tint-${activeCategory.key}`">
      <div class="shelf-open-head">
        <span class="soh-dot"></span>
        <h3 class="soh-title">{{ activeCategory.label }}</h3>
        <span class="soh-meta"><span class="ltr-number">{{ activeCategory.items.length }}</span> שיעורים · <span class="ltr-number">{{ activeCategory.companies.length }}</span> חברות<template v-if="activeCategory.range"> · <span class="ltr-number">{{ activeCategory.range }}</span></template></span>
      </div>
      <div class="shelf-open-body">
        <table class="rate-table">
          <colgroup><col class="col-product"/><col class="col-rate"/><col class="col-freq"/><col class="col-paidto"/><col class="col-email"/><col class="col-actions"/></colgroup>
          <thead><tr><th>מוצר</th><th class="num">אחוז</th><th>תדירות</th><th>נפרעים</th><th>אימייל</th><th class="actions-col"></th></tr></thead>
          <tbody v-for="(group, gi) in activeCategory.companies" :key="group.company" class="company-binder" :style="{ '--company-color': companyColor(group.company), animationDelay: (gi * 35) + 'ms' }">
            <tr class="company-row">
              <td colspan="6">
                <div class="company-row-inner">
                  <span class="company-tab" aria-hidden="true"></span>
                  <span class="company-row-name">{{ group.company }}</span>
                  <span class="company-row-count"><span class="ltr-number">{{ group.items.length }}</span> {{ group.items.length === 1 ? 'שיעור' : 'שיעורים' }}</span>
                  <span v-if="group.range" class="company-row-range ltr-number">{{ group.range }}</span>
                </div>
              </td>
            </tr>
            <tr v-for="rate in group.items" :key="rate.id">
              <template v-if="editingId === rate.id">
                <td><div class="edit-stack"><input v-model="editForm.company_name" class="edit-input" placeholder="חברה" /><input v-model="editForm.product" class="edit-input" placeholder="כל המוצרים" /><select v-model="editForm.rate_kind" class="edit-input" title="סוג השיעור — עמלת ספר ושיעור תגמול מסתכמים יחד"><option value="single">שיעור יחיד</option><option value="book">עמלת ספר</option><option value="reward">שיעור תגמול</option><option value="total">סה"כ</option></select></div></td>
                <td class="num"><input v-model.number="editForm.rate" type="number" step="0.01" class="edit-input num-input" dir="ltr" placeholder="%" /></td>
                <td><select v-model="editForm.payment_frequency" class="edit-input"><option value="חודשי">חודשי</option><option value="רבעוני">רבעוני</option><option value="שנתי">שנתי</option></select></td>
                <td><select v-model="editForm.paid_to" class="edit-input"><option value="עיתים">עיתים</option><option value="סוכן">סוכן</option><option value="ידנים">ידנים</option></select></td>
                <td><input v-model="editForm.company_email" class="edit-input email-input" dir="ltr" placeholder="email@company.co.il" /></td>
                <td class="actions">
                  <button class="icon-btn icon-btn--save" @click="saveEdit(rate.id)" title="שמור"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg></button>
                  <button class="icon-btn icon-btn--cancel" @click="editingId = null" title="ביטול"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>
                </td>
              </template>
              <template v-else>
                <td class="product-cell" :title="rate.product || 'כל המוצרים'"><span class="product-line"><span v-if="rate.product">{{ rate.product }}</span><span v-else class="product-cell--default">כל המוצרים</span><span v-if="rateKindLabel(rate)" class="kind-pill" :class="'kind-pill--' + rate.rate_kind" :title="rate.rate_kind === 'total' ? 'השיעור הסופי כפי שמופיע בהסכם' : 'רכיב אחד מתוך השיעור — עמלת ספר ושיעור תגמול מסתכמים יחד'">{{ rateKindLabel(rate) }}</span><span v-if="rate.rate_scope" class="scope-pill">{{ rate.rate_scope }}</span><span v-if="rateYearLabel(rate)" class="year-pill ltr-number" :class="rateYearClass(rate)" :title="rateYearTitle(rate)">{{ rateYearLabel(rate) }}</span></span></td>
                <td class="num"><span class="rate-pill ltr-number">{{ (rate.rate * 100).toFixed(2) }}%</span></td>
                <td class="muted-cell">{{ rate.payment_frequency || '—' }}</td>
                <td class="muted-cell">{{ rate.paid_to || '—' }}</td>
                <td class="email-cell"><span class="ltr-number">{{ rate.company_email || '—' }}</span></td>
                <td class="actions">
                  <button class="icon-btn icon-btn--edit" @click="startEdit(rate)" title="ערוך"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></button>
                  <button class="icon-btn icon-btn--del" @click="deleteRate(rate.id)" title="מחק"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/></svg></button>
                </td>
              </template>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <p v-if="rates.length > 0 && search && !visibleCategoryCount" class="empty empty--filter">אין תוצאות עבור "<span class="ltr-number">{{ search }}</span>"</p>

    <section v-if="addingNew" class="add-card">
      <div class="add-card-head">
        <span class="add-card-icon"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg></span>
        <span class="add-card-title">שורה חדשה</span><span class="add-card-hint">הקטגוריה תיקבע אוטומטית לפי שם המוצר</span>
      </div>
      <table class="rate-table"><tbody><tr>
        <td><div class="edit-stack"><input v-model="newForm.company_name" class="edit-input" placeholder="שם חברה" /><input v-model="newForm.product" class="edit-input" placeholder="שם מוצר (אופציונלי)" /></div></td>
        <td class="num"><input v-model.number="newForm.rate" type="number" step="0.01" class="edit-input num-input" dir="ltr" placeholder="%" /></td>
        <td><select v-model="newForm.payment_frequency" class="edit-input"><option value="חודשי">חודשי</option><option value="רבעוני">רבעוני</option><option value="שנתי">שנתי</option></select></td>
        <td><select v-model="newForm.paid_to" class="edit-input"><option value="עיתים">עיתים</option><option value="סוכן">סוכן</option><option value="ידנים">ידנים</option></select></td>
        <td><input v-model="newForm.company_email" class="edit-input email-input" dir="ltr" placeholder="email@company.co.il" /></td>
        <td class="actions">
          <button class="icon-btn icon-btn--save" @click="saveNew" title="שמור"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg></button>
          <button class="icon-btn icon-btn--cancel" @click="cancelNew" title="ביטול"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>
        </td>
      </tr></tbody></table>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onBeforeUnmount, onMounted, reactive, watch } from 'vue'
import { storeToRefs } from 'pinia'
import api from '../../api/client.js'
import { chartColor } from '../../utils/chartPalette.js'
import { useChatStore } from '../../stores/chat.js'
import TabHeroLoop from '../workspace/TabHeroLoop.vue'
import DataModal from '../workspace/DataModal.vue'
import { extractionOutcome, dropReasonLabel } from '../../utils/extractionReport.js'

const emit = defineEmits(['rates-changed'])

const rates = ref([])
const loading = ref(false)
// Welcome section (first run): only once the first fetch has answered "none",
// so a user WITH agreements never sees it flash while the list loads.
const ratesLoaded = ref(false)
const isWelcome = computed(() => ratesLoaded.value && !loading.value && rates.value.length === 0)
// Kling art for the welcome section; optional — glob so a missing file is no crash.
const welcomeAssets = import.meta.glob('../../assets/welcome/shelf-empty.{webp,mp4}', { eager: true, import: 'default' })
const welcomeArt = {
  still: Object.entries(welcomeAssets).find(([k]) => k.endsWith('.webp'))?.[1] || '',
  video: Object.entries(welcomeAssets).find(([k]) => k.endsWith('.mp4'))?.[1] || '',
}
const reducedMotion = typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

// Welcome slider — the three-step AI story, one step at a time.
const SW_STEPS = ['מעלים PDF', 'ה-AI קורא את ההסכם', 'השיעורים על המדף']
const SW_MS = 2800 // keep in sync with .sw-bar--on .sw-bar-fill animation
const swStep = ref(0)
const swCycle = ref(0) // re-keys the active bar so its fill restarts on every step
const swPaused = ref(false)
let swTimer = null
function swGo(n) { swStep.value = n; swCycle.value++; swArm() }
function swArm() {
  clearTimeout(swTimer)
  if (reducedMotion || !isWelcome.value) return
  swTimer = setTimeout(() => { if (swPaused.value) return swArm(); swGo((swStep.value + 1) % SW_STEPS.length) }, SW_MS)
}
watch(isWelcome, (on) => { if (on) swGo(0); else clearTimeout(swTimer) }, { immediate: true })
watch(swPaused, (p) => { if (!p) swArm() })
onBeforeUnmount(() => clearTimeout(swTimer))
const seeding = ref(false)
const search = ref('')
const yearFilter = ref('all')
const editingId = ref(null)
const editForm = reactive({ company_name: '', product: '', rate: 0, rate_kind: 'single', payment_frequency: '', paid_to: '', company_email: '' })
const addingNew = ref(false)
const newForm = reactive({ company_name: '', product: '', rate: 0, rate_kind: 'single', payment_frequency: 'חודשי', paid_to: 'עיתים', company_email: '' })

// Which shelf (category) is open/active.
const activeShelf = ref(null)

const chat = useChatStore()
const { uploadError, docQueue, queueBusy } = storeToRefs(chat)
const queueDone = computed(() => docQueue.value.filter(i => i.status === 'done' || i.status === 'error').length)

// Seconds ticker for the queue's elapsed clocks — runs only while something is
// being read.
const now = ref(Date.now())
let nowTimer = null
watch(queueBusy, (busy) => {
  clearInterval(nowTimer)
  nowTimer = busy ? setInterval(() => { now.value = Date.now() }, 1000) : null
}, { immediate: true })
onBeforeUnmount(() => clearInterval(nowTimer))

function mmss(ms) {
  const sec = Math.max(0, Math.round(ms / 1000))
  return `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, '0')}`
}
function queueMeta(it) {
  if (it.status === 'queued') return 'ממתין בתור'
  if (it.status === 'extracting') return `קורא את ההסכם ${mmss(now.value - it.startedAt)}`
  if (it.status === 'error') return it.error || 'העלאה נכשלה'
  const out = extractionOutcome(it.doc?.structured_data?.extraction, it.doc?.structured_data?.rates || [])
  return out.text.split('\n\n')[0].replace(/\*\*/g, '')
}
const fileInput = ref(null)

const ART = import.meta.glob('../../assets/commission-shelf/*.webp', { eager: true, import: 'default' })
function artFor(key) { return ART[`../../assets/commission-shelf/${key}.webp`] || null }
const heroArt = computed(() => artFor('hero'))

const ICONS = {
  savings: '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/></svg>',
  risk:    '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/></svg>',
  health:  '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 8L9 4l-3 8H2"/></svg>',
  other:   '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>',
}
const CATEGORIES = [
  { key: 'savings', label: 'חיסכון ופנסיה', icon: ICONS.savings, keywords: ['גמל', 'השתלמ', 'פנסיה', 'פיננס', 'השקעה', 'חיסכון', 'צבירה', 'קצבה', 'הון', 'אקסלנס', 'מצנח'] },
  { key: 'risk', label: 'חיים וריסק', icon: ICONS.risk, keywords: ['ריסק', 'מנהלים', 'חיים', 'מטריה', 'אובדן', 'אכ"ע', 'אכע', 'נכות', 'תאונה', 'אקסטרה', 'רצף', 'משכנת', 'מוות'] },
  { key: 'health', label: 'בריאות', icon: ICONS.health, keywords: ['בריאות', 'ניתוח', 'השתל', 'תרופ', 'אמבולטור', 'שב"ן', 'שבן', 'סרטן', 'מרפא', 'מחלות', 'פלוס', 'שירותים'] },
  { key: 'other', label: 'אחר', icon: ICONS.other, keywords: [] },
]

function categorize(rate) {
  const text = (rate.product || '').toLowerCase()
  if (text) for (const cat of CATEGORIES) if (cat.keywords.some(k => text.includes(k))) return cat.key
  const pct = (rate.rate || 0) * 100
  return (pct > 0 && pct <= 1) ? 'savings' : 'other'
}
function matchesSearch(rate, q) {
  if (!q) return true
  const n = q.toLowerCase().trim()
  return (rate.company_name || '').toLowerCase().includes(n) || (rate.product || '').toLowerCase().includes(n)
}
function applyFilters(r) { return matchesSearch(r, search.value) && rateInYear(r, yearFilter.value) }

const companyOrder = computed(() => [...new Set(rates.value.map(r => r.company_name || '—'))].sort((a, b) => _normCompany(a).localeCompare(_normCompany(b), 'he')))
const companyColors = computed(() => { const m = new Map(); companyOrder.value.forEach((n, i) => m.set(n, chartColor(i))); return m })
function companyColor(name) { return companyColors.value.get(name) || 'var(--text-muted)' }

const availableYears = computed(() => {
  const yearSet = new Set(); let undated = 0
  for (const r of rates.value) { const s = rateYearSpan(r); if (!s) { undated++; continue } for (let y = s.from; y <= s.to; y++) yearSet.add(y) }
  const nowYear = new Date().getFullYear()
  const chips = [{ key: 'all', label: 'כל השנים', count: rates.value.length, tone: 'all' },
    ...[...yearSet].sort((a, b) => b - a).map(y => ({ key: String(y), label: String(y), count: rates.value.filter(r => rateInYear(r, String(y))).length, tone: y >= nowYear - 1 ? 'current' : (y >= nowYear - 3 ? 'recent' : 'old') }))]
  if (undated) chips.push({ key: 'undated', label: 'ללא תאריך', count: undated, tone: 'old' })
  return chips
})

function _normCompany(name) { return (name || '').trim().replace(/^ה/, '') }
function rateYearSpan(rate) {
  const yf = rate.effective_from ? new Date(rate.effective_from).getFullYear() : null
  const yt = rate.effective_to ? new Date(rate.effective_to).getFullYear() : null
  if (!yf && !yt) return null
  return { from: yf ?? yt, to: yt ?? yf }
}
function rateInYear(rate, year) {
  if (year === 'all') return true
  const s = rateYearSpan(rate)
  if (year === 'undated') return s === null
  const y = parseInt(year, 10)
  return s ? (s.from <= y && y <= s.to) : false
}
function rateYearLabel(rate) {
  const yf = rate.effective_from ? new Date(rate.effective_from).getFullYear() : null
  const yt = rate.effective_to ? new Date(rate.effective_to).getFullYear() : null
  if (!yf && !yt) return null
  return (yf && yt && yf !== yt) ? `${yf}–${yt}` : String(yf || yt)
}
function rateYearTitle(rate) {
  const f = rate.effective_from, t = rate.effective_to
  if (!f && !t) return ''
  return f && t ? `תוקף: ${f} → ${t}` : (f ? `תוקף מ-${f}` : `תוקף עד ${t}`)
}
function rateYearClass(rate) {
  const ref = rate.effective_to || rate.effective_from
  if (!ref) return ''
  const r = new Date(ref).getFullYear(), n = new Date().getFullYear()
  return r >= n - 1 ? 'year-pill--current' : (r >= n - 3 ? 'year-pill--recent' : 'year-pill--old')
}

const KIND_LABELS = { book: 'עמלת ספר', reward: 'שיעור תגמול', total: 'סה"כ' }
function rateKindLabel(rate) { return KIND_LABELS[(rate.rate_kind || '').toLowerCase()] || null }

// One agreement LINE can unfold into several DB rows — עמלת ספר and שיעור
// תגמול are stored separately and the real rate is their SUM (see
// commission_rate_summing.md, and rate_select._effective_rate which this
// mirrors). A range built from the raw rows therefore reads like
// "0.15% – 0.40%" while the agreement says one number, mixing a book rate, a
// reward rate and their total. Collapse to effective rates first.
function effectivePercents(items) {
  const kindOf = r => (r.rate_kind || 'single').toLowerCase()
  const groups = new Map()
  for (const r of items) {
    const key = `${(r.product || '').trim()}|${r.rate_scope || ''}`
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(r)
  }
  const out = []
  for (const rows of groups.values()) {
    const total = rows.find(r => kindOf(r) === 'total')
    if (total) { out.push(+total.rate); continue }
    const book = rows.find(r => kindOf(r) === 'book')
    const reward = rows.find(r => kindOf(r) === 'reward')
    if (book && reward) { out.push(+book.rate + +reward.rate); continue }
    if (book) { out.push(+book.rate); continue }
    if (reward) { out.push(+reward.rate); continue }
    for (const r of rows) out.push(+r.rate)
  }
  return out.map(x => +(x * 100).toFixed(2)).filter(x => x > 0)
}
function rangeLabel(items) {
  const pcts = effectivePercents(items)
  if (!pcts.length) return ''
  const lo = Math.min(...pcts), hi = Math.max(...pcts)
  return lo === hi ? `${lo}%` : `${lo}% – ${hi}%`
}

function _companiesOf(items) {
  const byCompany = new Map()
  for (const r of items) { const k = r.company_name || '—'; if (!byCompany.has(k)) byCompany.set(k, []); byCompany.get(k).push(r) }
  return Array.from(byCompany.entries()).map(([company, list]) => {
    return { company, items: list, range: rangeLabel(list) }
  }).sort((a, b) => b.items.length - a.items.length || _normCompany(a.company).localeCompare(_normCompany(b.company), 'he'))
}

const visibleCategories = computed(() => CATEGORIES.map(cat => {
  const items = rates.value.filter(r => categorize(r) === cat.key && applyFilters(r)).sort((a, b) => {
    const cmp = _normCompany(a.company_name).localeCompare(_normCompany(b.company_name), 'he')
    if (cmp !== 0) return cmp
    if (!a.product && b.product) return 1
    if (a.product && !b.product) return -1
    return (a.product || '').localeCompare(b.product || '', 'he')
  })
  const companies = _companiesOf(items)
  return { ...cat, items, companies, range: rangeLabel(items) }
}).filter(cat => cat.items.length > 0))
const visibleCategoryCount = computed(() => visibleCategories.value.length)

// All shelves start FOLDED (activeShelf = null). A click opens one book and
// drills into it; clicking it again folds it back.
const activeCategory = computed(() => activeShelf.value ? (visibleCategories.value.find(c => c.key === activeShelf.value) || null) : null)
function toggleShelf(key) { activeShelf.value = activeShelf.value === key ? null : key }

// First shelf (חיסכון ופנסיה) opens by default so the row is filled, not empty.
watch(visibleCategories, (cats) => {
  if (!cats.length) { activeShelf.value = null; return }
  if (!cats.find(c => c.key === activeShelf.value)) activeShelf.value = cats[0].key
}, { immediate: true })

// ── Coverage: how much of the ACTIVE production file these rates actually
// price, and which companies they miss. The shelf otherwise shows only
// percentages and counts, so an agent had no way to notice that most of their
// portfolio was contributing ₪0 to "עמלות צפויות". ──
const coverage = ref(null)
const coverageOpen = ref(false)

const coverageGaps = computed(() => (coverage.value?.rows || []).filter(r => r.reason))
const coveragePct = computed(() => {
  const t = coverage.value?.total_records || 0
  return t ? Math.round((coverage.value.covered_records / t) * 100) : 0
})
const coverageApprox = computed(() =>
  (coverage.value?.rows || []).reduce((n, r) => n + (r.approximate || 0), 0))
// Records priced from the built-in default rates rather than an agreement the
// agent actually uploaded. Worth calling out: those defaults are generic, so a
// figure resting on them shouldn't read as if it came from their contract.
const coverageSeeded = computed(() =>
  (coverage.value?.rows || []).reduce((n, r) => n + (r.seeded || 0), 0))

function fmtMoney(n) { return '₪' + Math.round(n || 0).toLocaleString('en-US') }

async function fetchCoverage() {
  try { coverage.value = (await api.get('/commission-rates/coverage')).data }
  catch (e) { coverage.value = null }
}

onMounted(() => { fetchRates(); fetchCoverage(); fetchAgreements() })
async function fetchRates() { loading.value = true; try { const res = await api.get('/commission-rates'); rates.value = res.data } finally { loading.value = false; ratesLoaded.value = true } }

const lastUpload = ref(null)

// ── Source documents per company ────────────────────────────────────────
const agreementCompanies = ref([])
const agreementDocTotal = ref(0)
const pdfLoading = ref(null)
const pdfError = ref('')

async function fetchAgreements() {
  try {
    const res = await api.get('/commission-rates/agreements')
    agreementCompanies.value = res.data.companies || []
    agreementDocTotal.value = res.data.total_documents || 0
  } catch (e) {
    agreementCompanies.value = []
  }
}

// Six translucent binders ship with the shelf art. A company always gets the
// SAME one, so the shelf looks like a real set of files rather than reshuffling
// on every load.
const BINDERS = import.meta.glob('../../assets/commission-shelf/books/*.webp', { eager: true, import: 'default' })
const BINDER_LIST = Object.keys(BINDERS).sort().map(k => BINDERS[k])

function binderArt(company) {
  let h = 0
  for (const ch of String(company || '')) h = (h * 31 + ch.charCodeAt(0)) % 100000
  return BINDER_LIST[h % (BINDER_LIST.length || 1)]
}

const shelfOpen = ref(false)
const openBinder = ref(null)

const openCompanyDocs = computed(
  () => agreementCompanies.value.find(c => c.stem === openBinder.value) || null,
)

function clickBinder(co) {
  // One document: open it. Several: show which, rather than guessing.
  if (co.documents.length === 1 && co.documents[0].has_file) {
    openBinder.value = null
    openPdf(co.documents[0])
    return
  }
  openBinder.value = openBinder.value === co.stem ? null : co.stem
}

// Every document that yielded no rates, with its company — the binder shows a
// flag, this says what to do about it.
const zeroDocs = computed(() =>
  agreementCompanies.value.flatMap(co =>
    co.documents.filter(d => !d.rates).map(d => ({ ...d, company: co.company })),
  ),
)

const DOC_REASONS = {
  appendix_missing: 'ההסכם מפנה לנספח התמורה שאינו כלול בקובץ',
  all_rows_dropped: 'כל השורות שנמצאו הן עמלת היקף/החזר — לא נפרעים',
  rate_table_present_but_unparsed: 'יש טבלה במסמך אך לא זוהו ממנה שורות נפרעים',
  no_readable_text: 'לא ניתן לקרוא טקסט מהקובץ (סריקה)',
  no_rates_in_document: 'אין במסמך טבלת שיעורי נפרעים',
}

function docReason(d) {
  if (d.status === 'error') return d.error || 'העיבוד נכשל'
  if (d.zero_reason) {
    const base = DOC_REASONS[d.zero_reason] || d.zero_reason
    return d.appendix_ref ? `${base} (${d.appendix_ref})` : base
  }
  // Uploaded before the extraction report existed — don't invent a cause.
  return 'לא חולצו שיעורים — פתחו את ה-PDF לבדיקה'
}

// The PDF needs the Bearer token, so it can't be a plain <a href>. Fetch it
// as a blob through the same axios client and hand the browser an object URL.
async function openPdf(d) {
  if (!d.has_file) return
  pdfError.value = ''
  pdfLoading.value = d.id
  try {
    const res = await api.get(`/ai/documents/${d.id}/file`, { responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
    const w = window.open(url, '_blank')
    if (!w) pdfError.value = 'הדפדפן חסם את החלון — אפשרו חלונות קופצים לאתר.'
    // Give the new tab time to take the URL before releasing it.
    setTimeout(() => URL.revokeObjectURL(url), 60000)
  } catch (e) {
    pdfError.value = e?.response?.status === 404
      ? 'קובץ ה-PDF אינו זמין עוד בשרת — העלו אותו שוב.'
      : 'לא ניתן לפתוח את ה-PDF.'
  } finally {
    pdfLoading.value = null
  }
}

function triggerUpload() { if (!queueBusy.value) fileInput.value?.click() }
async function onAgreementFile(e) {
  const files = Array.from((e.target && e.target.files) || [])
  if (e.target) e.target.value = ''
  if (!files.length) return
  const before = new Set(rates.value.map(r => r.id))
  lastUpload.value = null
  const items = await chat.uploadDocuments(files)
  await ratesChanged()
  const fresh = rates.value.filter(r => !before.has(r.id))
  if (fresh.length) activeShelf.value = categorize(fresh[0])

  // A batch reports per file in the queue rows; the detailed card (with the
  // dropped-rows list) is for a single agreement.
  const doc = items.length === 1 ? items[0].doc : null
  if (doc && doc.status !== 'error') {
    const ex = doc.structured_data?.extraction
    const out = extractionOutcome(ex, doc.structured_data?.rates || [])
    const [headline, ...rest] = out.text.split('\n\n')
    lastUpload.value = {
      tone: out.tone,
      headline: headline.replace(/\*\*/g, ''),
      detail: rest.join(' ').replace(/\*\*/g, ''),
      dropped: ex?.dropped || [],
    }
  }
}

// Any write to the shelf changes what the rates cover, so the banner has to be
// recomputed with them — otherwise it keeps reporting the gaps the agent just
// closed by uploading an agreement.
async function ratesChanged() { await fetchRates(); fetchCoverage(); fetchAgreements(); emit('rates-changed') }

async function seedRates() { seeding.value = true; try { await api.post('/commission-rates/seed'); await ratesChanged() } finally { seeding.value = false } }

function startEdit(rate) {
  addingNew.value = false; editingId.value = rate.id
  editForm.company_name = rate.company_name; editForm.product = rate.product || ''
  editForm.rate = +(rate.rate * 100).toFixed(4)
  editForm.rate_kind = (rate.rate_kind || 'single').toLowerCase()
  editForm.payment_frequency = rate.payment_frequency || 'חודשי'; editForm.paid_to = rate.paid_to || 'עיתים'; editForm.company_email = rate.company_email || ''
}
// NB: the payload deliberately omits effective_from/effective_to — the form has
// no date inputs, and the API now assigns only what it receives, so the
// agreement's validity window survives an edit instead of being nulled.
async function saveEdit(id) { await api.put(`/commission-rates/${id}`, { ...editForm, rate: editForm.rate / 100, product: editForm.product || null }); editingId.value = null; await ratesChanged() }
async function deleteRate(id) { await api.delete(`/commission-rates/${id}`); await ratesChanged() }
function startNew() { editingId.value = null; addingNew.value = true; newForm.company_name = ''; newForm.product = ''; newForm.rate = 0; newForm.rate_kind = 'single'; newForm.payment_frequency = 'חודשי'; newForm.paid_to = 'עיתים'; newForm.company_email = '' }
function cancelNew() { addingNew.value = false }
async function saveNew() { if (!newForm.company_name) return; await api.post('/commission-rates', { ...newForm, rate: newForm.rate / 100, product: newForm.product || null }); addingNew.value = false; await ratesChanged() }
</script>

<style scoped>
/* ── The agreement shelf ──────────────────────────────────────────────
   The binder artwork is lit glass on a dark reflective floor, so the board
   under it is dark too — the same two values `.shelf-media--fallback`
   already uses. Orange appears once, on the upload action, and nowhere as
   decoration. */
/* No upload button here — the hero already owns that action, and a second
   one in this tab's brand colour would be two CTAs for one job. */
.agshelf { margin: 0; }

/* Opens the bookcase. Icon-only: it sits beside the tab's single primary
   action and must not compete with it. `--chart-4` is this tab's identity
   colour; orange is reserved for brand actions and is wrong here. */
.btn-icon {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 10px 12px; border-radius: 12px;
  background: var(--bg-surface); color: var(--text-secondary);
  border: 1px solid var(--border-subtle);
  font-family: inherit; font-size: 12px; font-weight: 700; cursor: pointer;
  transition: all 0.18s var(--transition);
}
.btn-icon:hover { border-color: var(--chart-4); color: var(--chart-4); }
.btn-icon-count { font-size: 11px; opacity: 0.75; }

.agshelf-board {
  position: relative; border-radius: var(--radius-md); overflow: hidden;
  background:
    radial-gradient(120% 90% at 50% 0%, rgba(255,255,255,0.07), transparent 60%),
    linear-gradient(160deg, #2b2f3a, #1c2029);
}
/* A bookcase, not a scroller. A single row hid whatever did not fit — live,
   three insurers with no agreement sat off-screen to the left, which is the
   opposite of what an empty slot is for. Rows wrap, and a plank is drawn
   under each one by repeating the gradient at the row pitch. */
.agshelf-row {
  --binder-h: 140px;
  --row-gap: 50px;
  --row-pitch: calc(var(--binder-h) + var(--row-gap));
  display: flex; flex-wrap: wrap; align-items: flex-end;
  column-gap: 16px; row-gap: var(--row-gap);
  padding: 24px 20px 0;
  background-image: repeating-linear-gradient(180deg,
    transparent 0 calc(var(--binder-h) - 3px),
    rgba(255,255,255,0.20) calc(var(--binder-h) - 3px) calc(var(--binder-h) - 1px),
    rgba(0,0,0,0.34) calc(var(--binder-h) - 1px) calc(var(--binder-h) + 6px),
    transparent calc(var(--binder-h) + 6px) var(--row-pitch));
  background-origin: content-box;
  background-clip: content-box;
  background-repeat: repeat-y;
}
/* The board's front edge — what makes the binders read as standing ON
   something rather than floating in a dark box. */
/* The board's front edge — a lit lip, then the thickness of the plank. It is
   what makes the row read as a shelf and not a dark panel with pictures. */
.agshelf-edge {
  height: 16px;
  background: linear-gradient(180deg,
    rgba(255,255,255,0.22) 0 2px,
    rgba(255,255,255,0.09) 2px 5px,
    rgba(0,0,0,0.38) 100%);
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.28);
}

.binder, .slot {
  position: relative; flex: 0 0 auto;
  width: 96px; height: 140px; padding: 0;
  border: none; background: none; cursor: pointer; font-family: inherit;
}
/* The artwork is a lit binder photographed on black. `screen` drops that
   black into the board instead of stamping a dark tile onto it, so the
   binder reads as standing on the shelf rather than pasted over it. */
.binder-art {
  position: absolute; inset: 0;
  /* Cropped above the photographed floor and faded out at the base, so the
     binder meets the board instead of sitting in a lighter rectangle of its
     own studio backdrop. */
  background-size: 132% auto; background-position: center 30%;
  mix-blend-mode: screen;
  /* `screen` only hides a TRUE black. The photos are shot on a dark grey
     studio floor, which under screen stayed lighter than the board and drew
     a rectangle around every binder. Crushing the blacks first removes the
     backdrop; the radial mask feathers whatever survives at the edges. */
  filter: contrast(1.42) brightness(0.96);
  -webkit-mask-image: radial-gradient(74% 72% at 50% 44%, #000 52%, transparent 100%);
  mask-image: radial-gradient(74% 72% at 50% 44%, #000 52%, transparent 100%);
}
/* Contact shadow — the binder casts onto the board it stands on. */
.binder::after {
  content: ''; position: absolute; left: 6%; right: 6%; bottom: -2px; height: 12px;
  background: radial-gradient(60% 100% at 50% 0%, rgba(0,0,0,0.55), transparent 72%);
  pointer-events: none;
}
.binder-count {
  position: absolute; top: 6px; right: 6px; z-index: 2;
  min-width: 20px; height: 20px; padding: 0 5px;
  display: grid; place-items: center; border-radius: 10px;
  background: rgba(255,255,255,0.92); color: #1c2029;
  font-size: 11px; font-weight: 800;
}

/* The face only appears on hover/focus — at rest the shelf is just binders. */
.binder-face {
  position: absolute; inset: 0; z-index: 1; display: flex;
  flex-direction: column; align-items: center; justify-content: center; gap: 3px;
  border-radius: 4px; background: rgba(10,13,18,0.72);
  opacity: 0; transition: opacity 0.18s ease;
}
.binder:hover .binder-face,
.binder:focus-visible .binder-face,
.binder--open .binder-face { opacity: 1; }
.binder--open { outline: 2px solid var(--primary); outline-offset: 3px; border-radius: 4px; }
.binder-rates { font-size: 21px; font-weight: 800; color: #fff; line-height: 1; }
.binder-rates--zero { color: var(--amber); }
.binder-open { font-size: 10.5px; font-weight: 600; color: rgba(255,255,255,0.86); }

.binder-label, .slot .binder-label {
  /* Below the plank the binder stands on, not on top of it. */
  position: absolute; top: 100%; right: -8px; left: -8px; padding-top: 13px;
  font-size: 11px; font-weight: 600; color: rgba(255,255,255,0.84);
  text-align: center; line-height: 1.4;
  /* Two lines, because insurer legal names are long and one truncated line
     turned four different companies into "…מגדל מקפת קרנו". */
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden;
}
.binder-flag {
  position: absolute; top: 6px; left: 6px; z-index: 2;
  display: grid; place-items: center; width: 19px; height: 19px;
  border-radius: 50%; background: var(--amber); color: #1c2029;
}

/* An insurer with no signed agreement: a gap on the shelf, not a card. */
.slot {
  /* The flex ITEM is a full binder tall so every row of the bookcase is one
     line tall — a shorter item made its row shorter than the plank pitch and
     the plank was then drawn through the middle of the next row.
     The visible gap is shorter, drawn at the base: agreements the agent HAS
     are the content, and the gaps should recede rather than outnumber them
     at equal weight (live: 9 empty slots against 3 binders). */
  height: var(--binder-h, 140px);
  display: flex; flex-direction: column; align-items: center; justify-content: flex-end;
  gap: 5px; padding-bottom: 26px;
  border: none; background: none; color: rgba(255,255,255,0.5);
}
.slot::before {
  content: ''; position: absolute; left: 0; right: 0; bottom: 0; height: 98px;
  border: 1.5px dashed rgba(255,255,255,0.17); border-radius: 5px;
  background: rgba(255,255,255,0.025);
}
.slot > * { position: relative; z-index: 1; }
.slot::after { content: none; }
.slot:hover::before { border-color: var(--chart-4); background: rgba(255,255,255,0.06); }
.slot:hover { color: rgba(255,255,255,0.9); }
.slot-note { font-size: 10.5px; font-weight: 600; }
.slot .binder-label { color: rgba(255,255,255,0.5); }

/* The final row's labels sit below its plank and still need room, or the
   board clips them. */
.agshelf-row { padding-bottom: 44px; }

/* ── The picked binder's documents ── */
.agpick {
  margin-top: 12px; padding: 12px 14px;
  border: 1px solid var(--border-subtle); border-radius: var(--radius-md);
  background: var(--card-bg);
}
.agpick-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 9px; }
.agpick-head strong { font-size: 13.5px; color: var(--text); }
.agpick-sub { font-size: 11.5px; color: var(--text-muted); }
.agpick-x {
  margin-right: auto; border: none; background: none; cursor: pointer;
  font-size: 18px; line-height: 1; color: var(--text-muted); font-family: inherit;
}
.agpick-x:hover { color: var(--text); }
.agpick-list { list-style: none; display: flex; flex-direction: column; gap: 8px; }
.agpick-list li { display: grid; grid-template-columns: 1fr auto; gap: 5px 10px; align-items: center; }
.agpick-open {
  display: flex; align-items: center; gap: 8px; min-width: 0;
  padding: 6px 9px; border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle); background: none;
  font-family: inherit; font-size: 12.5px; color: var(--text);
  cursor: pointer; text-align: right;
}
.agpick-open:hover:not(:disabled) { background: var(--border-subtle); border-color: var(--text-muted); }
.agpick-open:disabled { opacity: 0.55; cursor: not-allowed; }
.agpick-open svg { flex-shrink: 0; color: var(--text-muted); }
.agpick-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; unicode-bidi: plaintext; }
.agpick-rates { font-size: 11.5px; color: var(--text-muted); white-space: nowrap; }
.agpick-rates--zero { color: var(--amber); font-weight: 700; }
.agpick-why { grid-column: 1 / -1; font-size: 11.5px; color: var(--amber); line-height: 1.6; }

.agshelf-notes {
  list-style: none; margin-top: 14px;
  display: flex; flex-direction: column; gap: 6px;
}
.agshelf-notes li {
  display: grid; grid-template-columns: minmax(120px, 0.9fr) minmax(0, 1.1fr) minmax(0, 1.4fr);
  align-items: baseline; gap: 4px 12px;
  font-size: 12px; color: var(--text-muted); line-height: 1.6;
}
.agshelf-notes strong { color: var(--text); font-weight: 700; }
.agnote-file, .agnote-why { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.agnote-file { unicode-bidi: plaintext; opacity: 0.85; }
.agnote-why { color: var(--amber); }
@media (max-width: 760px) {
  .agshelf-notes li { grid-template-columns: 1fr; }
  .agnote-file, .agnote-why { white-space: normal; }
}
.agshelf-err { margin-top: 10px; font-size: 12px; color: var(--danger, #c23934); }

@media (prefers-reduced-motion: reduce) {
  .binder-face { transition: none; }
}

/* Outcome of the last agreement upload — including the zero-rate case, which
   previously left every surface here unchanged. */
.up-result {
  margin-top: 10px; padding: 10px 12px;
  border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);
  background: var(--border-subtle); font-size: 12.5px; line-height: 1.65;
}
.up-result--warn { background: var(--amber-light); border-color: transparent; }
.up-result--warn .up-result-head { color: var(--amber); }
.up-result--ok .up-result-head { color: var(--text); }
.up-result-head {
  display: flex; align-items: center; gap: 7px;
  font-weight: 700;
}
.up-result-head svg { flex-shrink: 0; }
.up-result-x {
  margin-right: auto; border: none; background: none; cursor: pointer;
  font-size: 17px; line-height: 1; color: inherit; opacity: 0.55; font-family: inherit;
}
.up-result-x:hover { opacity: 1; }
.up-result-detail { margin-top: 5px; color: var(--text); }
.up-dropped { list-style: none; margin-top: 8px; display: flex; flex-direction: column; gap: 3px; }
.up-dropped li {
  display: flex; align-items: baseline; gap: 8px;
  font-size: 11.5px; color: var(--text-muted);
}
.up-dropped-name { color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.up-dropped-why { margin-right: auto; flex-shrink: 0; }
.up-dropped-more { opacity: 0.8; }

/* ══ מדף ההסכמים — horizontal picture accordion (your reference), RTL, pastel. ══ */
.rate-shelf { position: relative; }

.shelf-hero { position: relative; overflow: hidden; background: var(--card-bg); border: 1px solid var(--border-subtle); border-radius: var(--radius-xl, 24px); padding: 22px 26px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.shelf-hero .hero-copy { position: relative; z-index: 1; max-width: 62%; }
.shelf-art { position: absolute; inset-inline-end: 8px; top: 50%; transform: translateY(-50%); width: min(300px, 34%); aspect-ratio: 420 / 300; pointer-events: none; z-index: 0; }
@media (max-width: 720px) { .shelf-hero .hero-copy { max-width: 100%; } .shelf-art { display: none; } }

/* ── Welcome (no agreements yet), under the hero: realistic photo + type ── */
.shelf-welcome {
  position: relative; overflow: hidden; margin-top: 4px; min-height: 380px;
  display: flex; align-items: center;
  border-radius: var(--radius-xl, 24px); border: 1px solid var(--border-subtle);
  background: var(--card-bg);
}
/* The photo fills the left ~62% and dissolves toward the text: a mask, not a
   frame, so it reads as part of the page rather than a picture on it. */
.sw-photo {
  position: absolute; top: 0; bottom: 0; inset-inline-end: 0; width: 64%; z-index: 0;
  -webkit-mask-image: linear-gradient(to right, #000 0%, #000 52%, transparent 96%);
          mask-image: linear-gradient(to right, #000 0%, #000 52%, transparent 96%);
}
.sw-photo video, .sw-photo img { width: 100%; height: 100%; object-fit: cover; object-position: left center; display: block; }
.sw-copy { position: relative; z-index: 1; display: flex; flex-direction: column; gap: 12px; width: min(520px, 50%); padding: 44px 48px; }
/* App font, heavy/light contrast: 900 display over 400 body. */
.sw-display {
  margin: 0; font-family: 'Heebo', sans-serif; font-weight: 900;
  font-size: clamp(32px, 3.8vw, 48px); line-height: 1.05; letter-spacing: -0.03em; color: var(--text);
}
.sw-display-accent { color: var(--tab-commission); }
/* Slider: big step line + story-style progress bars, no icons. */
.sw-slider { margin-top: 14px; width: min(380px, 100%); }
.sw-slide-track { height: 40px; display: flex; align-items: center; overflow: hidden; }
.sw-slide { margin: 0; display: flex; align-items: baseline; gap: 12px; font-size: 22px; font-weight: 700; letter-spacing: -0.01em; color: var(--text); white-space: nowrap; }
.sw-slide-num { font-size: 13px; font-weight: 800; letter-spacing: 0.06em; color: var(--tab-commission); }
.sw-slide-enter-active { transition: opacity 0.26s ease-out, transform 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
.sw-slide-leave-active { transition: opacity 0.16s ease-in, transform 0.18s ease-in; }
.sw-slide-enter-from { opacity: 0; transform: translateY(14px); }
.sw-slide-leave-to { opacity: 0; transform: translateY(-10px); }
.sw-bars { display: flex; gap: 6px; margin-top: 8px; }
.sw-bar {
  /* 16px hit area; the visible bar is the 4px track drawn inside it */
  position: relative; flex: 1; height: 16px; padding: 0; border: none; background: none; cursor: pointer;
}
.sw-bar::before, .sw-bar-fill { position: absolute; inset-inline: 0; top: 6px; height: 4px; border-radius: 99px; }
.sw-bar::before { content: ''; background: color-mix(in srgb, var(--tab-commission) 16%, white); }
.sw-bar:focus-visible { outline: 2px solid var(--tab-commission); outline-offset: 2px; border-radius: 6px; }
.sw-bar-fill { display: block; width: 0; inset-inline-end: auto; background: var(--tab-commission); }
.sw-bar--done .sw-bar-fill { width: 100%; }
.sw-bar--on .sw-bar-fill { animation: sw-fill 2.8s linear forwards; }
.sw-bar--on.sw-bar--paused .sw-bar-fill { animation-play-state: paused; }
@keyframes sw-fill { from { width: 0; } to { width: 100%; } }
.sw-steps-static { list-style: none; margin: 14px 0 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.sw-steps-static li { display: flex; align-items: baseline; gap: 12px; font-size: 18px; font-weight: 700; color: var(--text); }
@media (max-width: 900px) {
  .shelf-welcome { flex-direction: column; align-items: stretch; min-height: 0; }
  .sw-photo { position: relative; width: 100%; height: 220px;
    -webkit-mask-image: linear-gradient(to bottom, #000 55%, transparent 100%);
            mask-image: linear-gradient(to bottom, #000 55%, transparent 100%); }
  .sw-copy { width: auto; padding: 4px 22px 28px; }
}
.hero-copy { display: flex; flex-direction: column; gap: 7px; }
.hero-eyebrow { display: inline-flex; align-items: center; gap: 7px; align-self: flex-start; font-size: 11px; font-weight: 700; letter-spacing: 0.04em; color: var(--chart-9); background: color-mix(in srgb, var(--chart-2) 12%, white); border: 1px solid color-mix(in srgb, var(--chart-2) 28%, white); padding: 4px 11px; border-radius: 999px; }
.hero-title { margin: 2px 0 0; font-size: 25px; font-weight: 800; letter-spacing: -0.02em; color: var(--text); }
.hero-sub { margin: 0; font-size: 13px; color: var(--text-secondary); line-height: 1.6; }
.hero-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-top: 10px; }
.btn-accent { display: inline-flex; align-items: center; gap: 8px; background: var(--chart-4); color: #fff; border: none; border-radius: 12px; padding: 11px 18px; font-size: 14px; font-family: inherit; font-weight: 700; cursor: pointer; box-shadow: 0 5px 14px color-mix(in srgb, var(--chart-4) 26%, transparent); transition: transform 0.2s var(--transition), background 0.2s var(--transition); }
.btn-accent:hover:not(:disabled) { transform: translateY(-1px); background: color-mix(in srgb, var(--chart-4) 88%, black); }
.btn-accent:disabled { opacity: 0.7; cursor: default; }
.btn-spin { width: 15px; height: 15px; border-radius: 50%; border: 2px solid rgba(255,255,255,0.4); border-top-color: #fff; animation: spin 0.7s linear infinite; }
.btn-ghost { display: inline-flex; align-items: center; gap: 6px; background: var(--bg-surface); color: var(--text-secondary); border: 1px solid var(--border-subtle); border-radius: 12px; padding: 10px 15px; font-size: 13px; font-family: inherit; font-weight: 600; cursor: pointer; transition: all 0.18s var(--transition); }
.btn-ghost:hover:not(:disabled) { border-color: var(--chart-4); color: var(--chart-4); }
.btn-ghost:disabled { opacity: 0.5; cursor: default; }
.hidden-file { display: none; }
.up-queue { margin-top: 12px; max-width: 520px; display: flex; flex-direction: column; gap: 6px; }
.uq-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.uq-row { display: flex; align-items: center; gap: 9px; padding: 6px 10px; border-radius: var(--radius-sm); background: var(--bg-surface); border: 1px solid var(--border-subtle); font-size: 12.5px; }
.uq-icon { flex-shrink: 0; width: 16px; height: 16px; display: inline-flex; align-items: center; justify-content: center; color: var(--text-muted); }
.uq-row--done .uq-icon { color: var(--green); }
.uq-row--error .uq-icon, .uq-row--error .uq-meta { color: var(--red); }
.uq-row--extracting .uq-icon { color: var(--chart-4); }
.uq-spin { width: 12px; height: 12px; border-radius: 50%; border: 2px solid color-mix(in srgb, var(--chart-4) 30%, transparent); border-top-color: var(--chart-4); animation: spin 0.8s linear infinite; }
.uq-name { flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text); font-weight: 600; }
.uq-meta { flex-shrink: 0; max-width: 55%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-muted); font-variant-numeric: tabular-nums; }
.uq-note { margin: 2px 0 0; font-size: 11.5px; color: var(--text-muted); }
.uq-clear { align-self: flex-start; border: none; background: none; padding: 2px 0; font-family: inherit; font-size: 12px; font-weight: 600; color: var(--text-secondary); cursor: pointer; text-decoration: underline; }
.uq-clear:hover { color: var(--chart-4); }
.hero-upload-error { margin: 8px 0 0; font-size: 12px; color: var(--red); font-weight: 600; }

/* ══ Coverage banner — how much of the portfolio the shelf actually prices ══ */
.cov { background: var(--card-bg); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg, 16px); padding: 14px 18px; margin-bottom: 14px; }
.cov--thin { border-color: color-mix(in srgb, var(--chart-4) 42%, transparent); background: color-mix(in srgb, var(--chart-4) 5%, var(--card-bg)); }
.cov-head { display: flex; align-items: center; gap: 11px; }
.cov-icon { display: inline-flex; align-items: center; justify-content: center; width: 30px; height: 30px; flex: none; border-radius: 9px; background: color-mix(in srgb, var(--chart-2) 14%, transparent); color: var(--chart-9); }
.cov--thin .cov-icon { background: color-mix(in srgb, var(--chart-4) 16%, transparent); color: var(--chart-4); }
.cov-headline { display: flex; flex-direction: column; gap: 2px; min-width: 0; flex: 1 1 auto; }
.cov-headline strong { font-size: 13.5px; font-weight: 700; color: var(--text); }
.cov-sub { font-size: 11.5px; color: var(--text-muted); }
.cov-pct { font-size: 19px; font-weight: 800; color: var(--chart-9); flex: none; }
.cov--thin .cov-pct { color: var(--chart-4); }
.cov-bar { height: 6px; border-radius: 999px; background: color-mix(in srgb, var(--text-muted) 14%, transparent); overflow: hidden; margin-top: 10px; }
.cov-fill { height: 100%; border-radius: 999px; background: var(--chart-9); transition: width 0.4s var(--transition); }
.cov--thin .cov-fill { background: var(--chart-4); }
.cov-toggle { display: inline-flex; align-items: center; gap: 6px; margin-top: 10px; padding: 0; background: none; border: none; font-family: inherit; font-size: 12px; font-weight: 600; color: var(--text-secondary); cursor: pointer; }
.cov-toggle:hover { color: var(--chart-4); }
.cov-toggle svg { transition: transform 0.2s var(--transition); }
.cov-gaps { list-style: none; margin: 10px 0 0; padding: 0; display: flex; flex-direction: column; gap: 1px; border-radius: 10px; overflow: hidden; }
.cov-gap { display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: var(--bg-surface); font-size: 12.5px; }
.cov-gap-co { font-weight: 650; color: var(--text); flex: 1 1 auto; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cov-gap-n { color: var(--text-muted); font-size: 11.5px; flex: none; }
.cov-gap-why { color: var(--chart-4); font-weight: 600; font-size: 11.5px; flex: none; text-align: start; }
@media (max-width: 640px) {
  .cov-gap { flex-wrap: wrap; gap: 4px 10px; }
  .cov-gap-co { flex: 1 0 100%; }
}

/* Rate-kind pill — one agreement line can unfold into ספר + תגמול rows, which
   otherwise render as visually identical duplicates. */
.kind-pill { flex: none; font-size: 10px; font-weight: 700; padding: 1.5px 7px; border-radius: 999px; border: 1px solid transparent; white-space: nowrap; }
.kind-pill--book { color: var(--chart-9); background: color-mix(in srgb, var(--chart-9) 11%, transparent); border-color: color-mix(in srgb, var(--chart-9) 26%, transparent); }
.kind-pill--reward { color: var(--chart-6); background: color-mix(in srgb, var(--chart-6) 11%, transparent); border-color: color-mix(in srgb, var(--chart-6) 26%, transparent); }
.kind-pill--total { color: var(--chart-2); background: color-mix(in srgb, var(--chart-2) 13%, transparent); border-color: color-mix(in srgb, var(--chart-2) 30%, transparent); }
.scope-pill { flex: none; font-size: 10px; font-weight: 650; padding: 1.5px 7px; border-radius: 999px; color: var(--text-muted); background: color-mix(in srgb, var(--text-muted) 10%, transparent); white-space: nowrap; }

.shelf-toolbar { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 14px; }
.rate-search { display: inline-flex; align-items: center; gap: 6px; padding: 8px 12px; border: 1px solid var(--border-subtle); border-radius: 10px; background: var(--bg-surface); color: var(--text-muted); transition: border-color 0.2s, box-shadow 0.2s; }
.rate-search:focus-within { border-color: var(--chart-2); box-shadow: 0 0 0 3px color-mix(in srgb, var(--chart-2) 18%, transparent); color: var(--chart-9); }
.rate-search input { border: none; outline: none; background: transparent; font-family: inherit; font-size: 12.5px; width: 180px; color: var(--text); }
.year-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.year-chip { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 999px; font-family: inherit; font-size: 12px; font-weight: 600; color: var(--text-secondary); cursor: pointer; transition: all 0.18s var(--transition); }
.year-chip:hover { border-color: var(--chart-2); color: var(--text); }
.year-chip-count { font-size: 10.5px; font-weight: 700; padding: 1px 7px; background: var(--bg); border-radius: 999px; color: var(--text-muted); }
.year-chip--active { background: var(--text); border-color: var(--text); color: #fff; }
.year-chip--active .year-chip-count { background: rgba(255,255,255,0.18); color: #fff; }
.year-chip--active[data-tone="current"] { background: var(--chart-4); border-color: transparent; }

/* Category hue tokens — the app's VIVID "subjects" palette (chart colors). */
.tint-savings { --cat: var(--chart-2);  --cat-deep: var(--chart-9);   --cat-tint: color-mix(in srgb, var(--chart-2) 16%, white); }
.tint-risk    { --cat: var(--chart-4);  --cat-deep: #5A39B8;          --cat-tint: color-mix(in srgb, var(--chart-4) 16%, white); }
.tint-health  { --cat: var(--chart-5);  --cat-deep: var(--chart-10);  --cat-tint: color-mix(in srgb, var(--chart-5) 20%, white); }
.tint-other   { --cat: var(--chart-3);  --cat-deep: #565A1D;          --cat-tint: color-mix(in srgb, var(--chart-3) 20%, white); }

/* ── The picture accordion (your reference: tall panels, widen on hover) ── */
.shelf-rack { display: flex; flex-direction: row; gap: 14px; height: 300px; margin-bottom: 16px; }
.shelf-panel {
  position: relative; flex: 1 1 0; min-width: 132px;    /* closed books: narrow, clearly "closed" */
  border: none; padding: 0; cursor: pointer; border-radius: 18px; overflow: hidden;
  box-shadow: 0 4px 16px rgba(0,0,0,0.10);
  transition: flex 0.6s var(--transition), box-shadow 0.4s var(--transition), transform 0.35s var(--transition);
  outline: none;
}
/* The open book is much wider (~4.5×) so closed books read as closed. */
.shelf-panel--active { flex: 4.5 1 0; box-shadow: 0 18px 44px rgba(0,0,0,0.22); }
/* A closed book lifts on hover to signal it's clickable (opens on click). */
.shelf-panel:not(.shelf-panel--active):hover { transform: translateY(-6px); box-shadow: 0 14px 30px rgba(0,0,0,0.20); }
.shelf-panel:focus-visible { outline: 3px solid color-mix(in srgb, var(--cat) 55%, white); outline-offset: 2px; }

.shelf-media { position: absolute; inset: 0; z-index: 0; background-size: cover; background-position: center; transition: transform 0.6s var(--transition); }
/* Slow ken-burns drift while a shelf is open — feels alive. */
.shelf-panel--active .shelf-media { animation: shelfKen 14s ease-in-out infinite alternate; }
@keyframes shelfKen { from { transform: scale(1.03); } to { transform: scale(1.1) translate(-1.5%, 1%); } }
/* One-time light sheen sweeping across the picture when it opens. */
.shelf-panel::after { content: ''; position: absolute; inset: 0; z-index: 1; pointer-events: none; background: linear-gradient(115deg, transparent 34%, rgba(255,255,255,0.18) 50%, transparent 66%); transform: translateX(-130%); }
.shelf-panel--active::after { animation: shelfSheen 3.4s var(--transition) 0.25s; }
@keyframes shelfSheen { 0% { transform: translateX(-130%); } 55%, 100% { transform: translateX(130%); } }
.shelf-media--fallback { background: radial-gradient(120% 100% at 50% 0%, color-mix(in srgb, var(--cat) 46%, white), transparent 62%), linear-gradient(160deg, color-mix(in srgb, var(--cat) 34%, #2b2f3a), color-mix(in srgb, var(--cat-deep) 30%, #1c2029)); }

/* Constant, LIGHT veil (like the reference's bg-opacity-40) — picture stays visible. */
.shelf-veil { position: absolute; inset: 0; z-index: 0; background: linear-gradient(to top, rgba(12,16,26,0.62) 0%, rgba(12,16,26,0.18) 42%, rgba(12,16,26,0.05) 100%); }

.shelf-caption { position: absolute; z-index: 2; inset-inline: 0; bottom: 0; display: flex; flex-direction: column; align-items: flex-start; gap: 6px; padding: 16px 18px; color: #fff; text-align: start; }
.shelf-badge { display: inline-flex; align-items: center; justify-content: center; width: 36px; height: 36px; border-radius: 11px; background: rgba(255,255,255,0.18); border: 1px solid rgba(255,255,255,0.3); backdrop-filter: blur(5px); color: #fff; margin-bottom: 2px; }
.shelf-name { font-size: 16px; font-weight: 800; letter-spacing: -0.01em; line-height: 1.2; text-shadow: 0 2px 10px rgba(0,0,0,0.55); }
.shelf-meta { font-size: 12px; font-weight: 600; color: rgba(255,255,255,0.9); white-space: nowrap; opacity: 1; transition: opacity 0.35s var(--transition); text-shadow: 0 1px 6px rgba(0,0,0,0.5); }
/* A CLOSED book keeps its name HORIZONTAL at the bottom (just hides the meta line). */
.shelf-panel:not(.shelf-panel--active) .shelf-meta { display: none; }
/* "click to open / close" hint chip — only on the open book. */
.shelf-hint { display: inline-flex; align-items: center; gap: 5px; margin-top: 4px; padding: 4px 10px; font-size: 11px; font-weight: 700; color: #fff; background: rgba(255,255,255,0.18); border: 1px solid rgba(255,255,255,0.3); border-radius: 999px; backdrop-filter: blur(4px); white-space: nowrap; }
.shelf-panel:not(.shelf-panel--active) .shelf-hint { display: none; }

/* ── The opened shelf's agreements ── */
.shelf-open { background: var(--card-bg); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); overflow: hidden; }
.shelf-open-head { display: flex; align-items: center; gap: 10px; padding: 13px 18px; background: linear-gradient(95deg, var(--cat-tint) 0%, transparent 62%); border-bottom: 1px solid var(--border-subtle); }
.soh-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--cat); flex: 0 0 auto; }
.soh-title { margin: 0; font-size: 16px; font-weight: 800; color: var(--text); letter-spacing: -0.01em; }
.soh-meta { font-size: 12px; font-weight: 600; color: var(--text-muted); margin-inline-start: auto; }
.shelf-open-body { overflow-x: auto; }

.rate-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.rate-table thead { background: var(--glass-hover); }
.rate-table th { padding: 9px 12px; text-align: right; font-weight: 700; color: var(--text-muted); border-bottom: 1px solid var(--border-subtle); font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em; }
.rate-table th.num, .rate-table td.num { text-align: left; }
.rate-table td { padding: 9px 12px; border-bottom: 1px solid var(--border-subtle); color: var(--text); vertical-align: middle; }
.rate-table tbody tr { transition: background 0.15s; }
.rate-table tbody tr:hover { background: var(--glass-hover); }
.rate-table tbody:last-child tr:last-child td { border-bottom: none; }
.col-product { width: auto; } .col-rate { width: 92px; } .col-freq { width: 90px; } .col-paidto { width: 90px; } .col-email { width: 200px; } .col-actions { width: 60px; }

.company-binder { animation: binderIn 0.35s var(--transition) both; }
@keyframes binderIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: none; } }
.company-row td { padding: 9px 12px; background: var(--bg); border-bottom: 1px solid var(--border-subtle); border-inline-start: 3px solid var(--company-color); }
.company-binder + .company-binder .company-row td { border-top: 1px solid var(--border-subtle); }
.company-row-inner { display: flex; align-items: center; gap: 10px; }
.company-tab { width: 10px; height: 10px; border-radius: 3px; background: var(--company-color); flex: 0 0 auto; box-shadow: 0 0 0 3px color-mix(in srgb, var(--company-color) 18%, white); }
.company-row-name { font-size: 13px; font-weight: 800; color: var(--text); }
.company-row-count { font-size: 10.5px; font-weight: 600; color: var(--text-muted); padding: 2px 8px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 999px; }
.company-row-range { font-size: 10.5px; font-weight: 700; color: color-mix(in srgb, var(--company-color) 66%, black); padding: 2px 9px; background: color-mix(in srgb, var(--company-color) 13%, white); border-radius: 999px; margin-inline-start: auto; }
.edit-stack { display: flex; flex-direction: column; gap: 4px; }
.product-cell { color: var(--text-secondary); max-width: 380px; }
.product-line { display: inline-flex; align-items: center; gap: 8px; max-width: 100%; }
.product-line > span:first-child { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 0 1 auto; }
.product-cell--default { color: var(--text-muted); font-style: italic; }
.year-pill { flex: 0 0 auto; font-size: 10px; font-weight: 700; padding: 1px 7px; border-radius: 999px; border: 1px solid transparent; }
.year-pill--current { background: color-mix(in srgb, var(--chart-2) 16%, white); color: var(--chart-9); border-color: color-mix(in srgb, var(--chart-2) 40%, white); }
.year-pill--recent { background: var(--bg); color: var(--text-secondary); border-color: var(--border-subtle); }
.year-pill--old { background: transparent; color: var(--text-muted); border-color: var(--border-subtle); }
.muted-cell { color: var(--text-muted); }
.rate-pill { display: inline-block; min-width: 58px; text-align: center; padding: 3px 10px; background: var(--cat-tint); color: var(--cat-deep); border-radius: 999px; font-weight: 800; }
.email-cell { font-size: 11px; color: var(--text-muted); max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.actions { display: flex; gap: 4px; white-space: nowrap; justify-content: flex-end; }
.actions-col { width: 60px; }
.icon-btn { width: 27px; height: 27px; display: inline-flex; align-items: center; justify-content: center; padding: 0; background: transparent; border: 1px solid transparent; border-radius: 7px; cursor: pointer; color: var(--text-muted); transition: all 0.18s var(--transition); }
.icon-btn--edit:hover  { background: color-mix(in srgb, var(--chart-2) 14%, white); color: var(--chart-9); border-color: color-mix(in srgb, var(--chart-2) 40%, white); }
.icon-btn--del:hover   { background: var(--red-light); color: var(--red); border-color: var(--red); }
.icon-btn--save:hover  { background: var(--green-light); color: var(--green-deep); border-color: var(--green); }
.icon-btn--cancel:hover { background: var(--red-light); color: var(--red); border-color: var(--red); }
.ltr-number { direction: ltr; unicode-bidi: isolate; }
.edit-input { width: 100%; padding: 6px 9px; border: 1px solid var(--border-subtle); border-radius: 7px; font-size: 12px; font-family: 'Heebo', sans-serif; background: var(--bg-surface); color: var(--text); transition: border-color 0.2s, box-shadow 0.2s; }
.edit-input:focus { outline: none; border-color: var(--chart-2); box-shadow: 0 0 0 3px color-mix(in srgb, var(--chart-2) 18%, transparent); }
.num-input { width: 86px; } .email-input { width: 160px; }
.add-card { margin-top: 14px; background: var(--card-bg); border: 1px dashed color-mix(in srgb, var(--chart-4) 40%, var(--border-subtle)); border-radius: var(--radius-lg); overflow: hidden; }
.add-card-head { display: flex; align-items: center; gap: 10px; padding: 12px 16px; background: color-mix(in srgb, var(--chart-4) 7%, white); }
.add-card-icon { display: inline-flex; align-items: center; justify-content: center; width: 30px; height: 30px; border-radius: 8px; border: 1px dashed var(--chart-4); color: var(--chart-4); }
.add-card-title { font-size: 14px; font-weight: 800; color: var(--text); }
.add-card-hint { font-size: 11px; color: var(--text-muted); }
.empty { text-align: center; color: var(--text-muted); font-size: 13.5px; padding: 30px 16px; line-height: 1.7; }
.empty strong { color: var(--chart-9); }
.empty--filter { padding: 16px; }
.loading { display: flex; justify-content: center; padding: 30px 16px; }
.spinner { width: 26px; height: 26px; border: 3px solid var(--border-subtle); border-top-color: var(--chart-4); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.fade-enter-active, .fade-leave-active { transition: opacity 0.25s var(--transition); }
.fade-enter-from, .fade-leave-to { opacity: 0; }

@media (max-width: 760px) {
  .shelf-rack { height: 360px; }
  .shelf-panel { flex-basis: 60px; min-width: 60px; }
  .col-email, .col-freq, .col-paidto { display: none; }
}
@media (prefers-reduced-motion: reduce) {
  .shelf-panel, .shelf-media, .company-binder, .uq-spin { transition: none !important; animation: none !important; }
}
</style>
