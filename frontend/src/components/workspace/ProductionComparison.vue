<template>
  <div class="prod-comparison">
    <!-- No history -->
    <div v-if="!history.length && !comparisonResult" class="empty-state">
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
      </svg>
      <p>אין קבצים קודמים להשוואה — החלף את קובץ הפרודוקציה ותוכל להשוות</p>
    </div>

    <!-- File selector -->
    <div v-else-if="!comparisonResult && !comparing" class="selector-section">
      <h4 class="selector-title">בחר קובץ קודם להשוואה</h4>
      <div class="history-grid">
        <div
          v-for="f in history"
          :key="f.id"
          class="history-card"
          :class="{ selected: selectedFileId === f.id }"
          @click="selectedFileId = f.id"
        >
          <div class="hc-radio">
            <div class="hc-radio-inner" v-if="selectedFileId === f.id"></div>
          </div>
          <div class="hc-info">
            <span class="hc-name">{{ f.filename }}</span>
            <span class="hc-meta">
              <span class="ltr-number">{{ f.record_count.toLocaleString() }}</span> רשומות
              · {{ formatDate(f.uploaded_at) }}
            </span>
          </div>
        </div>
      </div>
      <button
        class="btn-compare"
        :disabled="!selectedFileId"
        @click="runCompare"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
        </svg>
        <span>השווה קבצים</span>
      </button>
    </div>

    <!-- Comparing -->
    <div v-else-if="comparing" class="loading-state">
      <div class="loader">
        <div class="loader-ring"></div>
        <div class="loader-ring delay"></div>
      </div>
      <span>משווה קבצים...</span>
    </div>

    <!-- Results -->
    <div v-else-if="comparisonResult" class="results-section">
      <div class="results-header">
        <h4>תוצאות השוואה</h4>
        <button class="btn-back" @click="$emit('reset')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="19" y1="12" x2="5" y2="12"/>
            <polyline points="12 19 5 12 12 5"/>
          </svg>
          חזרה
        </button>
      </div>

      <!-- Comparison context: which files -->
      <div class="compare-context" v-if="comparisonResult.summary.current_filename">
        <div class="compare-file compare-file-current">
          <span class="cf-label">{{ currentMonthLabel }}</span>
          <span class="cf-date ltr-number" v-if="comparisonResult.summary.current_date">{{ formatDate(comparisonResult.summary.current_date) }}</span>
        </div>
        <svg class="compare-arrow" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 5 5 12 12 19"/>
        </svg>
        <div class="compare-file compare-file-previous">
          <span class="cf-label">{{ previousMonthLabel }}</span>
          <span class="cf-date ltr-number" v-if="comparisonResult.summary.previous_date">{{ formatDate(comparisonResult.summary.previous_date) }}</span>
        </div>
      </div>

      <!-- Summary KPI strip -->
      <div class="summary-strip">
        <div class="summary-badge badge-green" @click="openCategory('new')">
          <span class="ltr-number">{{ comparisonResult.summary.new_count }}</span>
          <span>חדשים</span>
        </div>
        <div class="summary-badge badge-red" @click="openCategory('removed')">
          <span class="ltr-number">{{ comparisonResult.summary.removed_count }}</span>
          <span>הוסרו</span>
        </div>
        <div class="summary-badge badge-amber" @click="openCategory('changed')">
          <span class="ltr-number">{{ comparisonResult.summary.changed_count }}</span>
          <span>שונו</span>
        </div>
        <div class="summary-badge badge-gray">
          <span class="ltr-number">{{ comparisonResult.summary.unchanged_count }}</span>
          <span>ללא שינוי</span>
        </div>
      </div>

      <!-- Donut Chart -->
      <div class="chart-card">
        <div class="chart-title-row">
          <span class="chart-title">התפלגות שינויים</span>
          <span class="chart-subtitle">לחץ על פרוסה לצפייה בפרטים</span>
        </div>
        <apexchart
          type="donut"
          height="400"
          :options="chartOptions"
          :series="chartSeries"
          @dataPointSelection="onChartClick"
        />
        <!-- Custom legend -->
        <div class="chart-legend">
          <div
            v-for="(cat, i) in CATEGORIES"
            :key="cat.key"
            class="legend-item"
            :class="{ clickable: cat.key !== 'unchanged' }"
            @click="cat.key !== 'unchanged' && openCategory(cat.key)"
          >
            <span class="legend-dot" :style="{ background: cat.color }"></span>
            <span class="legend-label">{{ cat.label }}</span>
            <span class="legend-value ltr-number">{{ chartSeries[i]?.toLocaleString() || 0 }}</span>
          </div>
        </div>
      </div>

      <!-- Company breakdown charts -->
      <div class="charts-grid">
        <!-- New by company -->
        <div class="chart-card chart-card-half" v-if="newByCompany.series.length">
          <div class="chart-title-row">
            <span class="chart-title">חדשים לפי חברה</span>
            <span class="chart-badge badge-green"><span class="ltr-number">{{ comparisonResult.summary.new_count }}</span></span>
          </div>
          <apexchart
            type="donut"
            height="380"
            :options="newByCompany.options"
            :series="newByCompany.series"
            @dataPointSelection="(e, chart, config) => onCompanyChartClick('new', newByCompany.labels, config)"
          />
          <div class="chart-legend">
            <div
              v-for="(label, i) in newByCompany.labels"
              :key="label"
              class="legend-item clickable"
              @click="onCompanyChartClick('new', newByCompany.labels, { dataPointIndex: i })"
            >
              <span class="legend-dot" :style="{ background: COMPANY_COLORS[i % COMPANY_COLORS.length] }"></span>
              <span class="legend-label">{{ label }}</span>
              <span class="legend-value ltr-number">{{ newByCompany.series[i]?.toLocaleString() }}</span>
            </div>
          </div>
        </div>

        <!-- Removed by company -->
        <div class="chart-card chart-card-half" v-if="removedByCompany.series.length">
          <div class="chart-title-row">
            <span class="chart-title">הוסרו לפי חברה</span>
            <span class="chart-badge badge-red"><span class="ltr-number">{{ comparisonResult.summary.removed_count }}</span></span>
          </div>
          <apexchart
            type="donut"
            height="380"
            :options="removedByCompany.options"
            :series="removedByCompany.series"
            @dataPointSelection="(e, chart, config) => onCompanyChartClick('removed', removedByCompany.labels, config)"
          />
          <div class="chart-legend">
            <div
              v-for="(label, i) in removedByCompany.labels"
              :key="label"
              class="legend-item clickable"
              @click="onCompanyChartClick('removed', removedByCompany.labels, { dataPointIndex: i })"
            >
              <span class="legend-dot" :style="{ background: COMPANY_COLORS[(i + 4) % COMPANY_COLORS.length] }"></span>
              <span class="legend-label">{{ label }}</span>
              <span class="legend-value ltr-number">{{ removedByCompany.series[i]?.toLocaleString() }}</span>
            </div>
          </div>
        </div>

        <!-- Changed by company -->
        <div class="chart-card chart-card-half" v-if="changedByCompany.series.length">
          <div class="chart-title-row">
            <span class="chart-title">שונו לפי חברה</span>
            <span class="chart-badge badge-amber"><span class="ltr-number">{{ comparisonResult.summary.changed_count }}</span></span>
          </div>
          <apexchart
            type="donut"
            height="380"
            :options="changedByCompany.options"
            :series="changedByCompany.series"
            @dataPointSelection="(e, chart, config) => onCompanyChartClick('changed', changedByCompany.labels, config)"
          />
          <div class="chart-legend">
            <div
              v-for="(label, i) in changedByCompany.labels"
              :key="label"
              class="legend-item clickable"
              @click="onCompanyChartClick('changed', changedByCompany.labels, { dataPointIndex: i })"
            >
              <span class="legend-dot" :style="{ background: COMPANY_COLORS[(i + 8) % COMPANY_COLORS.length] }"></span>
              <span class="legend-label">{{ label }}</span>
              <span class="legend-value ltr-number">{{ changedByCompany.series[i]?.toLocaleString() }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ===== Changed Insights Section ===== -->
      <div v-if="changedInsights.totalClients > 0" class="changed-section">
        <div class="changed-section-header">
          <span class="changed-section-title">שונו — תובנות</span>
          <span class="chart-badge badge-amber"><span class="ltr-number">{{ changedInsights.totalClients }}</span> לקוחות</span>
        </div>

        <!-- KPI cards -->
        <div class="changed-kpi-strip">
          <div class="changed-kpi" :class="changedInsights.totalPremiumDiff >= 0 ? 'kpi-green' : 'kpi-red'">
            <span class="changed-kpi-value ltr-number">{{ changedInsights.totalPremiumDiff >= 0 ? '+' : '' }}{{ formatAmount(changedInsights.totalPremiumDiff) }}</span>
            <span class="changed-kpi-label">שינוי פרמיה כולל</span>
            <span v-if="comparisonResult.summary.premium_positive || comparisonResult.summary.premium_negative" class="kpi-split">
              <span class="kpi-split-up ltr-number" v-if="comparisonResult.summary.premium_positive">&#x25B2; {{ comparisonResult.summary.premium_positive }}</span>
              <span class="kpi-split-down ltr-number" v-if="comparisonResult.summary.premium_negative">&#x25BC; {{ comparisonResult.summary.premium_negative }}</span>
            </span>
          </div>
          <div class="changed-kpi" :class="changedInsights.totalAccumulationDiff >= 0 ? 'kpi-green' : 'kpi-red'">
            <span class="changed-kpi-value ltr-number">{{ changedInsights.totalAccumulationDiff >= 0 ? '+' : '' }}{{ formatAmount(changedInsights.totalAccumulationDiff) }}</span>
            <span class="changed-kpi-label">שינוי צבירה כולל</span>
            <span v-if="comparisonResult.summary.accum_positive || comparisonResult.summary.accum_negative" class="kpi-split">
              <span class="kpi-split-up ltr-number" v-if="comparisonResult.summary.accum_positive">&#x25B2; {{ comparisonResult.summary.accum_positive }}</span>
              <span class="kpi-split-down ltr-number" v-if="comparisonResult.summary.accum_negative">&#x25BC; {{ comparisonResult.summary.accum_negative }}</span>
            </span>
          </div>
          <div class="changed-kpi kpi-pink" v-if="comparisonResult.summary.has_commission_data">
            <span class="changed-kpi-value ltr-number">{{ formatAmount(comparisonResult.summary.commission_total) }}</span>
            <span class="changed-kpi-label">סה"כ עמלה (נפרעים)</span>
            <span class="kpi-split">
              <span class="kpi-split-up kpi-split-clickable ltr-number" @click="openCommissionFilter('has')">&#x25B2; {{ comparisonResult.summary.commission_positive_count }} עם עמלה</span>
              <span class="kpi-split-down kpi-split-clickable ltr-number" v-if="comparisonResult.summary.commission_zero_count" @click="openCommissionFilter('zero')">&#x25BC; {{ comparisonResult.summary.commission_zero_count }} ללא עמלה</span>
            </span>
            <span v-if="comparisonResult.summary.commission_diff_positive || comparisonResult.summary.commission_diff_negative" class="kpi-split" style="margin-top:2px;padding-top:4px;border-top:1px solid rgba(0,0,0,0.06)">
              <span class="kpi-split-up kpi-split-clickable ltr-number" @click="openCommissionFilter('positive')">&#x25B2; {{ comparisonResult.summary.commission_diff_positive }} עלייה</span>
              <span class="kpi-split-down kpi-split-clickable ltr-number" @click="openCommissionFilter('negative')">&#x25BC; {{ comparisonResult.summary.commission_diff_negative }} ירידה</span>
            </span>
            <span v-else-if="comparisonResult.summary.commission_positive_count" class="kpi-no-diff-note">
              הועלה סט נפרעים אחד — העלה נפרעים חדשים להשוואה
            </span>
          </div>
          <div class="changed-kpi kpi-clickable" @click="openChangedByType('פרמיה')">
            <span class="changed-kpi-value ltr-number">{{ changedInsights.premiumCount }}</span>
            <span class="changed-kpi-label">שינוי פרמיה</span>
          </div>
          <div class="changed-kpi kpi-clickable" @click="openChangedByType('צבירה')">
            <span class="changed-kpi-value ltr-number">{{ changedInsights.accumulationCount }}</span>
            <span class="changed-kpi-label">שינוי צבירה</span>
          </div>
          <div class="changed-kpi kpi-clickable" @click="openChangedByType('מוצרים')">
            <span class="changed-kpi-value ltr-number">{{ changedInsights.productCount }}</span>
            <span class="changed-kpi-label">שינוי מוצרים</span>
          </div>
        </div>

        <!-- No commission data note -->
        <div v-if="comparisonResult.summary.has_commission_data === false" class="no-commission-note">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          אין קבצי נפרעים — העלה קבצי נפרעים בלשונית השוואה כדי לראות נתוני עמלות
        </div>

        <!-- Charts row: donut + bar -->
        <div class="charts-grid">
          <!-- Change type donut -->
          <div class="chart-card chart-card-half">
            <div class="chart-title-row">
              <span class="chart-title">שונו לפי סוג שינוי</span>
              <span class="chart-subtitle">לחץ על פרוסה לצפייה בפרטים</span>
            </div>
            <apexchart
              type="donut"
              height="380"
              :options="changeTypeChartOptions"
              :series="changeTypeChartSeries"
              @dataPointSelection="onChangeTypeChartClick"
            />
            <div class="chart-legend">
              <div
                v-for="(ct, i) in CHANGE_TYPES"
                :key="ct.field"
                class="legend-item clickable"
                @click="openChangedByType(ct.field)"
              >
                <span class="legend-dot" :style="{ background: ct.color }"></span>
                <span class="legend-label">{{ ct.label }}</span>
                <span class="legend-value ltr-number">{{ changeTypeChartSeries[i]?.toLocaleString() || 0 }}</span>
              </div>
            </div>
          </div>

          <!-- Top changers bar chart -->
          <div class="chart-card chart-card-half">
            <div class="chart-title-row">
              <span class="chart-title">גדולי השינויים</span>
              <div class="bar-toggle">
                <button
                  class="bar-toggle-btn"
                  :class="{ active: barMode === 'premium' }"
                  @click="barMode = 'premium'"
                >פרמיה</button>
                <button
                  class="bar-toggle-btn"
                  :class="{ active: barMode === 'accumulation' }"
                  @click="barMode = 'accumulation'"
                >צבירה</button>
              </div>
            </div>
            <apexchart
              type="bar"
              height="380"
              :options="topChangersChartOptions"
              :series="topChangersChartSeries"
              @dataPointSelection="onBarChartClick"
            />
          </div>
        </div>
      </div>

      <!-- ===== Clients Table ===== -->
      <div class="clients-table-section">
        <div class="table-header-row">
          <span class="table-section-title">רשימת לקוחות</span>
          <div class="table-filter-tabs">
            <button
              v-for="tab in tableTabs"
              :key="tab.key"
              class="table-tab"
              :class="{ active: tableFilter === tab.key }"
              @click="tableFilter = tab.key"
            >
              {{ tab.label }}
              <b class="ltr-number">{{ tab.count }}</b>
            </button>
          </div>
        </div>

        <div class="table-search-wrap">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input v-model="tableSearch" class="table-search" placeholder="חיפוש לפי שם או ת.ז..." />
        </div>

        <div class="tbl-wrap">
          <table class="pc-table">
            <thead>
              <tr>
                <th style="width:28px"></th>
                <th>שם</th>
                <th>ת.ז</th>
                <th>חברה</th>
                <th>מוצרים</th>
                <th>פרמיה</th>
                <th>צבירה</th>
                <th v-if="comparisonResult.summary.has_commission_data">עמלה</th>
                <th v-if="tableFilter === 'changed'">שינוי</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="c in paginatedTableClients"
                :key="c.id_number"
                class="pc-row"
                @click="openDetail(c)"
              >
                <td>
                  <span class="pc-dot" :class="tableFilter === 'new' ? 'dot-new' : tableFilter === 'removed' ? 'dot-removed' : 'dot-changed'"></span>
                </td>
                <td class="td-name">{{ c.name }}</td>
                <td class="td-id"><span class="ltr-number">{{ c.id_number }}</span></td>
                <td class="td-company" :title="c.company">{{ c.company || '—' }}</td>
                <td><span class="ltr-number">{{ c.products_count }}</span></td>
                <td>
                  <span v-if="c.premium" class="ltr-number">{{ formatAmount(c.premium) }}</span>
                  <span v-else>—</span>
                </td>
                <td>
                  <span v-if="c.accumulation" class="ltr-number">{{ formatAmount(c.accumulation) }}</span>
                  <span v-else>—</span>
                </td>
                <td v-if="comparisonResult.summary.has_commission_data">
                  <span v-if="c.commission" class="ltr-number">{{ formatAmount(c.commission) }}</span>
                  <span v-else>—</span>
                </td>
                <td v-if="tableFilter === 'changed'" class="td-changes">
                  <span v-if="c.premium_diff" class="change-pill" :class="c.premium_diff > 0 ? 'pill-up' : 'pill-down'">
                    פרמיה {{ c.premium_diff > 0 ? '+' : '' }}<span class="ltr-number">{{ formatAmount(c.premium_diff) }}</span>
                  </span>
                  <span v-if="c.accumulation_diff" class="change-pill" :class="c.accumulation_diff > 0 ? 'pill-up' : 'pill-down'">
                    צבירה {{ c.accumulation_diff > 0 ? '+' : '' }}<span class="ltr-number">{{ formatAmount(c.accumulation_diff) }}</span>
                  </span>
                  <span v-if="c.commission_diff" class="change-pill" :class="c.commission_diff > 0 ? 'pill-up' : 'pill-down'">
                    {{ c.commission_diff > 0 ? '▲' : '▼' }} עמלה <span class="ltr-number">{{ c.commission_diff > 0 ? '+' : '' }}{{ formatAmount(c.commission_diff) }}</span>
                  </span>
                </td>
              </tr>
              <tr v-if="!paginatedTableClients.length">
                <td :colspan="tableFilter === 'changed' ? 9 : 8" class="pc-empty">לא נמצאו תוצאות</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        <div class="pc-pagination" v-if="tableTotalPages > 1">
          <button class="pg-btn" :disabled="tablePage === 1" @click="tablePage--">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
          </button>
          <span class="pg-info ltr-number">{{ tablePage }} / {{ tableTotalPages }}</span>
          <button class="pg-btn" :disabled="tablePage === tableTotalPages" @click="tablePage++">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Filter Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="filterModal.open" class="fm-overlay" @click.self="closeModal">
          <div class="fm-card">
            <!-- List view -->
            <template v-if="!detailCustomer">
              <div class="fm-header">
                <div class="fm-header-info">
                  <span class="fm-title">{{ filterModal.title }}</span>
                  <span class="fm-count">
                    <span class="ltr-number">{{ filterModal.customers.length }}</span> לקוחות
                  </span>
                  <button
                    v-if="['removed','new','changed'].includes(filterModal.category)"
                    class="action-icon-btn"
                    title="שלח מייל"
                    @click.stop="sendFilteredMail"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
                  </button>
                  <button
                    v-if="['removed','new','changed'].includes(filterModal.category)"
                    class="action-icon-btn"
                    title="הורד לאקסל"
                    @click.stop="downloadFilteredExcel"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><polyline points="9 15 12 18 15 15"/></svg>
                  </button>
                </div>
                <button class="fm-close" @click="closeModal">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                </button>
              </div>

              <!-- Company filter pills (commission modal) -->
              <div v-if="filterModal.category === 'commission' && comparisonResult?.summary?.commission_by_company?.length > 0" class="fm-company-filter">
                <button
                  class="company-pill"
                  :class="{ active: !commissionCompanyFilter }"
                  @click="commissionCompanyFilter = null"
                >
                  הכל
                  <span class="pill-amount ltr-number">{{ formatAmount(comparisonResult.summary.commission_total) }}</span>
                </button>
                <button
                  v-for="co in comparisonResult.summary.commission_by_company"
                  :key="co.company"
                  class="company-pill"
                  :class="{ active: commissionCompanyFilter === co.company }"
                  @click="commissionCompanyFilter = co.company"
                >
                  {{ co.company }}
                  <span class="pill-amount ltr-number">{{ formatAmount(co.total) }}</span>
                  <span class="pill-count ltr-number">({{ co.clients_count }})</span>
                </button>
              </div>

              <!-- Product filter pills (commission modal - Bug 8) -->
              <div v-if="filterModal.category === 'commission' && commissionProducts.length > 1" class="fm-company-filter">
                <button class="company-pill" :class="{ active: !commissionProductFilter }" @click="commissionProductFilter = null">כל המוצרים</button>
                <button v-for="p in commissionProducts" :key="p" class="company-pill" :class="{ active: commissionProductFilter === p }" @click="commissionProductFilter = p">{{ p }}</button>
              </div>

              <!-- Company filter pills (non-commission categories - Bug 4) -->
              <div v-if="['removed','new','changed'].includes(filterModal.category) && modalCompanyBreakdown.length > 1" class="fm-company-filter">
                <button class="company-pill" :class="{ active: !categoryCompanyFilter }" @click="categoryCompanyFilter = null">
                  הכל <span class="pill-count ltr-number">({{ filterModal.customers.length }})</span>
                </button>
                <button v-for="co in modalCompanyBreakdown" :key="co.company" class="company-pill" :class="{ active: categoryCompanyFilter === co.company }" @click="categoryCompanyFilter = co.company">
                  {{ co.company }} <span class="pill-count ltr-number">({{ co.count }})</span>
                </button>
              </div>

              <!-- Filtered total -->
              <div v-if="filterModal.category === 'commission'" class="fm-filtered-total">
                <span>סה"כ עמלה:</span>
                <span class="ltr-number" style="font-weight:700;color:#ec4899">{{ formatAmount(filteredCommissionTotal) }}</span>
                <span class="ltr-number" style="color:var(--text-muted);font-size:0.82rem">({{ filteredCustomers.length }} לקוחות)</span>
              </div>

              <!-- Search -->
              <div class="fm-search-wrap">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
                <input v-model="searchQuery" class="fm-search" placeholder="חיפוש לפי שם או ת.ז." />
              </div>

              <div class="fm-table-wrap">
                <table class="fm-table">
                  <thead>
                    <tr>
                      <th v-if="filterModal.category === 'removed'" style="width:32px">
                        <input type="checkbox" :checked="allRemovedSelected" @change="toggleSelectAll" />
                      </th>
                      <th>שם</th>
                      <th>ת.ז</th>
                      <th>חברה</th>
                      <th v-if="filterModal.category === 'removed' || filterModal.category === 'new'">סוג מוצר</th>
                      <th>מוצרים</th>
                      <th>פרמיה</th>
                      <th>צבירה</th>
                      <th v-if="filterModal.category === 'changed' || filterModal.category === 'commission'">עמלה</th>
                      <th v-if="filterModal.category === 'changed'">שינוי</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="c in filteredCustomers"
                      :key="c.id_number"
                      class="fm-table-row"
                      @click="openDetail(c)"
                    >
                      <td v-if="filterModal.category === 'removed'" @click.stop>
                        <input type="checkbox" :checked="selectedRemovedIds.has(c.id_number)" @change="toggleSelected(c.id_number)" />
                      </td>
                      <td class="td-name">{{ c.name }}</td>
                      <td class="td-id"><span class="ltr-number">{{ c.id_number }}</span></td>
                      <td class="td-company" :title="c.company">{{ c.company || '—' }}</td>
                      <td v-if="filterModal.category === 'removed' || filterModal.category === 'new'">{{ c.product_types?.join(', ') || '—' }}</td>
                      <td><span class="ltr-number">{{ c.products_count }}</span></td>
                      <td>
                        <span v-if="c.premium" class="ltr-number">{{ formatAmount(c.premium) }}</span>
                        <span v-else>—</span>
                      </td>
                      <td>
                        <span v-if="c.accumulation" class="ltr-number">{{ formatAmount(c.accumulation) }}</span>
                        <span v-else>—</span>
                      </td>
                      <td v-if="filterModal.category === 'changed' || filterModal.category === 'commission'">
                        <span v-if="clientCommission(c)" class="ltr-number" style="font-weight:700;color:#ec4899">{{ formatAmount(clientCommission(c)) }}</span>
                        <span v-else>—</span>
                        <span v-if="c.commission_diff && filterModal.category === 'commission' && !commissionCompanyFilter" class="change-pill" :class="c.commission_diff > 0 ? 'pill-up' : 'pill-down'" style="margin-right:6px">
                          {{ c.commission_diff > 0 ? '▲' : '▼' }} <span class="ltr-number">{{ c.commission_diff > 0 ? '+' : '' }}{{ formatAmount(c.commission_diff) }}</span>
                        </span>
                      </td>
                      <td v-if="filterModal.category === 'changed'" class="td-changes">
                        <span v-if="c.premium_diff" class="change-pill" :class="c.premium_diff > 0 ? 'pill-up' : 'pill-down'">
                          {{ c.premium_diff > 0 ? '▲' : '▼' }} פרמיה <span class="ltr-number">{{ c.premium_diff > 0 ? '+' : '' }}{{ formatAmount(c.premium_diff) }}</span>
                        </span>
                        <span v-if="c.accumulation_diff" class="change-pill" :class="c.accumulation_diff > 0 ? 'pill-up' : 'pill-down'">
                          {{ c.accumulation_diff > 0 ? '▲' : '▼' }} צבירה <span class="ltr-number">{{ c.accumulation_diff > 0 ? '+' : '' }}{{ formatAmount(c.accumulation_diff) }}</span>
                        </span>
                      </td>
                    </tr>
                    <tr v-if="!filteredCustomers.length">
                      <td colspan="8" class="fm-empty">לא נמצאו תוצאות</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </template>

            <!-- Detail view -->
            <template v-else>
              <div class="fm-header">
                <button class="fm-back-btn" @click="detailCustomer = null">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="19" y1="12" x2="5" y2="12"/>
                    <polyline points="12 19 5 12 12 5"/>
                  </svg>
                  חזרה לרשימה
                </button>
                <button class="fm-close" @click="detailCustomer = null">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                </button>
              </div>

              <div class="detail-content">
                <!-- Customer info card -->
                <div class="detail-info-card">
                  <div class="detail-name">{{ detailCustomer.name }}</div>
                  <div class="detail-meta">
                    <span class="ltr-number">{{ detailCustomer.id_number }}</span>
                    <span class="detail-sep">·</span>
                    <span>{{ detailCustomer.company }}</span>
                  </div>
                  <div class="detail-stats">
                    <div class="detail-stat">
                      <span class="detail-stat-label">פרמיה</span>
                      <span class="detail-stat-value ltr-number">{{ formatAmount(detailCustomer.premium) }}</span>
                    </div>
                    <div class="detail-stat">
                      <span class="detail-stat-label">צבירה</span>
                      <span class="detail-stat-value ltr-number">{{ formatAmount(detailCustomer.accumulation) }}</span>
                    </div>
                    <div class="detail-stat" v-if="detailCustomer.commission || detailCustomer.commission_prev">
                      <span class="detail-stat-label">עמלה (נפרעים)</span>
                      <span class="detail-stat-value ltr-number">{{ formatAmount(detailCustomer.commission) }}</span>
                    </div>
                    <div class="detail-stat">
                      <span class="detail-stat-label">מוצרים</span>
                      <span class="detail-stat-value ltr-number">{{ detailCustomer.products_count }}</span>
                    </div>
                    <div class="detail-stat" v-if="detailCustomer.product_types?.length">
                      <span class="detail-stat-label">סוג מוצר</span>
                      <span class="detail-stat-value">{{ detailCustomer.product_types.join(', ') }}</span>
                    </div>
                  </div>
                </div>

                <!-- Changes (for changed customers) -->
                <div v-if="filterModal.category === 'changed' && detailCustomer.changes?.length" class="detail-changes">
                  <h5 class="detail-changes-title">שינויים שזוהו</h5>

                  <!-- Premium / accumulation diffs -->
                  <div v-if="detailCustomer.premium_diff || detailCustomer.accumulation_diff" class="detail-diffs-row">
                    <div v-if="detailCustomer.premium_diff" class="detail-diff-badge" :class="detailCustomer.premium_diff > 0 ? 'diff-up' : 'diff-down'">
                      <span>{{ detailCustomer.premium_diff > 0 ? '▲' : '▼' }}</span>
                      פרמיה <span class="ltr-number">{{ detailCustomer.premium_diff > 0 ? '+' : '' }}{{ formatAmount(detailCustomer.premium_diff) }}</span>
                    </div>
                    <div v-if="detailCustomer.accumulation_diff" class="detail-diff-badge" :class="detailCustomer.accumulation_diff > 0 ? 'diff-up' : 'diff-down'">
                      <span>{{ detailCustomer.accumulation_diff > 0 ? '▲' : '▼' }}</span>
                      צבירה <span class="ltr-number">{{ detailCustomer.accumulation_diff > 0 ? '+' : '' }}{{ formatAmount(detailCustomer.accumulation_diff) }}</span>
                    </div>
                  </div>

                  <!-- Changes table: old → new -->
                  <table class="changes-table">
                    <thead>
                      <tr>
                        <th class="ct-col-field">שדה</th>
                        <th class="ct-col-val">{{ previousMonthLabel }}</th>
                        <th class="ct-col-arrow"></th>
                        <th class="ct-col-val">{{ currentMonthLabel }}</th>
                        <th class="ct-col-val">הפרש</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="ch in detailCustomer.changes" :key="ch.field">
                        <td class="ct-field">{{ ch.field }}</td>
                        <td class="ct-old"><span class="ltr-number">{{ formatVal(ch.old_val) }}</span></td>
                        <td class="ct-arrow">→</td>
                        <td class="ct-new"><span class="ltr-number">{{ formatVal(ch.new_val) }}</span></td>
                        <td class="ct-diff" v-if="typeof ch.old_val === 'number'" :class="ch.new_val - ch.old_val > 0 ? 'diff-up-text' : 'diff-down-text'">
                          <span class="ltr-number">{{ ch.new_val - ch.old_val > 0 ? '+' : '' }}{{ formatVal(ch.new_val - ch.old_val) }}</span>
                        </td>
                        <td v-else class="ct-diff">—</td>
                      </tr>
                      <tr v-if="detailCustomer.commission && detailCustomer.commission_prev != null" class="ct-commission-row">
                        <td class="ct-field">עמלה</td>
                        <td class="ct-old"><span class="ltr-number">{{ formatAmount(detailCustomer.commission_prev || 0) }}</span></td>
                        <td class="ct-arrow">→</td>
                        <td class="ct-new"><span class="ltr-number ct-commission-val">{{ formatAmount(detailCustomer.commission || 0) }}</span></td>
                        <td class="ct-diff" :class="(detailCustomer.commission_diff || 0) > 0 ? 'diff-up-text' : (detailCustomer.commission_diff || 0) < 0 ? 'diff-down-text' : ''">
                          <span class="ltr-number">{{ (detailCustomer.commission_diff || 0) > 0 ? '+' : '' }}{{ formatAmount(detailCustomer.commission_diff || 0) }}</span>
                        </td>
                      </tr>
                      <!-- commission without comparison data: shown in breakdown below -->
                    </tbody>
                  </table>
                </div>

                <!-- Commission detail (for commission + changed modals) -->
                <div v-if="(filterModal.category === 'commission' || filterModal.category === 'changed') && detailCustomer.commission_details?.length" class="detail-changes">
                  <h5 class="detail-changes-title">פירוט עמלה לפי חברה</h5>

                  <!-- Per-company breakdown -->
                  <div v-if="detailCustomer.commission_details?.length" class="commission-company-breakdown">
                    <div
                      v-for="d in detailCustomer.commission_details"
                      :key="d.company"
                      class="commission-company-row"
                    >
                      <span class="commission-company-name">{{ d.company }}</span>
                      <span class="commission-company-amount ltr-number">{{ formatAmount(d.commission) }}</span>
                    </div>
                    <div v-if="detailCustomer.commission_details.length > 1" class="commission-company-row commission-total-row">
                      <span class="commission-company-name" style="font-weight:700">סה"כ</span>
                      <span class="commission-company-amount ltr-number" style="font-weight:700;color:#ec4899">{{ formatAmount(detailCustomer.commission) }}</span>
                    </div>
                  </div>

                  <!-- Diff section: show diff or "no previous data" message -->
                  <template v-if="detailCustomer.commission_diff">
                    <div class="detail-diffs-row" style="margin-top:12px">
                      <div class="detail-diff-badge" :class="detailCustomer.commission_diff > 0 ? 'diff-up' : 'diff-down'">
                        <span>{{ detailCustomer.commission_diff > 0 ? '▲' : '▼' }}</span>
                        שינוי עמלה <span class="ltr-number">{{ detailCustomer.commission_diff > 0 ? '+' : '' }}{{ formatAmount(detailCustomer.commission_diff) }}</span>
                      </div>
                    </div>
                    <table class="changes-table">
                      <thead>
                        <tr>
                          <th class="ct-col-field">שדה</th>
                          <th class="ct-col-val">{{ previousMonthLabel }}</th>
                          <th class="ct-col-arrow"></th>
                          <th class="ct-col-val">{{ currentMonthLabel }}</th>
                          <th class="ct-col-val">הפרש</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr class="ct-commission-row">
                          <td class="ct-field">עמלה</td>
                          <td class="ct-old"><span class="ltr-number">{{ formatAmount(detailCustomer.commission_prev || 0) }}</span></td>
                          <td class="ct-arrow">→</td>
                          <td class="ct-new"><span class="ltr-number ct-commission-val">{{ formatAmount(detailCustomer.commission || 0) }}</span></td>
                          <td class="ct-diff" :class="(detailCustomer.commission_diff || 0) > 0 ? 'diff-up-text' : (detailCustomer.commission_diff || 0) < 0 ? 'diff-down-text' : ''">
                            <span class="ltr-number">{{ (detailCustomer.commission_diff || 0) > 0 ? '+' : '' }}{{ formatAmount(detailCustomer.commission_diff || 0) }}</span>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </template>
                  <div v-else class="no-commission-diff-note">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>
                    </svg>
                    <span>הועלה סט נפרעים אחד — העלה נפרעים חדשים לתקופה הבאה כדי לראות השוואת עמלות</span>
                  </div>
                </div>
              </div>
            </template>
          </div>
        </div>
      </Transition>
    </Teleport>

    <Transition name="fade">
      <div v-if="clipboardNotice" class="clipboard-toast">תוכן המייל הועתק ללוח</div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import * as XLSX from 'xlsx'
import { openMailCompose } from '../../utils/mailHelper.js'
import api from '../../api/client.js'

const props = defineProps({
  history: { type: Array, default: () => [] },
  comparisonResult: { type: Object, default: null },
  comparing: { type: Boolean, default: false },
  currentFileId: { type: String, default: null },
})

const emit = defineEmits(['compare', 'reset'])

const selectedFileId = ref(null)
const searchQuery = ref('')
const detailCustomer = ref(null)
const tableFilter = ref('changed')
const tableSearch = ref('')
const tablePage = ref(1)
const tablePageSize = 30

const filterModal = reactive({
  open: false,
  title: '',
  category: '',
  customers: [],
})
const commissionCompanyFilter = ref(null) // null = all companies
const categoryCompanyFilter = ref(null) // company filter for non-commission categories
const commissionProductFilter = ref(null) // product filter for commission category
const selectedRemovedIds = ref(new Set())
const clipboardNotice = ref(false)
const companyContacts = ref([])

onMounted(async () => {
  try {
    const res = await api.get('/company-contacts')
    companyContacts.value = res.data
  } catch { /* ignore */ }
})

// Chart
const CATEGORIES = [
  { key: 'new', label: 'חדשים', color: '#10b981' },
  { key: 'removed', label: 'הוסרו', color: '#ef4444' },
  { key: 'changed', label: 'שונו', color: '#f59e0b' },
  { key: 'unchanged', label: 'ללא שינוי', color: '#94a3b8' },
]

const chartSeries = computed(() => {
  if (!props.comparisonResult) return []
  const s = props.comparisonResult.summary
  return [s.new_count, s.removed_count, s.changed_count, s.unchanged_count]
})

const chartOptions = computed(() => ({
  labels: CATEGORIES.map(c => c.label),
  colors: CATEGORIES.map(c => c.color),
  chart: {
    fontFamily: 'Heebo, sans-serif',
    animations: { enabled: true, easing: 'easeinout', speed: 800 },
    dropShadow: { enabled: true, top: 4, left: 0, blur: 12, opacity: 0.08 },
  },
  plotOptions: {
    pie: {
      expandOnClick: true,
      donut: {
        size: '58%',
        labels: {
          show: true,
          name: { fontSize: '15px', fontWeight: 700, offsetY: -4 },
          value: { fontSize: '26px', fontWeight: 800, offsetY: 4, formatter: (val) => Number(val).toLocaleString() },
          total: {
            show: true,
            label: 'סה"כ לקוחות',
            fontSize: '12px',
            fontWeight: 600,
            color: '#64748b',
            formatter: (w) => w.globals.seriesTotals.reduce((a, b) => a + b, 0).toLocaleString()
          }
        }
      }
    }
  },
  dataLabels: {
    enabled: true,
    formatter: (val) => val > 3 ? val.toFixed(0) + '%' : '',
    style: { fontSize: '12px', fontWeight: 700, colors: ['#fff'] },
    dropShadow: { enabled: true, top: 1, left: 0, blur: 2, opacity: 0.3 },
  },
  legend: {
    show: false,
  },
  stroke: { width: 3, colors: ['#fff'] },
  tooltip: {
    y: { formatter: (val) => val.toLocaleString() + ' לקוחות' }
  },
}))

// Company palette for sub-charts
const COMPANY_COLORS = [
  '#6366f1', '#06b6d4', '#f43f5e', '#8b5cf6', '#14b8a6',
  '#ec4899', '#f97316', '#0ea5e9', '#84cc16', '#a855f7',
  '#eab308', '#64748b',
]

function groupByCompany(clients) {
  const map = {}
  for (const c of clients) {
    const co = c.company || 'לא ידוע'
    map[co] = (map[co] || 0) + 1
  }
  // Sort descending
  const entries = Object.entries(map).sort((a, b) => b[1] - a[1])
  return { labels: entries.map(e => e[0]), series: entries.map(e => e[1]) }
}

function makeCompanyChartOptions(labels, colorOffset = 0) {
  return {
    labels,
    colors: labels.map((_, i) => COMPANY_COLORS[(i + colorOffset) % COMPANY_COLORS.length]),
    chart: {
      fontFamily: 'Heebo, sans-serif',
      animations: { enabled: true, easing: 'easeinout', speed: 800 },
      dropShadow: { enabled: true, top: 4, left: 0, blur: 12, opacity: 0.08 },
    },
    plotOptions: {
      pie: {
        expandOnClick: true,
        donut: {
          size: '58%',
          labels: {
            show: true,
            name: { fontSize: '14px', fontWeight: 700, offsetY: -4 },
            value: { fontSize: '24px', fontWeight: 800, offsetY: 4, formatter: (val) => Number(val).toLocaleString() },
            total: {
              show: true,
              label: 'סה"כ',
              fontSize: '11px',
              fontWeight: 600,
              color: '#64748b',
              formatter: (w) => w.globals.seriesTotals.reduce((a, b) => a + b, 0).toLocaleString()
            }
          }
        }
      }
    },
    dataLabels: {
      enabled: true,
      formatter: (val) => val > 5 ? val.toFixed(0) + '%' : '',
      style: { fontSize: '11px', fontWeight: 700, colors: ['#fff'] },
      dropShadow: { enabled: true, top: 1, left: 0, blur: 2, opacity: 0.3 },
    },
    legend: {
      show: false,
    },
    stroke: { width: 3, colors: ['#fff'] },
    tooltip: {
      y: { formatter: (val) => val.toLocaleString() + ' לקוחות' }
    },
  }
}

const newByCompany = computed(() => {
  if (!props.comparisonResult?.new_clients?.length) return { labels: [], series: [], options: {} }
  const { labels, series } = groupByCompany(props.comparisonResult.new_clients)
  return { labels, series, options: makeCompanyChartOptions(labels, 0) }
})

const removedByCompany = computed(() => {
  if (!props.comparisonResult?.removed_clients?.length) return { labels: [], series: [], options: {} }
  const { labels, series } = groupByCompany(props.comparisonResult.removed_clients)
  return { labels, series, options: makeCompanyChartOptions(labels, 4) }
})

const changedByCompany = computed(() => {
  if (!props.comparisonResult?.changed_clients?.length) return { labels: [], series: [], options: {} }
  const { labels, series } = groupByCompany(props.comparisonResult.changed_clients)
  return { labels, series, options: makeCompanyChartOptions(labels, 8) }
})

// ===== Changed Insights =====
const CHANGE_TYPES = [
  { field: 'פרמיה', label: 'פרמיה', color: '#6366f1' },
  { field: 'צבירה', label: 'צבירה', color: '#06b6d4' },
  { field: 'מוצרים', label: 'מוצרים', color: '#f59e0b' },
]

const barMode = ref('premium')

const changedInsights = computed(() => {
  const clients = props.comparisonResult?.changed_clients || []
  if (!clients.length) return { totalClients: 0, totalPremiumDiff: 0, totalAccumulationDiff: 0, premiumCount: 0, accumulationCount: 0, productCount: 0, topPremium: [], topAccumulation: [] }

  let totalPremiumDiff = 0
  let totalAccumulationDiff = 0
  let premiumCount = 0
  let accumulationCount = 0
  let productCount = 0

  for (const c of clients) {
    totalPremiumDiff += (c.premium_diff || 0)
    totalAccumulationDiff += (c.accumulation_diff || 0)
    if (c.changes?.some(ch => ch.field === 'פרמיה')) premiumCount++
    if (c.changes?.some(ch => ch.field === 'צבירה')) accumulationCount++
    if (c.changes?.some(ch => ch.field === 'מוצרים')) productCount++
  }

  const topPremium = [...clients]
    .filter(c => c.premium_diff)
    .sort((a, b) => Math.abs(b.premium_diff) - Math.abs(a.premium_diff))
    .slice(0, 10)

  const topAccumulation = [...clients]
    .filter(c => c.accumulation_diff)
    .sort((a, b) => Math.abs(b.accumulation_diff) - Math.abs(a.accumulation_diff))
    .slice(0, 10)

  return { totalClients: clients.length, totalPremiumDiff, totalAccumulationDiff, premiumCount, accumulationCount, productCount, topPremium, topAccumulation }
})

const changeTypeChartSeries = computed(() => {
  const ins = changedInsights.value
  return [ins.premiumCount, ins.accumulationCount, ins.productCount]
})

const changeTypeChartOptions = computed(() => ({
  labels: CHANGE_TYPES.map(c => c.label),
  colors: CHANGE_TYPES.map(c => c.color),
  chart: {
    fontFamily: 'Heebo, sans-serif',
    animations: { enabled: true, easing: 'easeinout', speed: 800 },
    dropShadow: { enabled: true, top: 4, left: 0, blur: 12, opacity: 0.08 },
  },
  plotOptions: {
    pie: {
      expandOnClick: true,
      donut: {
        size: '58%',
        labels: {
          show: true,
          name: { fontSize: '14px', fontWeight: 700, offsetY: -4 },
          value: { fontSize: '24px', fontWeight: 800, offsetY: 4, formatter: (val) => Number(val).toLocaleString() },
          total: {
            show: true,
            label: 'סוגי שינויים',
            fontSize: '11px',
            fontWeight: 600,
            color: '#64748b',
            formatter: (w) => w.globals.seriesTotals.reduce((a, b) => a + b, 0).toLocaleString()
          }
        }
      }
    }
  },
  dataLabels: {
    enabled: true,
    formatter: (val) => val > 5 ? val.toFixed(0) + '%' : '',
    style: { fontSize: '11px', fontWeight: 700, colors: ['#fff'] },
    dropShadow: { enabled: true, top: 1, left: 0, blur: 2, opacity: 0.3 },
  },
  legend: { show: false },
  stroke: { width: 3, colors: ['#fff'] },
  tooltip: {
    y: { formatter: (val) => val.toLocaleString() + ' לקוחות' }
  },
}))

const topChangersData = computed(() => {
  const ins = changedInsights.value
  return barMode.value === 'premium' ? ins.topPremium : ins.topAccumulation
})

const topChangersChartSeries = computed(() => {
  const data = topChangersData.value
  const diffKey = barMode.value === 'premium' ? 'premium_diff' : 'accumulation_diff'
  return [{
    name: barMode.value === 'premium' ? 'שינוי פרמיה' : 'שינוי צבירה',
    data: data.map(c => Math.round(c[diffKey] || 0)),
  }]
})

const topChangersChartOptions = computed(() => {
  const data = topChangersData.value
  const diffKey = barMode.value === 'premium' ? 'premium_diff' : 'accumulation_diff'
  const names = data.map(c => c.name || c.id_number || '---')
  return {
    chart: {
      fontFamily: 'Heebo, sans-serif',
      toolbar: { show: false },
    },
    plotOptions: {
      bar: {
        horizontal: true,
        borderRadius: 4,
        barHeight: '65%',
        distributed: true,
        colors: {
          ranges: [
            { from: -999999999, to: -0.01, color: '#ef4444' },
            { from: 0, to: 999999999, color: '#10b981' },
          ]
        }
      }
    },
    colors: data.map(c => (c[diffKey] || 0) >= 0 ? '#10b981' : '#ef4444'),
    dataLabels: {
      enabled: true,
      formatter: (val) => (val >= 0 ? '+' : '') + '₪' + Math.abs(val).toLocaleString(),
      style: { fontSize: '11px', fontWeight: 700, colors: ['#1e293b'] },
      offsetX: 6,
    },
    xaxis: {
      labels: {
        formatter: (val) => '₪' + Math.abs(Math.round(val)).toLocaleString(),
        style: { fontFamily: 'Heebo, sans-serif', fontSize: '10px' },
      }
    },
    yaxis: {
      labels: {
        style: { fontFamily: 'Heebo, sans-serif', fontSize: '11px', fontWeight: 600 },
        maxWidth: 120,
      }
    },
    labels: names,
    legend: { show: false },
    tooltip: {
      y: { formatter: (val) => (val >= 0 ? '+' : '') + '₪' + Math.abs(val).toLocaleString() }
    },
    grid: {
      borderColor: 'var(--border-subtle)',
      xaxis: { lines: { show: true } },
      yaxis: { lines: { show: false } },
    },
  }
})

// ===== Table =====
const tableTabs = computed(() => {
  const r = props.comparisonResult
  if (!r) return []
  return [
    { key: 'changed', label: 'שונו', count: r.summary.changed_count },
    { key: 'new', label: 'חדשים', count: r.summary.new_count },
    { key: 'removed', label: 'הוסרו', count: r.summary.removed_count },
  ]
})

const tableClients = computed(() => {
  const r = props.comparisonResult
  if (!r) return []
  const map = { new: r.new_clients, removed: r.removed_clients, changed: r.changed_clients }
  let list = map[tableFilter.value] || []
  const q = tableSearch.value.trim().toLowerCase()
  if (q) {
    list = list.filter(c =>
      (c.name && c.name.toLowerCase().includes(q)) ||
      (c.id_number && c.id_number.includes(q))
    )
  }
  return list
})

const tableTotalPages = computed(() => Math.ceil(tableClients.value.length / tablePageSize))
const paginatedTableClients = computed(() => {
  const start = (tablePage.value - 1) * tablePageSize
  return tableClients.value.slice(start, start + tablePageSize)
})

watch([tableFilter, tableSearch], () => { tablePage.value = 1 })

function onChangeTypeChartClick(_e, _chart, config) {
  const idx = config.dataPointIndex
  if (idx < 0) return
  openChangedByType(CHANGE_TYPES[idx].field)
}

function openCommissionFilter(type) {
  const r = props.comparisonResult
  if (!r) return
  const allClients = [...(r.new_clients || []), ...(r.removed_clients || []), ...(r.changed_clients || []), ...(r.unchanged_clients || [])]
  let filtered, title
  if (type === 'positive') {
    // Diff mode: commission went up
    filtered = allClients.filter(c => (c.commission_diff || 0) > 0.01)
    title = 'לקוחות עם עליית עמלה'
  } else if (type === 'negative') {
    // Diff mode: commission went down
    filtered = allClients.filter(c => (c.commission_diff || 0) < -0.01)
    title = 'לקוחות עם ירידת עמלה'
  } else if (type === 'has') {
    // Absolute mode: has commission
    filtered = allClients.filter(c => (c.commission || 0) > 0)
    title = 'לקוחות עם עמלה'
  } else if (type === 'zero') {
    // Absolute mode: no commission
    filtered = allClients.filter(c => (c.commission || 0) === 0)
    title = 'לקוחות ללא עמלה'
  } else {
    return
  }
  if (!filtered.length) return

  filterModal.open = true
  filterModal.title = title
  filterModal.category = 'commission'
  filterModal.customers = filtered
  searchQuery.value = ''
  detailCustomer.value = null
  commissionCompanyFilter.value = null
  commissionProductFilter.value = null
}

function openChangedByType(field) {
  const clients = props.comparisonResult?.changed_clients || []
  const filtered = clients.filter(c => c.changes?.some(ch => ch.field === field))
  if (!filtered.length) return

  filterModal.open = true
  filterModal.title = `שונו — ${field}`
  filterModal.category = 'changed'
  filterModal.customers = filtered
  searchQuery.value = ''
  detailCustomer.value = null
}

function onBarChartClick(_e, _chart, config) {
  const idx = config.dataPointIndex
  if (idx < 0) return
  const data = topChangersData.value
  if (idx < data.length) {
    openDetail(data[idx])
    // Also ensure modal is open with changed clients context
    if (!filterModal.open) {
      filterModal.open = true
      filterModal.title = 'גדולי השינויים'
      filterModal.category = 'changed'
      filterModal.customers = props.comparisonResult?.changed_clients || []
      searchQuery.value = ''
    }
  }
}

function onCompanyChartClick(category, labels, config) {
  const idx = config.dataPointIndex
  if (idx < 0) return
  const company = labels[idx]
  const r = props.comparisonResult
  if (!r) return

  const clientsMap = { new: r.new_clients, removed: r.removed_clients, changed: r.changed_clients }
  const titlesMap = { new: 'חדשים', removed: 'הוסרו', changed: 'שונו' }
  const clients = (clientsMap[category] || []).filter(c => (c.company || 'לא ידוע') === company)

  if (!clients.length) return

  filterModal.open = true
  filterModal.title = `${titlesMap[category]} — ${company}`
  filterModal.category = category
  filterModal.customers = clients
  searchQuery.value = ''
  detailCustomer.value = null
  selectedRemovedIds.value = new Set()
  categoryCompanyFilter.value = null
}

// Company breakdown for non-commission categories (Bug 4)
const modalCompanyBreakdown = computed(() => {
  if (filterModal.category === 'commission') return []
  const map = {}
  for (const c of filterModal.customers) {
    const co = c.company || 'לא ידוע'
    map[co] = (map[co] || 0) + 1
  }
  return Object.entries(map)
    .sort((a, b) => b[1] - a[1])
    .map(([company, count]) => ({ company, count }))
})

// Product list for commission category (Bug 8)
const commissionProducts = computed(() => {
  if (filterModal.category !== 'commission') return []
  const products = new Set()
  for (const c of filterModal.customers) {
    for (const d of (c.commission_details || [])) {
      if (d.company) products.add(d.company) // companies are already tracked, this is for products
    }
    // Extract actual product names from the changed_clients commission data
    for (const ch of (c.changes || [])) {
      if (ch.field) products.add(ch.field)
    }
  }
  // Actually get product_types from clients
  const prods = new Set()
  for (const c of filterModal.customers) {
    if (c.product_types) {
      for (const pt of c.product_types) prods.add(pt)
    }
  }
  return [...prods].sort()
})

const filteredCustomers = computed(() => {
  let list = filterModal.customers
  // Filter by commission company if active
  if (commissionCompanyFilter.value && filterModal.category === 'commission') {
    list = list.filter(c =>
      c.commission_details?.some(d => d.company === commissionCompanyFilter.value)
    )
  }
  // Filter by commission product if active (Bug 8)
  if (commissionProductFilter.value && filterModal.category === 'commission') {
    list = list.filter(c =>
      c.product_types?.includes(commissionProductFilter.value)
    )
  }
  // Filter by category company if active (Bug 4)
  if (categoryCompanyFilter.value && filterModal.category !== 'commission') {
    list = list.filter(c => (c.company || 'לא ידוע') === categoryCompanyFilter.value)
  }
  if (!searchQuery.value) return list
  const q = searchQuery.value.toLowerCase()
  return list.filter(c =>
    (c.name && c.name.toLowerCase().includes(q)) ||
    (c.id_number && c.id_number.includes(q))
  )
})

// Commission amount for display — respects company filter
function clientCommission(c) {
  if (!commissionCompanyFilter.value || !c.commission_details) return c.commission
  const entry = c.commission_details.find(d => d.company === commissionCompanyFilter.value)
  return entry ? entry.commission : 0
}

// Total commission for filtered view
const filteredCommissionTotal = computed(() => {
  if (filterModal.category !== 'commission') return 0
  return filteredCustomers.value.reduce((sum, c) => sum + clientCommission(c), 0)
})

function onChartClick(_e, _chart, config) {
  const idx = config.dataPointIndex
  if (idx < 0) return
  const cat = CATEGORIES[idx]
  openCategory(cat.key)
}

function openCategory(key) {
  const r = props.comparisonResult
  if (!r) return

  if (key === 'unchanged') return // no client list available

  const map = {
    new: { title: 'לקוחות חדשים', customers: r.new_clients },
    removed: { title: 'לקוחות שהוסרו', customers: r.removed_clients },
    changed: { title: 'לקוחות ששונו', customers: r.changed_clients },
  }

  const info = map[key]
  if (!info || !info.customers?.length) return

  filterModal.open = true
  filterModal.title = info.title
  filterModal.category = key
  filterModal.customers = info.customers
  searchQuery.value = ''
  detailCustomer.value = null
  selectedRemovedIds.value = new Set()
  categoryCompanyFilter.value = null
}

function openDetail(customer) {
  detailCustomer.value = customer
}

function closeModal() {
  filterModal.open = false
  detailCustomer.value = null
}

const allRemovedSelected = computed(() => {
  if (filterModal.category !== 'removed') return false
  const customers = filteredCustomers.value
  return customers.length > 0 && customers.every(c => selectedRemovedIds.value.has(c.id_number))
})

function toggleSelectAll() {
  const customers = filteredCustomers.value
  if (allRemovedSelected.value) {
    selectedRemovedIds.value = new Set()
  } else {
    selectedRemovedIds.value = new Set(customers.map(c => c.id_number))
  }
}

function toggleSelected(idNumber) {
  const next = new Set(selectedRemovedIds.value)
  if (next.has(idNumber)) {
    next.delete(idNumber)
  } else {
    next.add(idNumber)
  }
  selectedRemovedIds.value = next
}

function findCompanyEmail(companyName) {
  if (!companyName || !companyContacts.value.length) return ''
  const match = companyContacts.value.find(c =>
    companyName.includes(c.company_name) || c.company_name.includes(companyName)
  )
  return match?.email || ''
}

async function sendFilteredMail() {
  const customers = filteredCustomers.value
  const selected = (filterModal.category === 'removed' && selectedRemovedIds.value.size > 0)
    ? customers.filter(c => selectedRemovedIds.value.has(c.id_number))
    : customers
  if (!selected.length) return

  // Group by company
  const byCompany = {}
  for (const c of selected) {
    const co = c.company || 'לא ידוע'
    if (!byCompany[co]) byCompany[co] = []
    byCompany[co].push(c)
  }

  const topCompany = Object.entries(byCompany).reduce((max, cur) => cur[1].length > max[1].length ? cur : max)
  const companyName = topCompany[0]
  const clients = topCompany[1]
  const companyEmail = findCompanyEmail(companyName)

  const catLabel = filterModal.title || filterModal.category
  const lines = clients.map(c => {
    const productInfo = c.product_types?.length ? ` (${c.product_types.join(', ')})` : ''
    const premiumStr = c.premium ? ` פרמיה: ₪${Math.round(c.premium)}` : ''
    return `- ${c.name} ת.ז ${c.id_number}${productInfo}${premiumStr}`
  }).join('\n')

  const subject = `${catLabel} (${clients.length}) — ${companyName}`
  const body = `שלום רב,\n\nלהלן רשימת לקוחות — ${catLabel}:\n\n${lines}\n\nבברכה`

  const status = await openMailCompose({ to: companyEmail, subject, body })
  if (status === 'clipboard') {
    clipboardNotice.value = true
    setTimeout(() => { clipboardNotice.value = false }, 4000)
  }
}

function downloadFilteredExcel() {
  const customers = filteredCustomers.value
  if (!customers.length) return

  const rows = customers.map(c => ({
    'שם': c.name || '',
    'ת.ז': c.id_number || '',
    'חברה': c.company || '',
    'סוג מוצר': c.product_types?.join(', ') || '',
    'מוצרים': c.products_count || '',
    'פרמיה': c.premium || 0,
    'צבירה': c.accumulation || 0,
  }))

  const ws = XLSX.utils.json_to_sheet(rows)
  ws['!Dir'] = 'rtl'
  const wb = XLSX.utils.book_new()
  const sheetName = filterModal.title || filterModal.category
  XLSX.utils.book_append_sheet(wb, ws, sheetName.slice(0, 31))
  const fileName = `${sheetName.replace(/\s+/g, '_')}_${new Date().toLocaleDateString('he-IL')}.xlsx`
  XLSX.writeFile(wb, fileName)
}

function runCompare() {
  if (selectedFileId.value && props.currentFileId) {
    emit('compare', props.currentFileId, selectedFileId.value)
  }
}

function formatDate(dateStr) {
  const d = new Date(dateStr)
  return d.toLocaleDateString('he-IL', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

// Extract month label from production filename (e.g., "דוח פרודוקציה פברואר 26.xlsx" → "פברואר 26")
function extractMonthLabel(filename) {
  if (!filename) return ''
  const match = filename.replace('.xlsx', '').replace('.xls', '')
    .replace('דוח פרודוקציה', '').trim()
  return match || filename
}

const currentMonthLabel = computed(() =>
  extractMonthLabel(props.comparisonResult?.summary?.current_filename) || 'חדש'
)
const previousMonthLabel = computed(() =>
  extractMonthLabel(props.comparisonResult?.summary?.previous_filename) || 'ישן'
)

function formatAmount(val) {
  if (!val || val === 0) return '₪0'
  const num = Math.round(val)
  if (num < 0) return '-₪' + Math.abs(num).toLocaleString()
  return '₪' + num.toLocaleString()
}

function formatVal(val) {
  if (typeof val === 'number') return formatAmount(val)
  return val
}
</script>

<style scoped>
.prod-comparison {
  animation: slideUp 0.4s var(--transition);
}

.empty-state {
  text-align: center;
  padding: 48px 24px;
  color: var(--text-muted);
}

.empty-state svg { margin-bottom: 12px; opacity: 0.3; }
.empty-state p { font-size: 14px; }

/* Selector */
.selector-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.selector-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
}

.history-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  background: var(--card-bg);
  border: 1.5px solid var(--border-subtle);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.25s var(--transition);
}

.history-card:hover {
  border-color: var(--border);
  background: var(--bg-surface);
}

.history-card.selected {
  border-color: var(--primary);
  background: var(--primary-light);
}

.hc-radio {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: border-color 0.2s;
}

.history-card.selected .hc-radio {
  border-color: var(--primary);
}

.hc-radio-inner {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--primary);
}

