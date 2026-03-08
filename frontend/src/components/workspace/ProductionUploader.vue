<template>
  <div class="production-uploader">
    <div
      data-tour="production-uploader"
      class="drop-zone"
      :class="{ dragging: isDragging, uploading: productionStore.uploading, 'has-file': hasFiles }"
      @dragover.prevent="handleDragOver"
      @dragleave="handleDragLeave"
      @drop.prevent="handleDrop"
      @click="openFilePicker"
    >
      <div v-if="productionStore.uploading" class="upload-progress">
        <div class="progress-top">
          <div class="loader">
            <div class="loader-ring"></div>
            <div class="loader-ring delay"></div>
          </div>
          <span class="progress-text">{{ uploadStageLabel }}</span>
          <span class="progress-hint">{{ uploadStageHint }}</span>
        </div>

        <!-- Progress bar -->
        <div class="progress-bar-track">
          <div class="progress-bar-fill" :style="{ width: progressBarWidth }"></div>
          <div class="progress-bar-glow" :style="{ width: progressBarWidth }"></div>
        </div>

        <!-- Upload steps -->
        <div class="upload-steps">
          <div class="upload-step" :class="{ active: uploadStage >= 1, done: uploadStage > 1 }">
            <div class="step-icon">
              <svg v-if="uploadStage > 1" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
              <span v-else class="ltr-number">1</span>
            </div>
            <span>העלאת קובץ</span>
          </div>
          <div class="step-line" :class="{ filled: uploadStage > 1 }"></div>
          <div class="upload-step" :class="{ active: uploadStage >= 2, done: uploadStage > 2 }">
            <div class="step-icon">
              <svg v-if="uploadStage > 2" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
              <span v-else class="ltr-number">2</span>
            </div>
            <span>ניתוח עמודות</span>
          </div>
          <div class="step-line" :class="{ filled: uploadStage > 2 }"></div>
          <div class="upload-step" :class="{ active: uploadStage >= 3 }">
            <div class="step-icon">
              <span class="ltr-number">3</span>
            </div>
            <span>שמירת נתונים</span>
          </div>
        </div>

        <span v-if="uploadPercent > 0 && uploadStage === 1" class="progress-percent ltr-number">{{ uploadPercent }}%</span>
        <span v-if="uploadStage >= 2" class="progress-wait-hint">קבצים גדולים עשויים לקחת עד דקה</span>
      </div>
      <div v-else class="upload-prompt">
        <div class="icon-container">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
        </div>
        <h3>העלאת קובץ פרודוקציה</h3>
        <p>גרור קובץ Excel לכאן או לחץ לבחירה</p>
        <div class="format-badges">
          <span class="format-badge">.xlsx</span>
          <span class="format-badge">.xls</span>
        </div>
      </div>
      <div class="drop-zone-glow"></div>
    </div>
    <input
      ref="fileInputRef"
      type="file"
      accept=".xlsx,.xls"
      @change="handleFileInputChange"
      style="display: none"
    />

    <!-- File card preview -->
    <Transition name="slide-down">
      <div v-if="hasFiles && !productionStore.uploading" class="file-card-list">
        <div class="file-card">
          <div class="file-card-icon" :class="fileDetails[0].extension">
            <span class="file-ext-label ltr-number">.{{ fileDetails[0].extension }}</span>
          </div>
          <div class="file-card-info">
            <span class="file-card-name">{{ fileDetails[0].name }}</span>
            <span class="file-card-size ltr-number">{{ fileDetails[0].size }}</span>
          </div>
          <button class="file-card-remove" @click.stop="clearFiles" title="הסר">&times;</button>
        </div>
        <button class="upload-btn" @click.stop="uploadFile">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          העלה קובץ
        </button>
      </div>
    </Transition>

    <div class="options-row">
      <label class="toggle-label">
        <div class="toggle" :class="{ on: needPassword }">
          <input type="checkbox" v-model="needPassword" />
          <div class="toggle-track"><div class="toggle-thumb"></div></div>
        </div>
        <span>קובץ מוצפן</span>
      </label>
    </div>

    <Transition name="slide-down">
      <div class="password-field" v-if="needPassword">
        <input type="password" v-model="password" placeholder="סיסמת הקובץ..." dir="ltr" />
      </div>
    </Transition>

    <Transition name="fade">
      <p class="error-msg" v-if="error">{{ error }}</p>
    </Transition>
  </div>
</template>

<script setup>
import { inject, watch, ref, computed } from 'vue'
import { useProductionStore } from '../../stores/production.js'
import { useFileUpload } from '../../composables/useFileUpload.js'

const productionStore = useProductionStore()

const {
  files, isDragging, needPassword, password, error,
  hasFiles, fileDetails, fileInputRef,
  openFilePicker, addFiles, clearFiles,
  handleDrop, handleDragOver, handleDragLeave,
  handleFileInputChange,
} = useFileUpload({ multiple: false })

// Upload progress tracking
const uploadPercent = ref(0)
const uploadStage = ref(0) // 0=idle, 1=uploading, 2=parsing, 3=saving

