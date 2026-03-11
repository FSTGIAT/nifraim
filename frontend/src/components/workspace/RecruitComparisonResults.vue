<template>
  <div class="comparison-results glass-card">
    <div class="results-header">
      <div class="header-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
        </svg>
        <h3>תוצאות בדיקה</h3>
      </div>
      <button class="btn-close" @click="recruitsStore.resetComparison()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18"/>
          <line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
    </div>

    <!-- Chart + KPI row -->
    <div class="dashboard-row">
      <div class="chart-box">
        <apexchart
          v-if="chartReady"
          type="donut"
          :options="chartOptions"
          :series="chartSeries"
          height="240"
        />
      </div>
      <div class="kpi-row">
        <div class="kpi found-kpi" @click="activeFilter = 'found'">
          <span class="kpi-num ltr-number">{{ result.found }}</span>
          <span class="kpi-lbl">נמצאו</span>
          <span class="kpi-pct ltr-number">{{ foundPct }}%</span>
        </div>
        <div class="kpi missing-kpi" @click="showMissingModal = true">
          <span class="kpi-num ltr-number">{{ result.not_found }}</span>
          <span class="kpi-lbl">לא נמצאו</span>
          <span class="kpi-pct ltr-number">{{ missingPct }}%</span>
        </div>
        <div class="kpi total-kpi" @click="activeFilter = 'all'">
          <span class="kpi-num ltr-number">{{ result.total }}</span>
          <span class="kpi-lbl">סה"כ</span>
        </div>
      </div>
    </div>

    <!-- ── Insights Section ── -->
    <div class="insights-section">
      <!-- Enhanced KPI Row (5 cards) -->
      <div class="insights-kpi-row">
        <div class="ins-kpi ins-kpi-green">
          <span class="ins-kpi-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>
          </span>
          <span class="ins-kpi-val ltr-number">₪{{ fmtNum(result.total_premium_found || 0) }}</span>
          <span class="ins-kpi-lbl">פרמיה שנמצאה</span>
        </div>
        <div class="ins-kpi ins-kpi-orange">
          <span class="ins-kpi-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          </span>
          <span class="ins-kpi-val ltr-number">₪{{ fmtNum(result.estimated_missing_premium || 0) }}</span>
          <span class="ins-kpi-lbl">פרמיה חסרה (הערכה)</span>
        </div>
        <div class="ins-kpi ins-kpi-cyan">
          <span class="ins-kpi-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
          </span>
          <span class="ins-kpi-val ltr-number">{{ fmtNum(result.active_product_rate || 0) }}%</span>
          <span class="ins-kpi-lbl">מוצרים פעילים</span>
        </div>
        <div class="ins-kpi ins-kpi-violet">
          <span class="ins-kpi-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v16"/></svg>
          </span>
          <span class="ins-kpi-val ltr-number">{{ avgProductsPerClient }}</span>
          <span class="ins-kpi-lbl">מוצרים ממוצע ללקוח</span>
        </div>
        <div class="ins-kpi ins-kpi-primary">
          <span class="ins-kpi-icon">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
          </span>
          <span class="ins-kpi-val ltr-number">{{ foundPct }}%</span>
          <span class="ins-kpi-lbl">שיעור המרה</span>
        </div>
      </div>

      <!-- Three-column: Company bar + Product donut + Status donut -->
      <div class="insights-charts-row insights-charts-row-3" v-if="hasCompanyData || hasProductData || hasStatusData">
        <div class="ins-chart-box ins-chart-clickable" v-if="hasCompanyData">
          <div class="ins-chart-title">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>
            פילוח לפי חברה
            <span class="chart-click-hint">לחץ לפירוט</span>
          </div>
          <apexchart
            v-if="chartReady"
            type="bar"
            :options="companyChartOptions"
            :series="companyChartSeries"
            :height="Math.max(160, (result.company_breakdown || []).length * 38)"
          />
        </div>
        <div class="ins-chart-box ins-chart-clickable" v-if="hasProductData">
          <div class="ins-chart-title">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/></svg>
            פילוח לפי מוצר
            <span class="chart-click-hint">לחץ לפירוט</span>
          </div>
          <apexchart
            v-if="chartReady"
            type="donut"
            :options="productChartOptions"
            :series="productChartSeries"
            height="220"
          />
        </div>
        <div class="ins-chart-box" v-if="hasStatusData">
          <div class="ins-chart-title">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            סטטוס מוצרים שנמצאו
          </div>
          <apexchart
            v-if="chartReady"
            type="donut"
            :options="statusChartOptions"
            :series="statusChartSeries"
            height="220"
          />
        </div>
      </div>

      <!-- Top Missing Clients -->
      <div class="ins-missing-table" v-if="topMissing.length > 0">
        <div class="ins-chart-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          לקוחות חסרים מובילים
        </div>
        <table class="mini-tbl">
          <thead>
            <tr>
              <th>שם</th>
              <th>ת.ז</th>
              <th>חברה</th>
              <th>מוצר</th>
              <th>סכום</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in topMissing" :key="m.recruit_id" @click="openDetail(m)">
              <td class="td-name">{{ m.first_name }} {{ m.last_name }}</td>
              <td class="td-id ltr-number">{{ m.id_number }}</td>
              <td>{{ m.company || '—' }}</td>
              <td>{{ m.product || '—' }}</td>
              <td class="ltr-number" style="font-weight:700;color:var(--primary)">
                <template v-if="m.amount > 0">₪{{ fmtNum(m.amount) }}</template>
                <template v-else>—</template>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Actionable Summary Card -->
      <div class="ins-summary-card" v-if="summaryBullets.length > 0">
        <div class="ins-chart-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18l6-6-6-6"/></svg>
          המלצות לפעולה
          <span class="action-btns">
            <button class="action-icon-btn" title="שלח מייל על חסרים" @click.stop="sendMissingMail">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
            </button>
            <button class="action-icon-btn" title="הורד Excel חסרים" @click.stop="downloadMissingExcel">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            </button>
          </span>
        </div>
        <ul class="summary-bullets">
          <li v-for="(b, i) in summaryBullets" :key="i" v-html="b"></li>
        </ul>
      </div>
    </div>

    <!-- Segmented filter -->
    <div class="seg-filter">
      <button :class="{ active: activeFilter === 'all' }" @click="activeFilter = 'all'">הכל <b>{{ result.total }}</b></button>
      <button :class="{ active: activeFilter === 'found' }" @click="activeFilter = 'found'">נמצאו <b>{{ result.found }}</b></button>
      <button :class="{ active: activeFilter === 'not_found' }" @click="activeFilter = 'not_found'">לא נמצאו <b>{{ result.not_found }}</b></button>
    </div>

    <!-- Company & Product filters -->
    <div class="slice-filters">
      <div class="slice-filter">
        <label>חברה</label>
        <select v-model="companyFilter">
          <option value="">הכל ({{ uniqueCompanies.length }})</option>
          <option v-for="c in uniqueCompanies" :key="c" :value="c">{{ c }}</option>
        </select>
      </div>
      <div class="slice-filter">
        <label>מוצר</label>
        <select v-model="productFilter">
          <option value="">הכל ({{ uniqueProducts.length }})</option>
          <option v-for="p in uniqueProducts" :key="p" :value="p">{{ p }}</option>
        </select>
      </div>
      <button v-if="companyFilter || productFilter" class="slice-clear" @click="companyFilter = ''; productFilter = ''">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        נקה סינון
      </button>
      <span class="slice-count" v-if="companyFilter || productFilter">{{ filteredResults.length }} תוצאות</span>
    </div>

    <!-- Results table -->
    <div class="tbl-wrap">
      <table class="tbl">
        <thead>
          <tr>
            <th class="th-status"></th>
            <th>שם</th>
            <th>ת.ז</th>
            <th>חברה</th>
            <th>מוצר</th>
            <th>מוצרים בפרודוקציה</th>
            <th>פרמיה</th>
            <th>סטטוס לקוח</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="item in paginatedResults"
            :key="item.recruit_id"
            class="tbl-row"
            :class="{ 'row-found': item.found_in_production, 'row-missing': !item.found_in_production }"
            @click="openDetail(item)"
          >
            <td class="td-status">
              <span v-if="item.found_in_production" class="dot dot-found"></span>
              <span v-else class="dot dot-missing"></span>
            </td>
            <td class="td-name">{{ item.first_name }} {{ item.last_name }}</td>
            <td class="td-id ltr-number">{{ item.id_number }}</td>
            <td class="td-company">{{ item.company || '—' }}</td>
            <td class="td-product">{{ item.product || '—' }}</td>
            <td class="td-prod-count ltr-number">
              <span v-if="item.found_in_production" class="prod-badge">{{ item.production_products.length }}</span>
              <span v-else class="prod-badge prod-badge-zero">0</span>
            </td>
            <td class="td-premium ltr-number">
              <template v-if="item.production_premium > 0">₪{{ fmtNum(item.production_premium) }}</template>
              <template v-else>—</template>
            </td>
            <td class="td-customer-status" @click.stop>
              <div v-if="!item.found_in_production" class="status-select-wrap">
                <select
                  class="status-select"
                  :class="customerStatusClass(customerStatuses[item.recruit_id])"
                  :value="customerStatuses[item.recruit_id] || ''"
                  @change="onStatusChange(item.recruit_id, $event)"
                >
                  <option value="">בחר סטטוס...</option>
                  <option value="עבר סוכן">עבר סוכן</option>
                  <option value="משך את הכסף">משך את הכסף</option>
                  <option value="__custom__">אחר (הקלד)...</option>
                </select>
                <input
                  v-if="customInputId === item.recruit_id"
                  class="status-custom-input"
                  v-model="customInputVal"
                  placeholder="הקלד סטטוס..."
                  @keydown.enter="confirmCustomStatus(item.recruit_id)"
                  @blur="confirmCustomStatus(item.recruit_id)"
                  ref="customInputRef"
                />
              </div>
              <span v-else class="status-found-label">בפרודוקציה</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div class="pagination" v-if="totalPages > 1">
      <button class="pg" :disabled="currentPage === 1" @click="currentPage--">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
      </button>
      <template v-for="p in visiblePages" :key="p">
        <span v-if="p === '...'" class="pg-dots">...</span>
        <button v-else class="pg" :class="{ active: p === currentPage }" @click="currentPage = p">{{ p }}</button>
      </template>
      <button class="pg" :disabled="currentPage === totalPages" @click="currentPage++">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
      </button>
      <span class="pg-info">{{ currentPage }} / {{ totalPages }}</span>
    </div>

    <!-- Detail Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="detailItem" class="modal-overlay" @click.self="detailItem = null">
          <div class="modal-card">
            <div class="modal-head">
              <button class="modal-x" @click="detailItem = null">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
              <div class="modal-id-row">
                <div>
                  <div class="modal-name">{{ detailItem.first_name }} {{ detailItem.last_name }}</div>
                  <div class="modal-id-num ltr-number">ת.ז {{ detailItem.id_number }}</div>
                </div>
                <span class="modal-status-chip" :class="detailItem.found_in_production ? 'chip-found' : 'chip-missing'">
                  {{ detailItem.found_in_production ? 'נמצא בפרודוקציה' : 'לא נמצא' }}
                </span>
              </div>
            </div>

            <!-- Recruit file data -->
            <div class="modal-section">
              <div class="section-title">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                נתוני קובץ גיוס
              </div>
              <div class="info-grid">
                <div class="info-cell" v-if="detailItem.company">
                  <span class="info-lbl">חברה</span>
                  <span class="info-val">{{ detailItem.company }}</span>
                </div>
                <div class="info-cell" v-if="detailItem.product">
                  <span class="info-lbl">מוצר</span>
                  <span class="info-val">{{ detailItem.product }}</span>
                </div>
                <div class="info-cell" v-if="detailItem.amount > 0">
                  <span class="info-lbl">סכום</span>
                  <span class="info-val ltr-number">₪{{ fmtNum(detailItem.amount) }}</span>
                </div>
              </div>
            </div>

            <!-- Production data -->
            <div class="modal-section" v-if="detailItem.found_in_production && detailItem.production_products.length">
              <div class="section-title">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                מוצרים בפרודוקציה
                <span class="section-count">{{ detailItem.production_products.length }}</span>
              </div>
              <div class="prod-table-wrap">
                <table class="prod-table">
                  <thead>
                    <tr>
                      <th>מוצר</th>
                      <th>חברה</th>
                      <th>סטטוס</th>
                      <th>פרמיה</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(p, i) in detailItem.production_products" :key="i">
                      <td class="pt-product">{{ p.product || p.product_type || '—' }}</td>
                      <td class="pt-company">{{ shortCompany(p.company) || '—' }}</td>
                      <td>
                        <span class="status-tag" :class="statusClass(p.status)">{{ statusLabel(p.status) }}</span>
                      </td>
                      <td class="pt-premium ltr-number">
                        <template v-if="p.premium > 0">₪{{ fmtNum(p.premium) }}</template>
                        <template v-else>—</template>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- Total premium -->
              <div class="modal-total" v-if="detailItem.production_premium > 0">
                <span>סה"כ פרמיה חודשית</span>
                <strong class="ltr-number">₪{{ fmtNum(detailItem.production_premium) }}</strong>
              </div>
            </div>

            <!-- Not found message -->
            <div class="modal-section modal-empty" v-if="!detailItem.found_in_production">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>
              <p>לקוח זה לא נמצא בקובץ הפרודוקציה</p>
              <span>יש לוודא שהלקוח קיים במערכת או שת.ז תקין</span>

              <div class="modal-status-edit" @click.stop>
                <label class="modal-status-label">סטטוס לקוח:</label>
                <select
                  class="status-select"
                  :class="customerStatusClass(customerStatuses[detailItem.recruit_id])"
                  :value="customerStatuses[detailItem.recruit_id] || ''"
                  @change="onStatusChange(detailItem.recruit_id, $event)"
                >
                  <option value="">בחר סטטוס...</option>
                  <option value="עבר סוכן">עבר סוכן</option>
                  <option value="משך את הכסף">משך את הכסף</option>
                  <option value="__custom__">אחר (הקלד)...</option>
                </select>
                <input
                  v-if="customInputId === detailItem.recruit_id"
                  class="status-custom-input"
                  v-model="customInputVal"
                  placeholder="הקלד סטטוס..."
                  @keydown.enter="confirmCustomStatus(detailItem.recruit_id)"
                  @blur="confirmCustomStatus(detailItem.recruit_id)"
                />
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Missing Customers Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="showMissingModal" class="modal-overlay" @click.self="showMissingModal = false">
          <div class="modal-card missing-modal-card">
            <div class="modal-head">
              <button class="modal-x" @click="showMissingModal = false">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
              <div class="modal-id-row">
                <div>
                  <div class="modal-name">לקוחות שלא נמצאו בפרודוקציה</div>
                  <div class="modal-id-num">{{ notFoundList.length }} לקוחות</div>
                </div>
                <span class="modal-status-chip chip-missing">לא נמצאו</span>
              </div>
            </div>

            <!-- Search -->
            <div class="mm-search-wrap">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              <input class="mm-search" v-model="missingSearch" placeholder="חיפוש לפי שם או ת.ז..." />
            </div>

            <!-- Action buttons -->
            <div class="mm-actions">
              <button class="mm-action-btn" @click="downloadMissingExcel(); showMissingModal = false">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                הורד Excel
              </button>
              <button class="mm-action-btn" @click="sendMissingMail(); showMissingModal = false">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
                שלח מייל
              </button>
            </div>

            <!-- Table -->
            <div class="mm-table-wrap">
              <table class="mm-table">
                <thead>
                  <tr>
                    <th>שם</th>
                    <th>ת.ז</th>
                    <th>חברה</th>
                    <th>מוצר</th>
                    <th>סכום</th>
                    <th>סטטוס</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="item in filteredMissingList"
                    :key="item.recruit_id"
                    class="mm-row"
                    @click="showMissingModal = false; openDetail(item)"
                  >
                    <td class="td-name">{{ item.first_name }} {{ item.last_name }}</td>
                    <td class="td-id ltr-number">{{ item.id_number }}</td>
                    <td>{{ item.company || '—' }}</td>
                    <td>{{ item.product || '—' }}</td>
                    <td class="ltr-number" style="font-weight:700;color:var(--primary)">
                      <template v-if="item.amount > 0">₪{{ fmtNum(item.amount) }}</template>
                      <template v-else>—</template>
                    </td>
                    <td @click.stop>
                      <select
                        class="status-select status-select-sm"
                        :class="customerStatusClass(customerStatuses[item.recruit_id])"
                        :value="customerStatuses[item.recruit_id] || ''"
                        @change="onStatusChange(item.recruit_id, $event)"
                      >
                        <option value="">—</option>
                        <option value="עבר סוכן">עבר סוכן</option>
                        <option value="משך את הכסף">משך את הכסף</option>
                        <option value="__custom__">אחר...</option>
                      </select>
                      <input
                        v-if="customInputId === item.recruit_id"
                        class="status-custom-input status-custom-input-sm"
                        v-model="customInputVal"
                        placeholder="הקלד..."
                        @keydown.enter="confirmCustomStatus(item.recruit_id)"
                        @blur="confirmCustomStatus(item.recruit_id)"
                      />
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Chart Drill-Down Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="drillModal.show" class="modal-overlay" @click.self="drillModal.show = false">
          <div class="modal-card missing-modal-card">
            <div class="modal-head">
              <button class="modal-x" @click="drillModal.show = false">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
              </button>
              <div class="modal-id-row">
                <div>
                  <div class="modal-name">{{ drillModal.title }}</div>
                  <div class="modal-id-num">{{ drillModalCustomers.length }} לקוחות</div>
                </div>
                <span class="modal-status-chip" :class="drillModal.type === 'company' ? 'chip-company' : 'chip-product'">
                  {{ drillModal.value }}
                </span>
              </div>
            </div>

            <!-- Summary strip -->
            <div class="drill-summary">
              <div class="drill-stat">
                <span class="drill-stat-val ltr-number">{{ drillModalFound }}</span>
                <span class="drill-stat-lbl">נמצאו</span>
              </div>
              <div class="drill-stat">
                <span class="drill-stat-val drill-stat-missing ltr-number">{{ drillModalMissing }}</span>
                <span class="drill-stat-lbl">לא נמצאו</span>
              </div>
              <div class="drill-stat">
                <span class="drill-stat-val drill-stat-premium ltr-number">₪{{ fmtNum(drillModalPremium) }}</span>
                <span class="drill-stat-lbl">פרמיה</span>
              </div>
            </div>

            <!-- Search -->
            <div class="mm-search-wrap" style="margin: 0 20px 12px 20px">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              <input class="mm-search" v-model="drillModal.search" placeholder="חיפוש לפי שם או ת.ז..." />
            </div>

            <!-- Table -->
            <div class="mm-table-wrap" style="margin: 0 20px 16px 20px">
              <table class="mm-table">
                <thead>
                  <tr>
                    <th style="width:28px"></th>
                    <th>שם</th>
                    <th>ת.ז</th>
                    <th>חברה</th>
                    <th>מוצר</th>
                    <th>מוצרים</th>
                    <th>פרמיה</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="item in drillModalFiltered"
                    :key="item.recruit_id"
                    class="mm-row"
                    @click="drillModal.show = false; openDetail(item)"
                  >
                    <td>
                      <span v-if="item.found_in_production" class="dot dot-found"></span>
                      <span v-else class="dot dot-missing"></span>
                    </td>
                    <td class="td-name">{{ item.first_name }} {{ item.last_name }}</td>
                    <td class="td-id ltr-number">{{ item.id_number }}</td>
                    <td>{{ item.company || '—' }}</td>
                    <td>{{ item.product || '—' }}</td>
                    <td class="ltr-number">
                      <span v-if="item.found_in_production" class="prod-badge">{{ item.production_products.length }}</span>
                      <span v-else class="prod-badge prod-badge-zero">0</span>
                    </td>
                    <td class="ltr-number" style="font-weight:700;color:var(--primary)">
                      <template v-if="item.production_premium > 0">₪{{ fmtNum(item.production_premium) }}</template>
                      <template v-else>—</template>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- Clipboard notification -->
    <Transition name="clipboard-toast">
      <div v-if="clipboardNotice" class="clipboard-toast">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 4h2a2 2 0 012 2v14a2 2 0 01-2 2H6a2 2 0 01-2-2V6a2 2 0 012-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>
        תוכן המייל הועתק ללוח — הדבק בגוף ההודעה
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import * as XLSX from 'xlsx'
import { useRecruitsStore } from '../../stores/recruits.js'
import { openMailCompose } from '../../utils/mailHelper.js'