.hc-info { display: flex; flex-direction: column; gap: 2px; }
.hc-name { font-size: 13px; font-weight: 600; color: var(--text); word-break: break-all; }
.hc-meta { font-size: 11px; color: var(--text-muted); }

.btn-compare {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 12px 28px;
  background: var(--primary);
  color: white;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 700;
  font-family: inherit;
  align-self: flex-start;
  transition: all 0.3s var(--transition);
}

.btn-compare:hover:not(:disabled) {
  transform: translateY(-2px);
  background: var(--primary-deep);
  box-shadow: 0 8px 24px rgba(245, 124, 0, 0.2);
}

.btn-compare:disabled { opacity: 0.4; cursor: not-allowed; }

/* Loading */
.loading-state {
  text-align: center;
  padding: 48px;
  color: var(--text-secondary);
  font-size: 14px;
}

.loader {
  width: 36px;
  height: 36px;
  position: relative;
  margin: 0 auto 14px;
}

.loader-ring {
  position: absolute;
  inset: 0;
  border: 2px solid transparent;
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.loader-ring.delay {
  inset: 5px;
  border-top-color: var(--accent-cyan);
  animation-duration: 1.5s;
  animation-direction: reverse;
}

/* Results */
.results-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.results-header h4 {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
}

.btn-back {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  color: var(--text-muted);
  border: 1px solid var(--border);
  border-radius: 8px;
  transition: all 0.2s;
}

.btn-back:hover {
  color: var(--text);
  background: var(--bg-surface);
}

/* Summary strip */
.summary-strip {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.summary-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.summary-badge:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.summary-badge.badge-gray {
  cursor: default;
}

.summary-badge.badge-gray:hover {
  transform: none;
  box-shadow: none;
}

.badge-green { background: var(--green-light); color: var(--accent-emerald); }
.badge-red { background: var(--red-light); color: var(--red); }
.badge-amber { background: var(--amber-light); color: var(--amber); }
.badge-gray { background: var(--border-subtle); color: var(--text-muted); }

/* Chart card */
.chart-card {
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg, 16px);
  padding: 28px 24px 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.chart-title-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 4px;
  padding: 0 4px;
}

.chart-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
}