const uploadStageLabel = computed(() => {
  if (uploadStage.value === 1) return 'מעלה קובץ...'
  if (uploadStage.value === 2) return 'מנתח נתונים ומזהה עמודות...'
  if (uploadStage.value === 3) return 'שומר נתונים במערכת...'
  return 'מעבד...'
})

const uploadStageHint = computed(() => {
  if (uploadStage.value === 1) return 'מעביר את הקובץ לשרת'
  if (uploadStage.value === 2) return 'מזהה פורמט ומפענח עמודות בעברית'
  if (uploadStage.value === 3) return 'כמעט סיימנו!'
  return ''
})

const progressBarWidth = computed(() => {
  if (uploadStage.value === 1) return Math.min(uploadPercent.value, 95) + '%'
  if (uploadStage.value === 2) return '70%'
  if (uploadStage.value === 3) return '90%'
  return '0%'
})

// Receive files from full-page drop overlay
const droppedFiles = inject('droppedFiles', null)
if (droppedFiles) {
  watch(droppedFiles, (val) => {
    if (val && val.length > 0) {
      addFiles(val)
    }
  })
}

async function uploadFile() {
  if (!hasFiles.value) return
  error.value = ''
  uploadPercent.value = 0
  uploadStage.value = 1
  try {
    await productionStore.uploadProduction(
      files.value[0],
      needPassword.value ? password.value : null,
      (progressEvent) => {
        if (progressEvent.total) {
          uploadPercent.value = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        }
        // When upload is done (100%), switch to parsing stage
        if (uploadPercent.value >= 100) {
          uploadStage.value = 2
          // Simulate transition to stage 3 after a delay (backend is parsing + saving)
          setTimeout(() => {
            if (productionStore.uploading) {
              uploadStage.value = 3
            }
          }, 3000)
        }
      }
    )
    clearFiles()
  } catch (e) {
    error.value = productionStore.error || 'שגיאה בהעלאת הקובץ'
  } finally {
    uploadStage.value = 0
    uploadPercent.value = 0
  }
}
</script>

<style scoped>
.production-uploader {
  max-width: 520px;
  margin: 0 auto;
}

.drop-zone {
  position: relative;
  border: 1.5px dashed var(--primary-light);
  border-radius: var(--radius-lg);
  padding: 56px 32px;
  text-align: center;
  cursor: pointer;
  transition: all 0.4s var(--transition);
  background: var(--card-bg);
  overflow: hidden;
}

.drop-zone.has-file {
  padding: 32px;
}

.drop-zone-glow {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: radial-gradient(circle at 50% 50%, var(--primary-light), transparent 70%);
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.4s;
}

.drop-zone:hover .drop-zone-glow,
.drop-zone.dragging .drop-zone-glow {
  opacity: 1;
}

.drop-zone:hover,
.drop-zone.dragging {
  border-color: var(--primary-light);
  transform: translateY(-4px);
  box-shadow: 0 20px 60px var(--primary-light), 0 0 0 1px var(--primary-light);
}

.drop-zone.uploading {
  pointer-events: none;
  border-color: var(--primary-light);
}

.icon-container {
  width: 64px;
  height: 64px;
  margin: 0 auto 20px;
  background: linear-gradient(135deg, var(--primary-light), rgba(34, 211, 238, 0.1));
  border: 1px solid var(--primary-light);
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--primary);
  transition: all 0.3s var(--transition);
}

.drop-zone:hover .icon-container {
  transform: scale(1.05);
  box-shadow: 0 8px 24px var(--primary-light);
}

.upload-prompt h3 {
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 6px;
  letter-spacing: -0.3px;
}

.upload-prompt p {
  font-size: 14px;
  color: var(--text-secondary);
}

.format-badges {
  display: flex;
  gap: 6px;
  justify-content: center;
  margin-top: 16px;
}

.format-badge {
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  background: var(--border-subtle);
  border: 1px solid var(--border-subtle);
  font-family: monospace;
  letter-spacing: 0.5px;
}

/* Loader */
.loader {
  width: 48px;
  height: 48px;
  position: relative;
  margin: 0 auto 16px;
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
  inset: 6px;
  border-top-color: var(--accent-cyan);
  animation-duration: 1.5s;
  animation-direction: reverse;
}

.progress-top {
  margin-bottom: 20px;
}

.progress-text {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 4px;
}

.progress-hint {
  font-size: 12px;
  color: var(--text-muted);
}

/* Progress bar */
.progress-bar-track {
  position: relative;
  width: 100%;
  height: 6px;
  background: var(--border-subtle);
  border-radius: 3px;
  margin-bottom: 20px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary), var(--accent-cyan, var(--primary)));
  border-radius: 3px;
  transition: width 0.5s ease;
}

.progress-bar-glow {
  position: absolute;
  top: -2px;
  height: 10px;
  background: linear-gradient(90deg, transparent 80%, var(--primary));
  border-radius: 5px;
  filter: blur(4px);
  opacity: 0.6;
  transition: width 0.5s ease;
  pointer-events: none;
}

