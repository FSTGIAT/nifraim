<template>
  <div class="upload-card" :class="statusClass">
    <div class="upload-icon">
      <svg v-if="isComplete" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
        <polyline points="22 4 12 14.01 9 11.01"/>
      </svg>
      <svg v-else width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
        <line x1="16" y1="13" x2="8" y2="13"/>
        <line x1="16" y1="17" x2="8" y2="17"/>
        <polyline points="10 9 9 9 8 9"/>
      </svg>
    </div>

    <div class="upload-body">
      <div class="upload-filename" :title="fileName">{{ fileName }}</div>
      <div class="upload-bar">
        <div class="upload-bar-fill" :class="{ 'upload-bar-fill--indeterminate': stage === 'extracting' }" :style="{ transform: `translateX(${barTranslate}%)` }"></div>
      </div>
      <div class="upload-meta">
        <span v-if="stage === 'uploading'" class="ltr-number">
          {{ formatBytes(uploadedSize) }} / {{ formatBytes(fileSize) }}
        </span>
        <span v-else class="upload-stage-label">
          <template v-if="isComplete">{{ formatBytes(fileSize) }} · נשמר</template>
          <template v-else-if="stage === 'extracting'">{{ formatBytes(fileSize) }} · ניתוח AI (יכול לקחת עד דקה)</template>
          <template v-else>{{ formatBytes(fileSize) }}</template>
        </span>
        <span class="upload-pct">
          <template v-if="isComplete">הושלם</template>
          <template v-else-if="stage === 'extracting'"><span class="ltr-number">{{ Math.round(progress) }}%</span></template>
          <template v-else><span class="ltr-number">{{ Math.round(progress) }}%</span></template>
        </span>
      </div>
    </div>

    <button
      v-if="!isComplete && cancelable"
      type="button"
      class="upload-cancel"
      :aria-label="'בטל העלאה'"
      @click="$emit('cancel')"
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <line x1="18" y1="6" x2="6" y2="18"/>
        <line x1="6" y1="6" x2="18" y2="18"/>
      </svg>
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  fileName: { type: String, required: true },
  fileSize: { type: Number, default: 0 },
  progress: { type: Number, default: 0 },
  stage: { type: String, default: 'uploading' }, // 'uploading' | 'extracting' | 'complete' | 'error'
  cancelable: { type: Boolean, default: true },
})
defineEmits(['cancel'])

const isComplete = computed(() => props.stage === 'complete' || props.progress >= 100)
const statusClass = computed(() => {
  if (props.stage === 'error') return 'upload-card--error'
  if (isComplete.value) return 'upload-card--complete'
  return 'upload-card--uploading'
})

const uploadedSize = computed(() => (props.fileSize * Math.min(props.progress, 100)) / 100)
const barTranslate = computed(() => -(100 - Math.min(props.progress, 100)))

function formatBytes(bytes) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`
}
</script>

<style scoped>
.upload-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  max-width: 440px;
  padding: 12px 14px;
  background: var(--card-bg);
  border: 1px solid var(--glass-border);
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  overflow: hidden;
  animation: card-in 0.25s ease-out;
}

.upload-card--complete {
  border-color: var(--green, #2e7d32);
}

.upload-card--error {
  border-color: var(--red, #c62828);
}

.upload-icon {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  color: var(--primary);
}

.upload-card--complete .upload-icon {
  color: var(--green, #2e7d32);
}

.upload-body {
  flex: 1 1 auto;
  min-width: 0;
}

.upload-filename {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.upload-bar {
  position: relative;
  height: 6px;
  margin-top: 8px;
  background: var(--bg);
  border-radius: 999px;
  overflow: hidden;
}

.upload-bar-fill {
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, var(--primary-deep), var(--primary));
  border-radius: 999px;
  transition: transform 0.25s ease-out;
}

/* Extracting phase: tasteful shimmer to signal "work is still happening
   on the server" even though the fill itself moves slowly. */
.upload-bar-fill--indeterminate::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.55) 50%,
    transparent 100%
  );
  animation: upload-shimmer 1.4s infinite linear;
}

@keyframes upload-shimmer {
  from { transform: translateX(-100%); }
  to { transform: translateX(100%); }
}

.upload-card--complete .upload-bar-fill {
  background: var(--green, #2e7d32);
}

.upload-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 4px;
  font-size: 11px;
  color: var(--text-muted);
  gap: 8px;
}

.upload-stage-label {
  flex: 1 1 auto;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.upload-pct {
  font-weight: 600;
  flex: 0 0 auto;
}

.upload-cancel {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: var(--text-muted);
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}

.upload-cancel:hover {
  background: var(--red-light, rgba(220, 38, 38, 0.1));
  color: var(--red, #c62828);
}

.ltr-number {
  direction: ltr;
  unicode-bidi: isolate;
}

@keyframes card-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