const props = defineProps({
  result: { type: Object, required: true },
})

const recruitsStore = useRecruitsStore()
const activeFilter = ref('all')
const currentPage = ref(1)
const pageSize = 50
const chartReady = ref(false)
const detailItem = ref(null)
const clipboardNotice = ref(false)
const customerStatuses = ref({})
const customInputId = ref(null)
const customInputVal = ref('')
const customInputRef = ref(null)
const showMissingModal = ref(false)
const missingSearch = ref('')
const companyFilter = ref('')
const productFilter = ref('')
const drillModal = ref({ show: false, type: '', value: '', title: '', search: '' })

onMounted(() => { nextTick(() => { chartReady.value = true }) })

const foundPct = computed(() => props.result.total > 0 ? Math.round((props.result.found / props.result.total) * 100) : 0)
const missingPct = computed(() => props.result.total > 0 ? Math.round((props.result.not_found / props.result.total) * 100) : 0)

const notFoundList = computed(() => props.result.results.filter(r => !r.found_in_production))

const filteredMissingList = computed(() => {
  const q = missingSearch.value.trim().toLowerCase()
  if (!q) return notFoundList.value
  return notFoundList.value.filter(r => {
    const name = `${r.first_name || ''} ${r.last_name || ''}`.toLowerCase()
    return name.includes(q) || (r.id_number || '').includes(q)
  })
})

