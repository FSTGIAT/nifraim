<template>
  <div class="rfp-wrap">
    <!-- Trigger: history / open-folder icon -->
    <button
      ref="btnEl"
      type="button"
      class="rfp-trigger"
      :class="{ active: open }"
      :aria-expanded="open"
      aria-haspopup="dialog"
      title="קבצי נפרעים אחרונים"
      @click="toggle"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>
        <path d="M12 11v4M10 13h4" />
      </svg>
      <span v-if="files.length" class="rfp-trigger-count ltr-number">{{ files.length }}</span>
    </button>

    <Teleport to="body">
      <Transition name="rfp-pop">
        <div
          v-if="open"
          class="rfp-pop"
          role="dialog"
          aria-label="קבצי נפרעים אחרונים"
          :style="popStyle"
        >
          <header class="rfp-head">
            <span class="rfp-title">היסטוריית קבצים</span>
            <span class="rfp-sub">3 האחרונים</span>
          </header>

          <div v-if="files.length" class="rfp-list">
            <button
              v-for="f in files"
              :key="f.id"
              type="button"
              class="rfp-item"
              :style="{ '--brand': brand(f).color }"
              :title="`${f.filename} · פתח השוואה`"
              @click="pick(f)"
            >
              <span class="rfp-badge" :style="{ background: brand(f).color }" aria-hidden="true">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round">
                  <path :d="brand(f).iconPath" />
                </svg>
              </span>
              <span class="rfp-text">
                <span class="rfp-top">
                  <span class="rfp-co">{{ brand(f).label || f.company_source || '—' }}</span>
                  <span class="rfp-time">· {{ relativeHebrew(f.uploaded_at) }}</span>
                </span>
                <span class="rfp-name">{{ truncate(f.filename, 30) }}</span>
              </span>
              <svg class="rfp-go" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M15 18l-6-6 6-6" />
              </svg>
            </button>
          </div>

          <div v-else class="rfp-empty">אין קבצי נפרעים אחרונים</div>
        </div>
      </Transition>
    </Teleport>

    <!-- Click-away scrim (transparent) -->
    <Teleport to="body">
      <div v-if="open" class="rfp-scrim" @click="open = false"></div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useUploadsStore } from '../../stores/uploads.js'
import { brandForLabel } from '../../utils/companyBrand.js'
import { relativeHebrew } from '../../utils/relativeTime.js'

const emit = defineEmits(['select'])

const uploadsStore = useUploadsStore()
const open = ref(false)
const btnEl = ref(null)
const popStyle = ref({})

// Last 3 commission files — the "history" the user asked to surface.
const files = computed(() => {
  const all = uploadsStore.uploads || []
  return all.filter((u) => u.file_category === 'commission').slice(0, 3)
})

function brand(f) {
  return brandForLabel(f.company_source)
}

function truncate(s, n) {
  if (!s) return ''
  return s.length > n ? s.slice(0, n - 1) + '…' : s
}

function position() {
  const el = btnEl.value
  if (!el) return
  const r = el.getBoundingClientRect()
  const width = 280
  // Anchor below the trigger; align the popover's right edge to the trigger
  // (RTL-friendly) but clamp inside the viewport.
  let left = r.right - width
  left = Math.max(12, Math.min(left, window.innerWidth - width - 12))
  popStyle.value = {
    top: `${Math.round(r.bottom + 8)}px`,
    left: `${Math.round(left)}px`,
    width: `${width}px`,
  }
}

function toggle() {
  open.value = !open.value
  if (open.value) {
    position()
    if (!uploadsStore.uploads.length) uploadsStore.fetchUploads()
  }
}

function pick(f) {
  emit('select', f)
  open.value = false
}

function onWindowChange() {
  if (open.value) position()
}

onMounted(() => {
  if (!uploadsStore.uploads.length) uploadsStore.fetchUploads()
  window.addEventListener('resize', onWindowChange)
  window.addEventListener('scroll', onWindowChange, true)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', onWindowChange)
  window.removeEventListener('scroll', onWindowChange, true)
})
</script>

