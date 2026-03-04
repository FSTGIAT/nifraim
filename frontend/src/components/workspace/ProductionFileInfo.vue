<template>
  <div class="file-info-card">
    <div class="card-glow"></div>

    <div class="card-inner">
      <!-- Status strip -->
      <div class="status-strip">
        <div class="pulse-dot"></div>
        <span>פעיל</span>
      </div>

      <div class="card-header">
        <div class="file-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
        </div>
        <div class="card-title">
          <h3>קובץ פרודוקציה</h3>
          <p class="filename">{{ file.filename }}</p>
        </div>
      </div>

      <div class="stats-grid">
        <div class="stat-card">
          <span class="stat-value ltr-number">{{ file.record_count.toLocaleString() }}</span>
          <span class="stat-label">רשומות</span>
        </div>
        <div class="stat-card">
          <span class="stat-value ltr-number">{{ formatDate(file.uploaded_at) }}</span>
          <span class="stat-label">תאריך העלאה</span>
        </div>
        <div class="stat-card" v-if="file.company_source">
          <span class="stat-value">{{ file.company_source }}</span>
          <span class="stat-label">מקור</span>
        </div>
      </div>

      <div class="companies-section" v-if="file.companies && file.companies.length">
        <span class="section-label">חברות בקובץ</span>
        <div class="company-tags">
          <span class="company-tag" v-for="c in file.companies" :key="c">{{ c }}</span>
        </div>
      </div>

      <div class="card-actions">
        <button class="btn-replace" @click="$emit('replace')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="23 4 23 10 17 10"/>
            <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
          </svg>
          <span>החלף קובץ</span>
        </button>
        <button class="btn-delete" @click="handleDelete">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  file: { type: Object, required: true },
})
const emit = defineEmits(['replace', 'delete'])

function formatDate(dateStr) {
  const d = new Date(dateStr)
  return d.toLocaleDateString('he-IL', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

function handleDelete() {
  if (confirm('האם למחוק את קובץ הפרודוקציה?')) {
    emit('delete')
  }
}
</script>

<style scoped>
.file-info-card {
  max-width: 520px;
  margin: 0 auto;
  position: relative;
  animation: slideUp 0.5s var(--transition);
}

.card-glow {
  position: absolute;
  inset: -1px;
  border-radius: calc(var(--radius-lg) + 1px);
  background: linear-gradient(135deg, var(--primary-light), rgba(34, 211, 238, 0.15), rgba(127, 86, 217, 0.08));
  opacity: 0.6;
  filter: blur(1px);
  z-index: 0;
}

.card-inner {
  position: relative;
  z-index: 1;
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  padding: 28px;
}

.status-strip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  background: var(--green-light);
  border: 1px solid var(--green-light);
  border-radius: 100px;
  font-size: 11px;
  font-weight: 600;
  color: var(--accent-emerald);
  margin-bottom: 20px;
}

.pulse-dot {
  width: 6px;
  height: 6px;
  background: var(--accent-emerald);
  border-radius: 50%;
  animation: pulse-soft 2s ease-in-out infinite;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.file-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, var(--primary-light), rgba(34, 211, 238, 0.1));
  border: 1px solid var(--primary-light);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary);
  flex-shrink: 0;
}

.card-title h3 {
  font-size: 17px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.3px;
}

.filename {
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 2px;
  word-break: break-all;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
  gap: 10px;
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
  padding: 16px 12px;
  background: var(--border-subtle);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  transition: all 0.25s var(--transition);
}

.stat-card:hover {
  background: var(--border-subtle);
  border-color: var(--border);
}

.stat-value {
  display: block;
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 4px;
}

.stat-label {
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.section-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.company-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 20px;
}

.company-tag {
  background: var(--primary-light);
  color: var(--primary);
  padding: 5px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  border: 1px solid var(--primary-light);
}

.card-actions {
  display: flex;
  gap: 8px;
}

.btn-replace {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 11px;
  background: linear-gradient(135deg, var(--primary-deep), var(--primary));
  color: white;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  transition: all 0.3s var(--transition);
}

.btn-replace:hover {
  box-shadow: 0 8px 24px var(--primary-light);
  transform: translateY(-2px);
}

.btn-delete {
  width: 42px;
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  border: 1px solid var(--border);
  transition: all 0.25s var(--transition);
}

.btn-delete:hover {
  background: var(--red-light);
  color: var(--red);
  border-color: var(--red-light);
}

.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
  display: inline-block;
}
</style>
