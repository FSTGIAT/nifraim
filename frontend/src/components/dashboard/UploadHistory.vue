<template>
  <div class="upload-history">
    <h3>היסטוריית העלאות</h3>
    <div v-if="uploads.length === 0" class="empty">אין העלאות עדיין</div>
    <div v-else class="upload-list">
      <div v-for="upload in uploads" :key="upload.id" class="upload-item">
        <div class="upload-info">
          <span class="upload-name" :title="upload.filename">{{ truncate(upload.filename, 30) }}</span>
          <span class="upload-meta">
            <span class="ltr-number">{{ upload.record_count }}</span> רשומות
            · {{ formatDate(upload.uploaded_at) }}
          </span>
          <span class="upload-source" v-if="upload.company_source">{{ upload.company_source }}</span>
        </div>
        <div class="upload-actions">
          <button class="btn-filter" @click="$emit('filter', upload.id)" title="סנן לפי העלאה זו">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="11" cy="11" r="8"/>
              <line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
          </button>
          <button class="btn-delete" @click="$emit('delete', upload.id)" title="מחק">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  uploads: { type: Array, required: true },
})
defineEmits(['delete', 'filter'])

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return d.toLocaleDateString('he-IL')
}
</script>

<style scoped>
.upload-history {
  background: var(--card-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg, 16px);
  padding: 20px;
}

h3 {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 12px;
}

.empty {
  text-align: center;
  color: var(--text-muted);
  font-size: 14px;
  padding: 16px;
}

.upload-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.upload-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid var(--glass-border);
  border-radius: 8px;
  transition: all 0.2s;
}

.upload-item:hover {
  background: var(--primary-light);
  border-color: var(--primary-light);
}

.upload-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.upload-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.upload-meta {
  font-size: 12px;
  color: var(--text-muted);
}

.ltr-number {
  direction: ltr;
  unicode-bidi: isolate;
}

.upload-source {
  font-size: 11px;
  color: var(--primary);
  background: var(--primary-light);
  padding: 2px 8px;
  border-radius: 4px;
  width: fit-content;
  margin-top: 2px;
}

.upload-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.btn-filter, .btn-delete {
  background: none;
  border: none;
  padding: 6px;
  border-radius: 6px;
  transition: all 0.2s;
  cursor: pointer;
  color: var(--text-muted);
  display: flex;
  align-items: center;
}

.btn-filter:hover {
  background: var(--primary-light);
  color: var(--primary);
}

.btn-delete:hover {
  background: var(--red-light);
  color: var(--red);
}
</style>