<style scoped>
.rfp-wrap {
  position: relative;
  flex-shrink: 0;
}

/* Trigger button */
.rfp-trigger {
  position: relative;
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-sm);
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 0.2s var(--transition), color 0.2s var(--transition),
    border-color 0.2s var(--transition), transform 0.2s var(--transition);
}
.rfp-trigger:hover {
  color: var(--primary-deep);
  border-color: var(--primary);
  background: var(--primary-light);
  transform: translateY(-1px);
}
.rfp-trigger.active {
  color: var(--primary-deep);
  border-color: var(--primary);
  background: var(--primary-light);
  box-shadow: var(--shadow-glow);
}
.rfp-trigger-count {
  position: absolute;
  top: -5px;
  inset-inline-end: -5px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  display: grid;
  place-items: center;
  font-size: 10px;
  font-weight: 800;
  color: #fff;
  background: var(--primary);
  border-radius: 999px;
  box-shadow: 0 0 0 2px var(--card-bg);
}

/* Popover */
.rfp-scrim {
  position: fixed;
  inset: 0;
  z-index: 1009;
  background: transparent;
}
.rfp-pop {
  position: fixed;
  z-index: 1010;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: 10px;
  font-family: 'Heebo', sans-serif;
  direction: rtl;
}

.rfp-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 4px 6px 8px;
}
.rfp-title {
  font-size: 13px;
  font-weight: 800;
  color: var(--text);
}
.rfp-sub {
  font-size: 10.5px;
  font-weight: 700;
  color: var(--text-muted);
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  padding: 1px 7px;
  border-radius: 999px;
}

.rfp-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.rfp-item {
  position: relative;
  display: grid;
  grid-template-columns: 34px 1fr 16px;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 10px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  cursor: pointer;
  text-align: start;
  font-family: inherit;
  overflow: hidden;
  transition: transform 0.16s var(--transition), box-shadow 0.16s var(--transition),
    border-color 0.16s var(--transition), background 0.16s var(--transition);
}
.rfp-item::before {
  content: '';
  position: absolute;
  inset-block: 0;
  inset-inline-start: 0;
  width: 3px;
  background: var(--brand);
}
.rfp-item:hover {
  transform: translateX(-2px);
  background: var(--glass-hover);
  border-color: var(--primary);
  box-shadow: var(--shadow-sm);
}
.rfp-item:hover .rfp-go { color: var(--primary-deep); transform: translateX(-2px); }

.rfp-badge {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  color: #fff;
  box-shadow: 0 3px 8px rgba(17, 12, 6, 0.14), inset 0 -1px 0 rgba(0, 0, 0, 0.18);
}
.rfp-text { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.rfp-top { display: flex; align-items: baseline; gap: 4px; min-width: 0; }
.rfp-co {
  font-size: 12.5px;
  font-weight: 800;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.rfp-time {
  font-size: 10.5px;
  color: var(--text-muted);
  white-space: nowrap;
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
}
.rfp-name {
  font-size: 10.5px;
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.rfp-go {
  color: var(--text-muted);
  transition: color 0.16s var(--transition), transform 0.16s var(--transition);
}

.rfp-empty {
  padding: 18px 12px;
  text-align: center;
  font-size: 12.5px;
  color: var(--text-muted);
}

/* Pop transition — scale+fade from the trigger */
.rfp-pop-enter-active { transition: opacity 0.18s var(--transition), transform 0.18s var(--transition); }
.rfp-pop-leave-active { transition: opacity 0.12s ease-in, transform 0.12s ease-in; }
.rfp-pop-enter-from,
.rfp-pop-leave-to {
  opacity: 0;
  transform: translateY(-6px) scale(0.97);
}

@media (prefers-reduced-motion: reduce) {
  .rfp-trigger,
  .rfp-item,
  .rfp-go,
  .rfp-pop-enter-active,
  .rfp-pop-leave-active { transition: none; }
  .rfp-item:hover,
  .rfp-trigger:hover { transform: none; }
}
</style>