// ── Insights computeds ──
const avgProductsPerClient = computed(() => {
  if (!props.result.found) return '0'
  const totalProds = props.result.results
    .filter(r => r.found_in_production)
    .reduce((sum, r) => sum + r.production_products.length, 0)
  return (totalProds / props.result.found).toFixed(1)
})

const hasCompanyData = computed(() => (props.result.company_breakdown || []).length > 0)
const hasStatusData = computed(() => {
  const sb = props.result.status_breakdown || {}
  return Object.keys(sb).length > 0
})
const hasProductData = computed(() => uniqueProducts.value.length > 1)

// Product breakdown data
const productBreakdown = computed(() => {
  const map = {}
  for (const r of props.result.results) {
    const prod = r.product || 'לא ידוע'
    if (!map[prod]) map[prod] = { product: prod, found: 0, not_found: 0, total: 0 }
    map[prod].total++
    if (r.found_in_production) map[prod].found++
    else map[prod].not_found++
  }
  return Object.values(map).sort((a, b) => b.total - a.total)
})

// Drill-down modal computeds
const drillModalCustomers = computed(() => {
  if (!drillModal.value.show) return []
  const { type, value } = drillModal.value
  return props.result.results.filter(r => {
    if (type === 'company') return (r.company || 'לא ידוע') === value
    if (type === 'product') return (r.product || 'לא ידוע') === value
    return false
  })
})

