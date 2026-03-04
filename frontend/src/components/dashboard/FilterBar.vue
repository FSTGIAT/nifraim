<template>
  <div class="filter-bar">
    <div class="filter-row">
      <div class="filter-field search">
        <svg class="field-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="11" cy="11" r="8"/>
          <line x1="21" y1="21" x2="16.65" y2="16.65"/>
        </svg>
        <input
          type="text"
          v-model="filters.search"
          placeholder="חיפוש שם / ת.ז..."
          @keyup.enter="$emit('apply')"
        />
      </div>
      <div class="filter-field">
        <select v-model="filters.status" @change="$emit('apply')">
          <option value="">כל הסטטוסים</option>
          <option value="matched">נמצא בשני הקבצים</option>
          <option value="missing_from_report">חסר בדוח חברה</option>
          <option value="extra_in_report">חסר בקובץ סוכן</option>
          <option value="paid_match">שולם - תואם</option>
          <option value="paid_mismatch">שולם - חריגה</option>
          <option value="unpaid">לא שולם</option>
          <option value="cancelled">בוטל</option>
          <option value="no_data">אין נתונים</option>
        </select>
      </div>
      <div class="filter-field">
        <input
          type="text"
          v-model="filters.company"
          placeholder="חברה..."
          @keyup.enter="$emit('apply')"
        />
      </div>
      <div class="filter-field">
        <input
          type="text"
          v-model="filters.product"
          placeholder="מוצר..."
          @keyup.enter="$emit('apply')"
        />
      </div>
      <div class="filter-field" v-if="uploads.length > 0">
        <select v-model="filters.uploadId" @change="$emit('apply')">
          <option value="">כל הקבצים</option>
          <option v-for="u in uploads" :key="u.id" :value="u.id">{{ truncate(u.filename, 25) }}</option>
        </select>
      </div>
      <button class="btn-apply" @click="$emit('apply')">סנן</button>
      <button class="btn-reset" @click="$emit('reset')">נקה</button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  filters: { type: Object, required: true },
  uploads: { type: Array, default: () => [] },
})
defineEmits(['apply', 'reset'])

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '...' : str
}
</script>

<style scoped>
.filter-bar {
  background: var(--card-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg, 16px);
  padding: 16px;
  margin-bottom: 16px;
}

.filter-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

.filter-field {
  position: relative;
}

.field-icon {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  pointer-events: none;
}

.filter-field input,
.filter-field select {
  padding: 8px 12px;
  border: 1px solid var(--glass-border);
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  min-width: 120px;
  outline: none;
  background: var(--bg-surface);
  color: var(--text);
  transition: all 0.25s;
}

.filter-field.search input {
  min-width: 200px;
  padding-right: 32px;
}

.filter-field input::placeholder {
  color: var(--text-muted);
}

.filter-field input:focus,
.filter-field select:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-glow);
}

.filter-field select option {
  background: var(--bg);
  color: var(--text-secondary);
}

.btn-apply {
  background: linear-gradient(135deg, var(--primary-deep), var(--primary));
  color: white;
  border: none;
  border-radius: 8px;
  padding: 8px 20px;
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.25s;
}

.btn-apply:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px var(--primary-light);
}

.btn-reset {
  background: none;
  border: 1px solid var(--glass-border);
  border-radius: 8px;
  padding: 8px 16px;
  font-size: 14px;
  font-family: inherit;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.25s;
}

.btn-reset:hover {
  background: var(--bg-surface);
  color: var(--text);
}
</style>
