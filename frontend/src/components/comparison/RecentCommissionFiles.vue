<template>
  <section v-if="files.length" class="rcf-strip" aria-label="קבצי נפרעים אחרונים">
    <header class="rcf-head">
      <h4 class="rcf-title">קבצי נפרעים אחרונים</h4>
      <span class="rcf-count">{{ files.length }}</span>
    </header>

    <div class="rcf-row">
      <article
        v-for="f in files"
        :key="f.id"
        class="rcf-card"
        :style="{ '--brand': brand(f).color }"
        :title="`${f.filename} · פתח השוואה`"
        role="button"
        tabindex="0"
        @click="$emit('select', f)"
        @keydown.enter="$emit('select', f)"
        @keydown.space.prevent="$emit('select', f)"
      >
        <span class="rcf-badge" :style="{ background: brand(f).color }" aria-hidden="true">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round">
            <path :d="brand(f).iconPath"/>
          </svg>
        </span>

        <div class="rcf-text">
          <div class="rcf-top">
            <span class="rcf-co">{{ brand(f).label || f.company_source || '—' }}</span>
            <span class="rcf-time">· {{ relativeHebrew(f.uploaded_at) }}</span>
          </div>
          <div class="rcf-name">{{ truncate(f.filename, 32) }}</div>
        </div>

        <button
          v-if="f.has_file"
          type="button"
          class="rcf-dl"
          :title="`הורד ${f.filename}`"
          :disabled="downloadingId === f.id"
          @click.stop="download(f)"
        >
          <span v-if="downloadingId === f.id" class="rcf-dl-spinner" aria-hidden="true"></span>
          <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.85" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
        </button>
      </article>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../../api/client.js'
import { useUploadsStore } from '../../stores/uploads.js'
import { brandForLabel } from '../../utils/companyBrand.js'
import { relativeHebrew } from '../../utils/relativeTime.js'

const props = defineProps({
  limit: { type: Number, default: 8 },
})
defineEmits(['select'])

const uploadsStore = useUploadsStore()
const downloadingId = ref(null)

const files = computed(() => {
  const all = uploadsStore.uploads || []
  return all
    .filter((u) => u.file_category === 'commission')
    .slice(0, props.limit)
})

function brand(f) {
  return brandForLabel(f.company_source)
}

function truncate(s, n) {
  if (!s) return ''
  return s.length > n ? s.slice(0, n - 1) + '…' : s
}

async function download(f) {
  if (downloadingId.value) return
  downloadingId.value = f.id
  try {
    // axios via api client carries the bearer token; a plain <a> link wouldn't.
    const res = await api.get(`/uploads/${f.id}/file`, { responseType: 'blob' })
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = f.filename || 'file'
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 0)
  } catch (e) {
    console.warn('download failed', e)
  } finally {
    downloadingId.value = null
  }
}

onMounted(() => {
  if (!uploadsStore.uploads.length) uploadsStore.fetchUploads()
})
</script>

<style scoped>
.rcf-strip {
  font-family: 'Heebo', sans-serif;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.rcf-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 0 4px;
}
.rcf-title {
  margin: 0;
  font-size: 12.5px;
  font-weight: 800;
  color: var(--text-muted);
  letter-spacing: 0.1px;
}
.rcf-count {
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 10.5px;
  font-weight: 700;
  color: var(--text-muted);
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  padding: 1px 7px;
  border-radius: 999px;
}

.rcf-row {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  padding: 4px 2px 6px;
  scrollbar-width: none;
}
.rcf-row::-webkit-scrollbar { display: none; }

.rcf-card {
  position: relative;
  flex-shrink: 0;
  width: 230px;
  height: 64px;
  display: grid;
  grid-template-columns: 36px 1fr 30px;
  align-items: center;
  gap: 10px;
  padding: 8px 10px 8px 12px;
  background: #fff;
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  box-shadow: 0 2px 6px rgba(17, 12, 6, 0.04);
  transition: transform 0.18s, box-shadow 0.18s, border-color 0.18s;
  overflow: hidden;
  cursor: pointer;
  outline: none;
}
.rcf-card:focus-visible {
  border-color: var(--primary, #F57C00);
  box-shadow: 0 0 0 3px rgba(245, 124, 0, 0.18);
}
/* Cadence-style 3px brand stripe on the leading edge */
.rcf-card::before {
  content: '';
  position: absolute;
  inset-block: 0;
  inset-inline-start: 0;
  width: 3px;
  background: var(--brand);
}
/* Top-edge orange wash on hover — matches the rest of the workspace */
.rcf-card::after {
  content: '';
  position: absolute;
  inset: 0 0 auto 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, #F57C00, transparent);
  opacity: 0;
  transition: opacity 0.18s;
}
.rcf-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(17, 12, 6, 0.06);
  border-color: var(--text-muted);
}
.rcf-card:hover::after { opacity: 1; }

.rcf-badge {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  color: #fff;
  flex-shrink: 0;
  box-shadow: 0 3px 8px rgba(17, 12, 6, 0.14), inset 0 -1px 0 rgba(0, 0, 0, 0.18);
}

.rcf-text { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.rcf-top { display: flex; align-items: baseline; gap: 4px; min-width: 0; }
.rcf-co {
  font-size: 12.5px;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -0.1px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.rcf-time {
  font-size: 11px;
  color: var(--text-muted);
  white-space: nowrap;
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
}
.rcf-name {
  font-size: 11px;
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  color: var(--text-muted);
  letter-spacing: 0.2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.rcf-dl {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  color: var(--text-muted);
  cursor: pointer;
  text-decoration: none;
  flex-shrink: 0;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}
.rcf-dl:hover:not(:disabled) {
  background: rgba(245, 124, 0, 0.08);
  color: var(--primary-deep, #E65100);
  border-color: rgba(245, 124, 0, 0.32);
}
.rcf-dl:disabled { cursor: default; opacity: 0.7; }
.rcf-dl-spinner {
  width: 13px;
  height: 13px;
  border: 1.6px solid rgba(245, 124, 0, 0.25);
  border-top-color: var(--primary-deep, #E65100);
  border-radius: 50%;
  animation: rcfSpin 0.8s linear infinite;
}
@keyframes rcfSpin { to { transform: rotate(360deg); } }
</style>