const drillModalFiltered = computed(() => {
  const q = (drillModal.value.search || '').trim().toLowerCase()
  const list = drillModalCustomers.value
  if (!q) return list
  return list.filter(r => {
    const name = `${r.first_name || ''} ${r.last_name || ''}`.toLowerCase()
    return name.includes(q) || (r.id_number || '').includes(q)
  })
})

const drillModalFound = computed(() => drillModalCustomers.value.filter(r => r.found_in_production).length)
const drillModalMissing = computed(() => drillModalCustomers.value.filter(r => !r.found_in_production).length)
const drillModalPremium = computed(() => drillModalCustomers.value.reduce((s, r) => s + (r.production_premium || 0), 0))

const topMissing = computed(() => {
  return props.result.results
    .filter(r => !r.found_in_production)
    .sort((a, b) => (b.amount || 0) - (a.amount || 0))
    .slice(0, 5)
})

const summaryBullets = computed(() => {
  const bullets = []
  const notFound = props.result.results.filter(r => !r.found_in_production)
  if (notFound.length > 0) {
    const totalMissing = notFound.reduce((s, r) => s + (r.amount || 0), 0)
    bullets.push(`<strong>${notFound.length}</strong> לקוחות עם פרמיה של <strong class="ltr-number">₪${fmtNum(totalMissing)}</strong> לא נמצאו — מומלץ לפנות לחברות`)
  }
  const sb = props.result.status_breakdown || {}
  const cancelled = sb['מבוטל'] || 0
  if (cancelled > 0) {
    bullets.push(`<strong>${cancelled}</strong> מוצרים מבוטלים — יש לבדוק מול הלקוחות`)
  }
  const breakdown = props.result.company_breakdown || []
  if (breakdown.length > 0) {
    const worst = breakdown.reduce((max, c) => c.not_found > max.not_found ? c : max, breakdown[0])
    if (worst.not_found > 0) {
      bullets.push(`חברת <strong>${worst.company}</strong> עם הכי הרבה חסרים (${worst.not_found})`)
    }
  }
  return bullets
})

// Company bar chart
const companyChartSeries = computed(() => {
  const bd = props.result.company_breakdown || []
  return [
    { name: 'נמצאו', data: bd.map(c => c.found) },
    { name: 'לא נמצאו', data: bd.map(c => c.not_found) },
  ]
})

const companyChartOptions = computed(() => ({
  chart: {
    type: 'bar', stacked: true, fontFamily: 'Heebo, sans-serif', toolbar: { show: false },
    events: {
      dataPointSelection: (_e, _chart, config) => {
        const bd = props.result.company_breakdown || []
        const company = bd[config.dataPointIndex]
        if (company) openDrillModal('company', company.company)
      },
    },
  },
  plotOptions: { bar: { horizontal: true, barHeight: '60%', borderRadius: 4 } },
  colors: ['#2E844A', '#E8720A'],
  xaxis: {
    categories: (props.result.company_breakdown || []).map(c => c.company),
    labels: { style: { fontFamily: 'Heebo, sans-serif', fontSize: '11px' } },
  },
  yaxis: {
    labels: {
      style: { fontFamily: 'Heebo, sans-serif', fontSize: '11px', cursor: 'pointer' },
    },
  },
  legend: { position: 'top', fontFamily: 'Heebo, sans-serif', fontSize: '11px' },
  dataLabels: { enabled: false },
  grid: { borderColor: 'var(--border-subtle)', strokeDashArray: 3 },
  tooltip: { style: { fontFamily: 'Heebo, sans-serif' } },
  states: { active: { filter: { type: 'darken', value: 0.75 } } },
}))

// Status donut chart
const statusChartSeries = computed(() => {
  const sb = props.result.status_breakdown || {}
  return Object.values(sb)
})