/* Upload steps */
.upload-steps {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  margin-bottom: 12px;
}

.upload-step {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
  opacity: 0.5;
  transition: all 0.4s ease;
}

.upload-step.active {
  opacity: 1;
  color: var(--primary);
}

.upload-step.done {
  color: var(--accent-emerald, #10b981);
}

.step-icon {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  background: var(--border-subtle);
  color: var(--text-muted);
  transition: all 0.4s ease;
  flex-shrink: 0;
}

.upload-step.active .step-icon {
  background: var(--primary-light);
  color: var(--primary);
  box-shadow: 0 0 12px var(--primary-light);
  animation: stepPulse 1.5s ease-in-out infinite;
}

.upload-step.done .step-icon {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  box-shadow: none;
  animation: none;
}

@keyframes stepPulse {
  0%, 100% { box-shadow: 0 0 8px var(--primary-light); }
  50% { box-shadow: 0 0 20px var(--primary-light); }
}

.step-line {
  width: 32px;
  height: 2px;
  background: var(--border-subtle);
  margin: 0 8px;
  transition: background 0.4s ease;
  border-radius: 1px;
}

.step-line.filled {
  background: var(--accent-emerald, #10b981);
}

.progress-percent {
  display: block;
  font-size: 22px;
  font-weight: 700;
  color: var(--primary);
  margin-top: 4px;
  letter-spacing: -0.5px;
}

.progress-wait-hint {
  display: block;
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 8px;
  opacity: 0.7;
  animation: fadeInUp 0.5s ease;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 0.7; transform: translateY(0); }
}

/* File card */
.file-card-list {
  margin-top: 12px;
}

.file-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  background: var(--card-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  transition: all 0.25s var(--transition);
}

.file-card:hover {
  border-color: var(--primary-light);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
}

.file-card-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-weight: 700;
}

.file-card-icon.xlsx {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.12), rgba(16, 185, 129, 0.04));
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.file-card-icon.xls {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.12), rgba(59, 130, 246, 0.04));
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.file-ext-label {
  font-size: 10px;
  font-weight: 700;
  font-family: monospace;
  letter-spacing: 0.3px;
  text-transform: uppercase;
}

.xlsx .file-ext-label { color: var(--accent-emerald); }
.xls .file-ext-label { color: var(--primary); }

.file-card-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.file-card-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  direction: ltr;
  text-align: right;
}

.file-card-size {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

.file-card-remove {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 20px;
  font-weight: 700;
  cursor: pointer;
  padding: 0 6px;
  line-height: 1;
  transition: color 0.2s;
  flex-shrink: 0;
}

.file-card-remove:hover { color: var(--red); }

.upload-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  margin-top: 10px;
  padding: 12px;
  border: 1px solid var(--primary-light);
  border-radius: 10px;
  background: linear-gradient(135deg, var(--primary-light), rgba(34, 211, 238, 0.1));
  color: var(--primary);
  font-size: 15px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.3s var(--transition);
}

.upload-btn:hover {
  background: linear-gradient(135deg, var(--primary-light), rgba(34, 211, 238, 0.15));
  transform: translateY(-2px);
  box-shadow: 0 8px 32px var(--primary-light);
}

.upload-btn:active { transform: translateY(0); }

/* Toggle */
.options-row { margin-top: 16px; }

.toggle-label {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-secondary);
}

.toggle { position: relative; }
.toggle input { position: absolute; opacity: 0; pointer-events: none; }

.toggle-track {
  width: 36px;
  height: 20px;
  background: var(--border-subtle);
  border-radius: 10px;
  transition: all 0.3s var(--transition);
  position: relative;
}

.toggle.on .toggle-track { background: var(--primary-light); }

.toggle-thumb {
  width: 16px;
  height: 16px;
  background: var(--text-secondary);
  border-radius: 50%;
  position: absolute;
  top: 2px;
  right: 2px;
  transition: all 0.3s var(--transition);
}

.toggle.on .toggle-thumb {
  right: 18px;
  background: var(--primary);
  box-shadow: 0 0 8px var(--primary-light);
}

/* Password */
.password-field { margin-top: 12px; }

.password-field input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-family: inherit;
  background: var(--bg-surface);
  color: var(--text);
  transition: all 0.25s var(--transition);
}

.password-field input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px var(--primary-glow);
}

/* Transitions */
.slide-down-enter-active { animation: slideDown 0.3s var(--transition); }
.slide-down-leave-active { animation: slideDown 0.2s var(--transition) reverse; }
@keyframes slideDown {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}

.fade-enter-active { animation: fadeIn 0.3s; }
.fade-leave-active { animation: fadeIn 0.2s reverse; }

.error-msg {
  color: var(--red);
  font-size: 13px;
  margin-top: 12px;
  text-align: center;
  padding: 8px 12px;
  background: var(--red-light);
  border-radius: 8px;
  border: 1px solid var(--red-light);
}

.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
  display: inline-block;
}
</style>