.chart-subtitle {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
}

/* Custom legend */
.chart-legend {
  display: flex;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 8px;
  padding: 0 8px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 10px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  transition: all 0.2s;
}

.legend-item.clickable {
  cursor: pointer;
}

.legend-item.clickable:hover {
  border-color: var(--border);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
}

.legend-value {
  font-size: 13px;
  font-weight: 800;
  color: var(--text);
}

/* Charts grid */
.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

@media (max-width: 700px) {
  .charts-grid { grid-template-columns: 1fr; }
}

.chart-card-half {
  padding: 20px 16px 12px;
}

.chart-badge {
  font-size: 11px;
  font-weight: 700;
  padding: 2px 10px;
  border-radius: 8px;
}

/* ===== Changed Insights Section ===== */
.changed-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.changed-section-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.changed-section-title {
  font-size: 16px;
  font-weight: 800;
  color: var(--text);
}

.changed-kpi-strip {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.changed-kpi {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 14px 20px;
  border-radius: 12px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  flex: 1;
  min-width: 110px;
  transition: all 0.2s;
}

.changed-kpi.kpi-clickable {
  cursor: pointer;
}

.changed-kpi.kpi-clickable:hover {
  border-color: var(--border);
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
}

.changed-kpi.kpi-green { border-color: rgba(16, 185, 129, 0.25); background: rgba(16, 185, 129, 0.06); }
.changed-kpi.kpi-red { border-color: rgba(239, 68, 68, 0.25); background: rgba(239, 68, 68, 0.06); }

.changed-kpi-value {
  font-size: 18px;
  font-weight: 800;
  color: var(--text);
}

.kpi-green .changed-kpi-value { color: var(--accent-emerald); }
.kpi-red .changed-kpi-value { color: var(--red); }

.changed-kpi-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
}