const statusChartOptions = computed(() => {
  const sb = props.result.status_breakdown || {}
  const labels = Object.keys(sb)
  const colorMap = { 'פעיל': '#2E844A', 'מוקפא': '#0176D3', 'מבוטל': '#EA4335', 'אחר': '#999' }
  const colors = labels.map(l => colorMap[l] || '#999')
  return {
    chart: { type: 'donut', fontFamily: 'Heebo, sans-serif' },
    labels,
    colors,
    legend: { position: 'bottom', fontFamily: 'Heebo, sans-serif', fontSize: '11px' },
    dataLabels: {
      enabled: true,
      formatter: (val) => val.toFixed(0) + '%',
      style: { fontFamily: 'Heebo, sans-serif', fontWeight: 700, fontSize: '12px' },
      dropShadow: { enabled: false },
    },
    plotOptions: { pie: { donut: { size: '60%' } } },
    stroke: { width: 2, colors: ['var(--card-bg)'] },
    tooltip: { style: { fontFamily: 'Heebo, sans-serif' }, y: { formatter: (val) => val + ' מוצרים' } },
  }
})

// Product donut chart
const productChartSeries = computed(() => productBreakdown.value.map(p => p.total))

const productChartOptions = computed(() => {
  const labels = productBreakdown.value.map(p => p.product)
  const productColors = ['#0176D3', '#7F56D9', '#06BDBD', '#E8720A', '#2E844A', '#EA4335', '#F59E0B', '#8B5CF6', '#EC4899', '#14B8A6']
  return {
    chart: {
      type: 'donut', fontFamily: 'Heebo, sans-serif',
      events: {
        dataPointSelection: (_e, _chart, config) => {
          const prod = productBreakdown.value[config.dataPointIndex]
          if (prod) openDrillModal('product', prod.product)
        },
      },
    },
    labels,
    colors: productColors.slice(0, labels.length),
    legend: { position: 'bottom', fontFamily: 'Heebo, sans-serif', fontSize: '11px' },
    dataLabels: {
      enabled: true,
      formatter: (val) => val.toFixed(0) + '%',
      style: { fontFamily: 'Heebo, sans-serif', fontWeight: 700, fontSize: '11px' },
      dropShadow: { enabled: false },
    },
    plotOptions: { pie: { donut: { size: '58%' } } },
    stroke: { width: 2, colors: ['var(--card-bg)'] },
    tooltip: { style: { fontFamily: 'Heebo, sans-serif' }, y: { formatter: (val) => val + ' לקוחות' } },
    states: { active: { filter: { type: 'darken', value: 0.75 } } },
  }
})

const uniqueCompanies = computed(() => {
  const set = new Set()
  for (const r of props.result.results) {
    if (r.company) set.add(r.company)
  }
  return [...set].sort()
})

const uniqueProducts = computed(() => {
  const set = new Set()
  for (const r of props.result.results) {
    if (r.product) set.add(r.product)
  }
  return [...set].sort()
})

const filteredResults = computed(() => {
  let list = props.result.results
  if (activeFilter.value === 'found') list = list.filter(r => r.found_in_production)
  if (activeFilter.value === 'not_found') list = list.filter(r => !r.found_in_production)
  if (companyFilter.value) list = list.filter(r => r.company === companyFilter.value)
  if (productFilter.value) list = list.filter(r => r.product === productFilter.value)
  return list
})

const totalPages = computed(() => Math.ceil(filteredResults.value.length / pageSize))

const paginatedResults = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredResults.value.slice(start, start + pageSize)
})

const visiblePages = computed(() => {
  const total = totalPages.value
  const cur = currentPage.value
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  const pages = []
  pages.push(1)
  if (cur > 3) pages.push('...')
  const windowStart = Math.max(2, cur - 1)
  const windowEnd = Math.min(total - 1, Math.max(cur + 1, 4))
  for (let i = windowStart; i <= windowEnd; i++) pages.push(i)
  if (cur < total - 2) pages.push('...')
  pages.push(total)
  return pages
})

watch([activeFilter, companyFilter, productFilter], () => { currentPage.value = 1 })

function openDetail(item) { detailItem.value = item }

function openDrillModal(type, value) {
  drillModal.value = {
    show: true,
    type,
    value,
    title: type === 'company' ? `לקוחות — ${value}` : `לקוחות — ${value}`,
    search: '',
  }
}

function downloadMissingExcel() {
  const missing = props.result.results.filter(r => !r.found_in_production)
  if (!missing.length) return

  const rows = missing.map(m => ({
    'שם': `${m.first_name || ''} ${m.last_name || ''}`.trim(),
    'ת.ז': m.id_number,
    'חברה': m.company || '',
    'מוצר': m.product || '',
    'סכום': m.amount || 0,
    'סטטוס': customerStatuses.value[m.recruit_id] || '',
  }))

  const ws = XLSX.utils.json_to_sheet(rows)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, 'חסרים')
  XLSX.writeFile(wb, `מגויסים_חסרים_${new Date().toLocaleDateString('he-IL')}.xlsx`)
}

async function sendMissingMail() {
  const missing = props.result.results.filter(r => !r.found_in_production)
  if (!missing.length) return

  // Group by company
  const byCompany = {}
  for (const m of missing) {
    const co = m.company || 'לא ידוע'
    if (!byCompany[co]) byCompany[co] = []
    byCompany[co].push(m)
  }

  // Find company with most missing
  const topCompany = Object.entries(byCompany).reduce((max, cur) => cur[1].length > max[1].length ? cur : max)
  const companyName = topCompany[0]
  const clients = topCompany[1]

  const lines = clients.map(m => {
    const name = `${m.first_name || ''} ${m.last_name || ''}`.trim()
    return `הלקוח ${name} ת.ז ${m.id_number} אינו מופיע אצלי בפרודוקציה.\nאשמח להבין מהי הסיבה לכך, ולבדוק האם יש צורך בפעולה כלשהי מצדי על מנת שיופיע בדוחות.`
  }).join('\n\n')

  const subject = `בקשת בדיקה — לקוחות חסרים בפרודוקציה (${clients.length})`
  const body = `שלום רב,\n\n${lines}\n\nבברכה`

  const status = await openMailCompose({ to: '', subject, body })
  if (status === 'clipboard') {
    clipboardNotice.value = true
    setTimeout(() => { clipboardNotice.value = false }, 4000)
  }
}

function onStatusChange(recruitId, event) {
  const val = event.target.value
  if (val === '__custom__') {
    customInputId.value = recruitId
    customInputVal.value = ''
    nextTick(() => {
      const inputs = document.querySelectorAll('.status-custom-input')
      const last = inputs[inputs.length - 1]
      if (last) last.focus()
    })
  } else {
    customerStatuses.value[recruitId] = val
    customInputId.value = null
  }
}

function confirmCustomStatus(recruitId) {
  if (customInputVal.value.trim()) {
    customerStatuses.value[recruitId] = customInputVal.value.trim()
  }
  customInputId.value = null
  customInputVal.value = ''
}

function customerStatusClass(status) {
  if (!status) return ''
  if (status === 'עבר סוכן') return 'cs-moved'
  if (status === 'משך את הכסף') return 'cs-withdrew'
  return 'cs-custom'
}