.changed-kpi.kpi-pink { border-color: rgba(236, 72, 153, 0.25); background: rgba(236, 72, 153, 0.06); }
.kpi-pink .changed-kpi-value { color: #ec4899; }

.kpi-split {
  display: flex;
  gap: 8px;
  margin-top: 2px;
  font-size: 11px;
  font-weight: 600;
}

.kpi-split-up { color: var(--accent-emerald); }
.kpi-split-down { color: var(--red); }
.kpi-split-clickable { cursor: pointer; border-radius: 4px; padding: 1px 4px; transition: background 0.15s; }
.kpi-split-clickable:hover { background: rgba(0,0,0,0.06); }

.no-commission-note {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  font-size: 12px;
  color: var(--text-muted);
  background: var(--bg-surface);
  border-radius: var(--radius-md);
  border: 1px dashed var(--border-subtle);
}

/* Bar chart toggle */
.bar-toggle {
  display: flex;
  gap: 2px;
  background: var(--bg-surface);
  border-radius: 8px;
  padding: 2px;
  border: 1px solid var(--border-subtle);
}

.bar-toggle-btn {
  padding: 4px 14px;
  font-size: 11px;
  font-weight: 600;
  font-family: inherit;
  color: var(--text-muted);
  border-radius: 6px;
  transition: all 0.2s;
}

.bar-toggle-btn.active {
  background: var(--card-bg);
  color: var(--text);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.bar-toggle-btn:not(.active):hover {
  color: var(--text-secondary);
}

/* ===== Filter Modal ===== */
.fm-overlay {
  position: fixed;
  inset: 0;
  z-index: 1010;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.fm-card {
  background: var(--card-bg, #fff);
  border-radius: var(--radius-lg, 16px);
  width: 100%;
  max-width: 820px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.18);
}

.fm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.fm-header-info {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.fm-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
}

.fm-count {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
}

.fm-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  color: var(--text-muted);
  transition: all 0.2s;
  flex-shrink: 0;
}

.fm-close:hover {
  background: var(--bg-surface);
  color: var(--text);
}

.fm-back-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  color: var(--primary);
  transition: opacity 0.2s;
}

.fm-back-btn:hover { opacity: 0.7; }

/* Search */
.fm-company-filter {
  display: flex;
  gap: 6px;
  padding: 12px 22px 0;
  flex-wrap: wrap;
  flex-shrink: 0;
}

.company-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 12px;
  border-radius: 20px;
  border: 1.5px solid var(--border-subtle, #e2e8f0);
  background: var(--card-bg, #fff);
  cursor: pointer;
  font-size: 12.5px;
  font-family: inherit;
  color: var(--text-secondary, #64748b);
  transition: all 0.15s ease;
}
.company-pill:hover { border-color: #ec4899; color: #ec4899; }
.company-pill.active {
  background: #ec4899;
  border-color: #ec4899;
  color: #fff;
}
.company-pill .pill-amount { font-weight: 700; font-size: 11.5px; }
.company-pill .pill-count { font-size: 10.5px; opacity: 0.7; }
.company-pill.active .pill-amount,
.company-pill.active .pill-count { color: #fff; }

.fm-filtered-total {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 22px;
  font-size: 13px;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.commission-company-breakdown {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: 4px;
}

.commission-company-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 7px 14px;
  border-radius: 8px;
  background: rgba(236, 72, 153, 0.04);
}

.commission-company-name { font-size: 13.5px; color: var(--text); }
.commission-company-amount { font-size: 13.5px; font-weight: 600; color: #ec4899; }

.commission-total-row {
  margin-top: 4px;
  border-top: 1px solid var(--border-subtle);
  padding-top: 9px;
  background: transparent;
}

.no-commission-diff-note {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  margin-top: 8px;
  border-radius: 8px;
  background: rgba(245, 158, 11, 0.06);
  border: 1px solid rgba(245, 158, 11, 0.15);
  color: #92400e;
  font-size: 12.5px;
  line-height: 1.5;
}
.no-commission-diff-note svg { flex-shrink: 0; color: #f59e0b; }

.kpi-no-diff-note {
  display: block;
  font-size: 10.5px;
  color: #92400e;
  background: rgba(245, 158, 11, 0.08);
  padding: 3px 8px;
  border-radius: 6px;
  margin-top: 4px;
  text-align: center;
}

.fm-search-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 22px;
  border-bottom: 1px solid var(--border-subtle);
  flex-shrink: 0;
}

.fm-search-wrap svg { color: var(--text-muted); flex-shrink: 0; }

.fm-search {
  flex: 1;
  border: none;
  outline: none;
  font-size: 13px;
  font-family: inherit;
  color: var(--text);
  background: transparent;
}

.fm-search::placeholder { color: var(--text-muted); }

/* List */
.fm-table-wrap {
  overflow: auto;
  flex: 1;
  padding: 0 22px;
}

.fm-table {
  width: 100%;
  min-width: 600px;
  border-collapse: collapse;
  font-size: 13px;
}

.fm-table th {
  padding: 10px 10px;
  text-align: right;
  font-weight: 700;
  font-size: 11px;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-subtle);
  white-space: nowrap;
  position: sticky;
  top: 0;
  background: var(--card-bg);
  z-index: 1;
}

.fm-table td {
  padding: 10px 10px;
  border-bottom: 1px solid var(--border-subtle);
  white-space: nowrap;
}

.fm-table-row {
  cursor: pointer;
  transition: background 0.15s;
}

.fm-table-row:hover { background: var(--bg-surface); }

.fm-table .td-name { font-weight: 600; }
.fm-table .td-id { font-size: 12px; color: var(--text-muted); }
.fm-table .td-company { font-size: 12px; max-width: 140px; overflow: hidden; text-overflow: ellipsis; }
.fm-table .td-changes { display: flex; gap: 4px; flex-wrap: nowrap; }

.fm-table .change-pill {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px 6px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 600;
  white-space: nowrap;
}

.fm-table .pill-up { background: rgba(16, 185, 129, 0.1); color: #10b981; }
.fm-table .pill-down { background: rgba(239, 68, 68, 0.1); color: #ef4444; }

.fm-empty {
  padding: 32px;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
}

/* ===== Detail view ===== */
.detail-content {
  padding: 22px;
  overflow-y: auto;
  flex: 1;
}

.detail-info-card {
  background: var(--bg-surface);
  border-radius: var(--radius-md);
  padding: 20px;
  margin-bottom: 20px;
}

.detail-name {
  font-size: 18px;
  font-weight: 800;
  color: var(--text);
  margin-bottom: 4px;
}

.detail-meta {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 16px;
}

.detail-sep { margin: 0 6px; }

.detail-stats {
  display: flex;
  gap: 24px;
}

.detail-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.detail-stat-label {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
}

.detail-stat-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
}

/* Changes section */
.detail-changes {
  margin-top: 4px;
}

.detail-changes-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 12px;
}

.detail-diffs-row {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.detail-diff-badge {
  font-size: 12px;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 8px;
}

.diff-up { background: var(--green-light); color: var(--accent-emerald); }
.diff-down { background: var(--red-light); color: var(--red); }

.changes-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  margin-top: 4px;
}

.changes-table th,
.changes-table td {
  padding: 10px 10px;
  text-align: right;
  white-space: nowrap;
}

.changes-table th {
  font-weight: 700;
  font-size: 11px;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-subtle);
}

.changes-table td {
  border-bottom: 1px solid var(--border-subtle);
}

.ct-col-field { width: 60px; }
.ct-col-arrow { width: 28px; }
.ct-col-val { min-width: 90px; }

.ct-field { font-weight: 600; color: var(--text); }
.ct-old { color: var(--text-muted); }
.ct-new { color: var(--text); font-weight: 600; }
.ct-arrow { text-align: center; color: var(--text-muted); padding: 10px 4px; font-size: 12px; }
.ct-diff { font-weight: 700; font-size: 12px; }
.diff-up-text { color: var(--accent-emerald); }
.diff-down-text { color: var(--red); }

.ct-commission-row { background: rgba(236, 72, 153, 0.04); }
.ct-commission-info {
  display: flex;
  align-items: center;
  gap: 10px;
}
.ct-commission-note {
  color: var(--text-muted);
  font-size: 0.78rem;
}
.ct-commission-val { font-weight: 700; color: #ec4899; }
.ct-commission-note { font-size: 11px; color: var(--text-muted); margin-right: 6px; }

.detail-val-new {
  font-size: 13px;
  color: var(--accent-emerald);
  font-weight: 600;
}

/* ===== Modal transition ===== */
.modal-enter-active { animation: modalIn 0.25s ease; }
.modal-leave-active { animation: modalIn 0.2s ease reverse; }

@keyframes modalIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-enter-active .fm-card { animation: cardIn 0.25s ease; }
.modal-leave-active .fm-card { animation: cardIn 0.2s ease reverse; }

@keyframes cardIn {
  from { opacity: 0; transform: scale(0.95) translateY(10px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

/* Collapse transition (kept for potential reuse) */
.collapse-enter-active { animation: collapseIn 0.25s ease; }
.collapse-leave-active { animation: collapseIn 0.2s ease reverse; }

@keyframes collapseIn {
  from { opacity: 0; max-height: 0; }
  to { opacity: 1; max-height: 2000px; }
}

.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
  display: inline-block;
}

/* Comparison context */
.compare-context {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  margin-bottom: 8px;
}

.compare-file {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.cf-label {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  padding: 2px 6px;
  border-radius: 4px;
  white-space: nowrap;
}

.compare-file-current .cf-label {
  background: rgba(16, 185, 129, 0.12);
  color: #10b981;
}

.compare-file-previous .cf-label {
  background: rgba(148, 163, 184, 0.15);
  color: #94a3b8;
}

.cf-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}

.cf-date {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
}

.compare-arrow {
  color: var(--text-muted);
  flex-shrink: 0;
}

/* ===== Clients Table ===== */
.clients-table-section {
  margin-top: 24px;
}

.table-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 10px;
}

.table-section-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
}

.table-filter-tabs {
  display: flex;
  gap: 4px;
  background: var(--bg-surface);
  padding: 3px;
  border-radius: 10px;
  border: 1px solid var(--border-subtle);
}

.table-tab {
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  border-radius: 8px;
  color: var(--text-muted);
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}

.table-tab:hover { color: var(--text); }
.table-tab.active {
  background: var(--card-bg);
  color: var(--text);
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}

.table-tab b { color: var(--primary); }

.table-search-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  margin-bottom: 12px;
}

.table-search-wrap svg { color: var(--text-muted); flex-shrink: 0; }

.table-search {
  border: none;
  background: transparent;
  font-family: inherit;
  font-size: 13px;
  color: var(--text);
  width: 100%;
  outline: none;
}

.tbl-wrap {
  overflow-x: auto;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
}

.pc-table {
  min-width: 800px;
  border-collapse: collapse;
  font-size: 13px;
}

.pc-table th,
.pc-table td {
  padding: 10px 10px;
  text-align: right;
  white-space: nowrap;
}

.pc-table th {
  font-weight: 700;
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-subtle);
}

.pc-table td {
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text);
}

.pc-row {
  cursor: pointer;
  transition: background 0.15s;
}

.pc-row:hover { background: var(--bg-surface); }

.pc-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.dot-new { background: #10b981; }
.dot-removed { background: #ef4444; }
.dot-changed { background: #f59e0b; }

.td-name { font-weight: 600; }
.td-id { font-size: 12px; color: var(--text-muted); }
.td-company { font-size: 12px; max-width: 150px; overflow: hidden; text-overflow: ellipsis; }

.td-changes {
  display: flex;
  gap: 4px;
  flex-wrap: nowrap;
}

.change-pill {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px 6px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 600;
  white-space: nowrap;
}

.pill-up { background: rgba(16, 185, 129, 0.1); color: #10b981; }
.pill-down { background: rgba(239, 68, 68, 0.1); color: #ef4444; }

.pc-empty {
  text-align: center;
  padding: 24px;
  color: var(--text-muted);
  font-size: 13px;
}

.pc-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 12px 0;
}

.pg-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
  background: var(--card-bg);
  color: var(--text-muted);
  font-family: inherit;
  transition: all 0.2s;
}

.pg-btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary); }
.pg-btn:disabled { opacity: 0.3; cursor: not-allowed; }

.pg-info { font-size: 12px; color: var(--text-muted); font-weight: 600; }

.action-icon-btn {
  display: inline-flex; align-items: center; justify-content: center;
  width: 28px; height: 28px; border-radius: 6px;
  border: none; background: var(--bg-alt, #f1f5f9); color: var(--text-muted);
  cursor: pointer; transition: all 0.15s;
  margin-right: 8px;
}
.action-icon-btn:hover { background: var(--primary); color: #fff; }

.clipboard-toast {
  position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
  background: #1e293b; color: #fff; padding: 10px 20px; border-radius: 8px;
  font-size: 13px; z-index: 9999; box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