function fmtNum(val) {
  if (val == null || val === 0) return '0'
  return Number(val).toLocaleString('he-IL', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

function shortCompany(name) {
  if (!name) return ''
  const words = name.split(/\s+/)
  return words.length <= 2 ? name : words.slice(0, 2).join(' ')
}

function statusLabel(s) {
  if (!s) return '—'
  if (s === 'פעיל' || s.includes('active') || s.includes('פעיל')) return 'פעיל'
  if (s === 'מוקפא' || s.includes('frozen')) return 'מוקפא'
  if (s.includes('מבוטל') || s.includes('cancel')) return 'מבוטל'
  return s
}

function statusClass(s) {
  const label = statusLabel(s)
  if (label === 'פעיל') return 'st-active'
  if (label === 'מוקפא') return 'st-frozen'
  if (label === 'מבוטל') return 'st-cancelled'
  return ''
}

const chartSeries = computed(() => [props.result.found, props.result.not_found])

const chartOptions = computed(() => ({
  chart: { type: 'donut', fontFamily: 'Heebo, sans-serif' },
  labels: ['נמצאו בפרודוקציה', 'לא נמצאו'],
  colors: ['#2E844A', '#E8720A'],
  legend: { show: false },
  dataLabels: {
    enabled: true,
    formatter: (val) => val.toFixed(0) + '%',
    style: { fontFamily: 'Heebo, sans-serif', fontWeight: 700, fontSize: '13px' },
    dropShadow: { enabled: false },
  },
  plotOptions: {
    pie: {
      donut: {
        size: '65%',
        labels: {
          show: true,
          total: {
            show: true,
            label: 'סה"כ',
            fontFamily: 'Heebo, sans-serif',
            fontSize: '13px',
            fontWeight: 700,
            color: 'var(--text-muted)',
            formatter: () => props.result.total,
          },
          value: {
            fontFamily: 'Heebo, sans-serif',
            fontSize: '22px',
            fontWeight: 800,
          },
        },
      },
    },
  },
  stroke: { width: 2, colors: ['var(--card-bg)'] },
  tooltip: {
    style: { fontFamily: 'Heebo, sans-serif' },
    y: { formatter: (val) => val + ' לקוחות' },
  },
}))
</script>

<style scoped>
.comparison-results {
  padding: 24px;
  animation: slideUp 0.5s var(--transition);
}

.results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--primary);
}

.header-title h3 {
  font-size: 17px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.3px;
}

.btn-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  color: var(--text-muted);
  transition: all 0.25s var(--transition);
}
.btn-close:hover { background: var(--bg-surface); color: var(--text); }

/* ── Dashboard row ── */
.dashboard-row {
  display: flex;
  gap: 20px;
  align-items: center;
  margin-bottom: 20px;
}

.chart-box { flex: 0 0 220px; }

.kpi-row {
  flex: 1;
  display: flex;
  gap: 10px;
}

.kpi {
  flex: 1;
  text-align: center;
  padding: 16px 12px;
  border-radius: 12px;
  border: 1px solid var(--border-subtle);
  cursor: pointer;
  transition: all 0.25s var(--transition);
}
.kpi:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.06); }

.kpi-num {
  display: block;
  font-size: 30px;
  font-weight: 800;
  letter-spacing: -1px;
  line-height: 1.1;
}

.kpi-lbl {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  margin-top: 4px;
}

.kpi-pct {
  display: block;
  font-size: 11px;
  font-weight: 700;
  margin-top: 2px;
}

.found-kpi { background: var(--green-light); border-color: var(--green-light); }
.found-kpi .kpi-num { color: var(--accent-emerald); }
.found-kpi .kpi-pct { color: var(--accent-emerald); }

.missing-kpi { background: rgba(232,114,10,0.06); border-color: rgba(232,114,10,0.1); }
.missing-kpi .kpi-num { color: #E8720A; }
.missing-kpi .kpi-pct { color: #E8720A; }

.total-kpi { background: var(--border-subtle); }
.total-kpi .kpi-num { color: var(--text); }

/* ── Insights Section ── */
.insights-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 20px;
  padding-top: 4px;
}

.insights-kpi-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
}

.ins-kpi {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 14px 8px 12px;
  border-radius: 12px;
  border: 1px solid var(--border-subtle);
  transition: all 0.25s var(--transition);
}
.ins-kpi:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.06); }

.ins-kpi-icon {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 8px;
}

.ins-kpi-val {
  font-size: 18px;
  font-weight: 800;
  letter-spacing: -0.5px;
  line-height: 1.2;
}

.ins-kpi-lbl {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  margin-top: 4px;
}

.ins-kpi-green { background: var(--green-light); border-color: var(--green-light); }
.ins-kpi-green .ins-kpi-icon { background: rgba(46,132,74,0.12); color: var(--accent-emerald); }
.ins-kpi-green .ins-kpi-val { color: var(--accent-emerald); }

.ins-kpi-orange { background: rgba(232,114,10,0.06); border-color: rgba(232,114,10,0.1); }
.ins-kpi-orange .ins-kpi-icon { background: rgba(232,114,10,0.12); color: #E8720A; }
.ins-kpi-orange .ins-kpi-val { color: #E8720A; }

.ins-kpi-cyan { background: rgba(6,189,189,0.06); border-color: rgba(6,189,189,0.1); }
.ins-kpi-cyan .ins-kpi-icon { background: rgba(6,189,189,0.12); color: #06BDBD; }
.ins-kpi-cyan .ins-kpi-val { color: #06BDBD; }

.ins-kpi-violet { background: rgba(127,86,217,0.06); border-color: rgba(127,86,217,0.1); }
.ins-kpi-violet .ins-kpi-icon { background: rgba(127,86,217,0.12); color: var(--accent-violet); }
.ins-kpi-violet .ins-kpi-val { color: var(--accent-violet); }

.ins-kpi-primary { background: var(--primary-glow); border-color: rgba(1,118,211,0.1); }
.ins-kpi-primary .ins-kpi-icon { background: rgba(1,118,211,0.12); color: var(--primary); }
.ins-kpi-primary .ins-kpi-val { color: var(--primary); }

.insights-charts-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.insights-charts-row-3 {
  grid-template-columns: 1fr 1fr 1fr;
}

.ins-chart-clickable {
  cursor: pointer;
  transition: all 0.25s var(--transition);
}
.ins-chart-clickable:hover {
  border-color: var(--primary);
  box-shadow: 0 4px 20px rgba(1, 118, 211, 0.08);
}

.chart-click-hint {
  margin-inline-start: auto;
  font-size: 10px;
  font-weight: 500;
  color: var(--primary);
  opacity: 0;
  transition: opacity 0.2s;
}
.ins-chart-clickable:hover .chart-click-hint {
  opacity: 1;
}

.ins-chart-box {
  padding: 16px;
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  background: var(--card-bg);
}

.ins-chart-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.ins-missing-table {
  padding: 16px;
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  background: var(--card-bg);
}

.mini-tbl {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
}
.mini-tbl thead th {
  padding: 8px 10px;
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  text-align: right;
  border-bottom: 1px solid var(--border-subtle);
}
.mini-tbl tbody tr {
  cursor: pointer;
  transition: background 0.12s;
}
.mini-tbl tbody tr:hover { background: var(--border-subtle); }
.mini-tbl tbody td {
  padding: 8px 10px;
  font-size: 12px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text);
}

.ins-summary-card {
  padding: 16px;
  border: 1px solid rgba(232,114,10,0.15);
  border-radius: 12px;
  background: rgba(232,114,10,0.03);
}

.summary-bullets {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.summary-bullets li {
  font-size: 13px;
  color: var(--text-secondary);
  padding-right: 16px;
  position: relative;
  line-height: 1.6;
}
.summary-bullets li::before {
  content: '•';
  position: absolute;
  right: 0;
  color: #E8720A;
  font-weight: 700;
}

@media (max-width: 900px) {
  .insights-charts-row-3 { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 700px) {
  .insights-kpi-row { grid-template-columns: repeat(2, 1fr); }
  .insights-kpi-row .ins-kpi:last-child { grid-column: span 2; }
  .insights-charts-row { grid-template-columns: 1fr; }
  .insights-charts-row-3 { grid-template-columns: 1fr; }
}

/* ── Segmented filter ── */
.seg-filter {
  display: inline-flex;
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 16px;
}

.seg-filter button {
  padding: 8px 18px;
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  color: var(--text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.2s var(--transition);
  border-left: 1px solid var(--border);
  white-space: nowrap;
}
.seg-filter button:first-child { border-left: none; }
.seg-filter button b { font-weight: 800; margin-right: 3px; }
.seg-filter button:hover { background: var(--border-subtle); }
.seg-filter button.active {
  background: var(--primary);
  color: #fff;
}

/* ── Slice Filters (Company & Product) ── */
.slice-filters {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
  margin-bottom: 4px;
  flex-wrap: wrap;
}

.slice-filter {
  display: flex;
  align-items: center;
  gap: 6px;
}

.slice-filter label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  white-space: nowrap;
}

.slice-filter select {
  padding: 6px 28px 6px 10px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--card-bg);
  color: var(--text-primary);
  font-family: 'Heebo', sans-serif;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  appearance: none;
  -webkit-appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%23999' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: left 8px center;
  transition: all 0.2s;
  min-width: 120px;
}

.slice-filter select:hover {
  border-color: var(--primary);
}

.slice-filter select:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 2px rgba(245, 124, 0, 0.15);
  outline: none;
}

.slice-clear {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px;
  border: 1px solid rgba(239, 83, 80, 0.3);
  border-radius: 8px;
  background: rgba(239, 83, 80, 0.06);
  color: #ef5350;
  font-family: 'Heebo', sans-serif;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.slice-clear:hover {
  background: rgba(239, 83, 80, 0.12);
}

.slice-count {
  font-size: 12px;
  color: var(--primary);
  font-weight: 700;
}

/* ── Table ── */
.tbl-wrap { overflow-x: auto; }

.tbl {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
}

.tbl thead th {
  padding: 10px 10px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-align: right;
  letter-spacing: 0.3px;
  border-bottom: 1px solid var(--border-subtle);
  white-space: nowrap;
}
.th-status { width: 28px; }

.tbl-row {
  cursor: pointer;
  transition: all 0.15s var(--transition);
}
.tbl-row:hover { background: var(--border-subtle); }
.tbl-row td {
  padding: 10px 10px;
  font-size: 13px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text);
}

.row-found { border-right: 3px solid var(--accent-emerald); }
.row-missing { border-right: 3px solid #E8720A; }

.dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.dot-found { background: var(--accent-emerald); box-shadow: 0 0 6px var(--green-light); }
.dot-missing { background: #E8720A; box-shadow: 0 0 6px rgba(232,114,10,0.2); }

.td-name { font-weight: 600; white-space: nowrap; }
.td-id { font-size: 12px; color: var(--text-muted); font-family: monospace; }
.td-company, .td-product { font-size: 12px; color: var(--text-secondary); max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.prod-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  background: var(--green-light);
  color: var(--accent-emerald);
}
.prod-badge-zero { background: rgba(232,114,10,0.08); color: #E8720A; }

.td-premium { font-weight: 700; font-size: 12px; color: var(--primary); white-space: nowrap; }

/* ── Pagination ── */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
}

.pg {
  min-width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  color: var(--text-secondary);
  border: 1px solid var(--border-subtle);
  background: transparent;
  cursor: pointer;
  transition: all 0.15s;
}
.pg:hover:not(:disabled) { background: var(--border-subtle); }
.pg.active { background: var(--primary); color: #fff; border-color: var(--primary); }
.pg:disabled { opacity: 0.3; cursor: not-allowed; }
.pg-dots { color: var(--text-muted); font-size: 12px; padding: 0 4px; }
.pg-info { font-size: 11px; color: var(--text-muted); margin-right: 8px; }

/* ── Modal ── */
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1010;
  background: rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.modal-card {
  width: 100%;
  max-width: 580px;
  max-height: 85vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: var(--card-bg, #fff);
  border: 1px solid var(--border);
  border-radius: 14px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.18);
}

.modal-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 20px;
  background: #F7F8FA;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
  position: relative;
}

.modal-x {
  position: absolute;
  top: 12px;
  left: 12px;
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-muted);
  width: 28px;
  height: 28px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}
.modal-x:hover { background: var(--border-subtle); color: var(--text); }

.modal-id-row {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.modal-name { font-size: 16px; font-weight: 700; color: var(--text); }
.modal-id-num { font-size: 12px; color: var(--text-muted); margin-top: 2px; }

.modal-status-chip {
  font-size: 11px;
  font-weight: 700;
  padding: 4px 12px;
  border-radius: 20px;
  white-space: nowrap;
  flex-shrink: 0;
}
.chip-found { background: var(--green-light); color: var(--accent-emerald); }
.chip-missing { background: rgba(232,114,10,0.08); color: #E8720A; }
.chip-company { background: rgba(1,118,211,0.08); color: #0176D3; }
.chip-product { background: rgba(127,86,217,0.08); color: #7F56D9; }

/* Modal sections */
.modal-section {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-subtle);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  margin-bottom: 12px;
}

.section-count {
  background: var(--primary-glow);
  color: var(--primary);
  padding: 1px 7px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 700;
}

/* Info grid (recruit data) */
.info-grid {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.info-cell {
  flex: 1;
  min-width: 100px;
  padding: 10px 14px;
  background: var(--border-subtle);
  border-radius: 8px;
}

.info-lbl {
  display: block;
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.info-val {
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
}

/* Product table in modal */
.prod-table-wrap {
  overflow-x: auto;
}

.prod-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
}

.prod-table thead th {
  padding: 8px 10px;
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  text-align: right;
  border-bottom: 1px solid var(--border-subtle);
  letter-spacing: 0.3px;
}

.prod-table tbody tr {
  transition: background 0.12s;
}
.prod-table tbody tr:hover { background: var(--border-subtle); }

.prod-table tbody td {
  padding: 9px 10px;
  font-size: 12px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text);
}

.pt-product { font-weight: 600; max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pt-company { color: var(--text-secondary); font-size: 11px; }
.pt-premium { font-weight: 700; color: var(--primary); white-space: nowrap; }

.status-tag {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 6px;
  white-space: nowrap;
}
.st-active { background: var(--green-light); color: var(--accent-emerald); }
.st-frozen { background: rgba(1,118,211,0.06); color: var(--primary); }
.st-cancelled { background: var(--red-light, rgba(234,67,53,0.06)); color: var(--red, #EA4335); }

.modal-total {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
  font-size: 13px;
  color: var(--text-secondary);
}
.modal-total strong { font-size: 16px; font-weight: 800; color: var(--primary); }

.modal-empty {
  text-align: center;
  padding: 32px 20px;
  color: var(--text-muted);
}
.modal-empty svg { margin-bottom: 12px; opacity: 0.4; }
.modal-empty p { font-size: 14px; font-weight: 600; color: var(--text-secondary); margin-bottom: 4px; }
.modal-empty span { font-size: 12px; }

/* Modal transition */
.modal-enter-active { animation: modalIn 0.2s ease-out; }
.modal-leave-active { animation: modalIn 0.15s ease reverse; }
@keyframes modalIn {
  from { opacity: 0; transform: scale(0.96) translateY(8px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

.ltr-number { direction: ltr; unicode-bidi: embed; display: inline-block; }

/* ── Action buttons ── */
.action-btns {
  margin-inline-start: auto;
  display: flex;
  gap: 4px;
}

.action-icon-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 7px;
  border: 1px solid var(--border-subtle);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.2s var(--transition);
}
.action-icon-btn:hover {
  background: var(--primary-glow);
  color: var(--primary);
  border-color: rgba(1,118,211,0.2);
}

/* ── Clipboard toast ── */
.clipboard-toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 9000;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: var(--text, #1a1a1a);
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  border-radius: 10px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.18);
  white-space: nowrap;
}
.clipboard-toast svg { flex-shrink: 0; }
.clipboard-toast-enter-active { animation: toastIn 0.3s ease-out; }
.clipboard-toast-leave-active { animation: toastIn 0.2s ease reverse; }
@keyframes toastIn {
  from { opacity: 0; transform: translateX(-50%) translateY(12px); }
  to { opacity: 1; transform: translateX(-50%) translateY(0); }
}

@media (max-width: 700px) {
  .dashboard-row { flex-direction: column; }
  .chart-box { flex: none; width: 100%; }
  .kpi-row { width: 100%; }
  .seg-filter { width: 100%; display: flex; }
  .seg-filter button { flex: 1; }
}

/* ── Customer Status Column ── */
.td-customer-status {
  min-width: 140px;
}

.status-select-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.status-select {
  padding: 6px 10px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--card-bg);
  color: var(--text-primary);
  font-family: 'Heebo', sans-serif;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  appearance: none;
  -webkit-appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%23999' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: left 10px center;
  padding-left: 28px;
}

.status-select:hover {
  border-color: var(--primary);
}

.status-select:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 2px rgba(245, 124, 0, 0.15);
  outline: none;
}

.status-select.cs-moved {
  background-color: rgba(232, 114, 10, 0.08);
  border-color: rgba(232, 114, 10, 0.3);
  color: #E8720A;
}

.status-select.cs-withdrew {
  background-color: rgba(239, 83, 80, 0.08);
  border-color: rgba(239, 83, 80, 0.3);
  color: #ef5350;
}

.status-select.cs-custom {
  background-color: rgba(1, 118, 211, 0.08);
  border-color: rgba(1, 118, 211, 0.3);
  color: #0176D3;
}

.status-custom-input {
  padding: 6px 10px;
  border: 1px solid var(--primary);
  border-radius: 8px;
  background: var(--card-bg);
  color: var(--text-primary);
  font-family: 'Heebo', sans-serif;
  font-size: 12px;
  outline: none;
  box-shadow: 0 0 0 2px rgba(245, 124, 0, 0.15);
}

.status-found-label {
  font-size: 12px;
  color: #2E844A;
  font-weight: 600;
}

.modal-status-edit {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
}

.modal-status-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
}

.modal-status-edit .status-select {
  width: 220px;
  font-size: 13px;
  padding: 8px 12px;
}

.modal-status-edit .status-custom-input {
  width: 220px;
  font-size: 13px;
  padding: 8px 12px;
}

/* ── Missing Modal ── */
.missing-modal-card {
  max-width: 800px;
  width: 95vw;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
}

.mm-search-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: var(--input-bg);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  margin-bottom: 12px;
  color: var(--text-muted);
}

.mm-search {
  border: none;
  background: transparent;
  outline: none;
  font-family: 'Heebo', sans-serif;
  font-size: 13px;
  color: var(--text-primary);
  width: 100%;
}

.mm-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.mm-action-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--card-bg);
  color: var(--text-secondary);
  font-family: 'Heebo', sans-serif;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.mm-action-btn:hover {
  border-color: var(--primary);
  color: var(--primary);
  background: rgba(245, 124, 0, 0.06);
}

.mm-table-wrap {
  overflow-y: auto;
  flex: 1;
  min-height: 0;
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
}

.mm-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.mm-table thead {
  position: sticky;
  top: 0;
  z-index: 1;
}

.mm-table th {
  background: var(--header-bg);
  padding: 10px 12px;
  font-weight: 700;
  font-size: 12px;
  color: var(--text-muted);
  text-align: right;
  border-bottom: 1px solid var(--border-subtle);
}

.mm-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border-subtle);
  vertical-align: middle;
}

.mm-row {
  cursor: pointer;
  transition: background 0.15s;
}

.mm-row:hover {
  background: rgba(245, 124, 0, 0.04);
}

/* ── Drill-Down Modal Summary ── */
.drill-summary {
  display: flex;
  gap: 12px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border-subtle);
}

.drill-stat {
  flex: 1;
  text-align: center;
  padding: 10px 8px;
  border-radius: 10px;
  background: var(--border-subtle);
}

.drill-stat-val {
  display: block;
  font-size: 20px;
  font-weight: 800;
  color: var(--accent-emerald);
  letter-spacing: -0.5px;
}

.drill-stat-missing { color: #E8720A; }
.drill-stat-premium { color: var(--primary); font-size: 16px; }

.drill-stat-lbl {
  display: block;
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  margin-top: 2px;
}

.status-select-sm {
  padding: 4px 8px;
  font-size: 11px;
  padding-left: 22px;
}

.status-custom-input-sm {
  padding: 4px 8px;
  font-size: 11px;
  width: 100%;
  margin-top: 4px;
}
</style>
