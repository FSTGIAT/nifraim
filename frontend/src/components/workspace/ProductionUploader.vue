<template>
  <div class="production-uploader">
    <!-- Animated orange wave background -->
    <div class="wave-bg">
      <svg class="wave wave-1" viewBox="0 0 1440 320" preserveAspectRatio="none">
        <path d="M0,160L48,170.7C96,181,192,203,288,197.3C384,192,480,160,576,149.3C672,139,768,149,864,170.7C960,192,1056,224,1152,218.7C1248,213,1344,171,1392,149.3L1440,128L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"/>
      </svg>
      <svg class="wave wave-2" viewBox="0 0 1440 320" preserveAspectRatio="none">
        <path d="M0,224L48,213.3C96,203,192,181,288,186.7C384,192,480,224,576,234.7C672,245,768,235,864,213.3C960,192,1056,160,1152,165.3C1248,171,1344,213,1392,234.7L1440,256L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"/>
      </svg>
      <svg class="wave wave-3" viewBox="0 0 1440 320" preserveAspectRatio="none">
        <path d="M0,288L48,272C96,256,192,224,288,218.7C384,213,480,235,576,245.3C672,256,768,256,864,240C960,224,1056,192,1152,186.7C1248,181,1344,203,1392,213.3L1440,224L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"/>
      </svg>
    </div>

    <!-- Content -->
    <div class="uploader-content">
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
          <div class="icon-circle">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
          </div>
          <h3>גרור קובץ Excel או לחץ לבחירה</h3>
        </div>
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
  position: relative;
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* ─── Animated waves ─── */
.wave-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
  border-radius: var(--radius-lg);
  pointer-events: none;
}

.wave {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 200%;
  height: 140px;
}

.wave-1 {
  fill: rgba(245, 124, 0, 0.06);
  animation: waveSlide 12s linear infinite;
}

.wave-2 {
  fill: rgba(245, 124, 0, 0.04);
  animation: waveSlide 16s linear infinite reverse;
  bottom: -8px;
}

.wave-3 {
  fill: rgba(245, 124, 0, 0.025);
  animation: waveSlide 20s linear infinite;
  bottom: -16px;
}

@keyframes waveSlide {
  0%   { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}

/* ─── Content area ─── */
.uploader-content {
  position: relative;
  z-index: 1;
  max-width: 400px;
  width: 100%;
}

/* ─── Drop zone ─── */
.drop-zone {
  position: relative;
  border: 1.5px dashed rgba(245, 124, 0, 0.25);
  border-radius: var(--radius-lg);
  padding: 36px 28px;
  text-align: center;
  cursor: pointer;
  transition: all 0.4s var(--transition);
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(8px);
}

.drop-zone.has-file {
  padding: 28px;
}

.drop-zone:hover {
  border-color: var(--primary);
  background: rgba(255, 255, 255, 0.95);
  transform: translateY(-2px);
  box-shadow: 0 12px 40px rgba(245, 124, 0, 0.1);
}

.drop-zone.dragging {
  border-color: var(--primary);
  background: rgba(255, 243, 224, 0.9);
  transform: translateY(-2px);
  box-shadow: 0 12px 40px rgba(245, 124, 0, 0.15), 0 0 0 3px rgba(245, 124, 0, 0.08);
}

.drop-zone.uploading {
  pointer-events: none;
  border-color: rgba(245, 124, 0, 0.2);
}

/* ─── Upload prompt (empty state) ─── */
.icon-circle {
  width: 48px;
  height: 48px;
  margin: 0 auto 14px;
  background: var(--primary);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  transition: all 0.3s var(--transition);
}

.drop-zone:hover .icon-circle {
  transform: scale(1.08);
  box-shadow: 0 6px 20px rgba(245, 124, 0, 0.3);
}

.upload-prompt h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-secondary);
  letter-spacing: -0.2px;
}

/* ─── Upload progress ─── */
.loader {
  width: 40px;
  height: 40px;
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
  inset: 6px;
  border-top-color: #FF9800;
  animation-duration: 1.5s;
  animation-direction: reverse;
}

.progress-top { margin-bottom: 16px; }

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

.progress-bar-track {
  position: relative;
  width: 100%;
  height: 5px;
  background: var(--border-subtle);
  border-radius: 3px;
  margin-bottom: 16px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary), #FF9800);
  border-radius: 3px;
  transition: width 0.5s ease;
}

.upload-steps {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  margin-bottom: 10px;
}

.upload-step {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--text-muted);
  opacity: 0.5;
  transition: all 0.4s ease;
}

.upload-step.active { opacity: 1; color: var(--primary); }
.upload-step.done { color: var(--accent-emerald, #10b981); }

.step-icon {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  background: var(--border-subtle);
  color: var(--text-muted);
  transition: all 0.4s ease;
  flex-shrink: 0;
}

.upload-step.active .step-icon {
  background: var(--primary-light);
  color: var(--primary);
  box-shadow: 0 0 10px rgba(245, 124, 0, 0.15);
  animation: stepPulse 1.5s ease-in-out infinite;
}

.upload-step.done .step-icon {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  box-shadow: none;
  animation: none;
}

@keyframes stepPulse {
  0%, 100% { box-shadow: 0 0 8px rgba(245, 124, 0, 0.1); }
  50% { box-shadow: 0 0 16px rgba(245, 124, 0, 0.2); }
}

.step-line {
  width: 28px;
  height: 2px;
  background: var(--border-subtle);
  margin: 0 6px;
  transition: background 0.4s ease;
  border-radius: 1px;
}

.step-line.filled { background: var(--accent-emerald, #10b981); }

.progress-percent {
  display: block;
  font-size: 20px;
  font-weight: 700;
  color: var(--primary);
  margin-top: 4px;
}

.progress-wait-hint {
  display: block;
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 6px;
  opacity: 0.7;
  animation: fadeUp 0.5s ease;
}

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 0.7; transform: translateY(0); }
}

/* ─── File card ─── */
.file-card-list { margin-top: 10px; }

.file-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(8px);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  transition: all 0.25s var(--transition);
}

.file-card:hover {
  border-color: rgba(245, 124, 0, 0.2);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.file-card-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
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
  font-size: 9px;
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
  font-size: 12px;
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
  margin-top: 1px;
}

.file-card-remove {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 18px;
  font-weight: 700;
  cursor: pointer;
  padding: 0 4px;
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
  margin-top: 8px;
  padding: 11px;
  border: none;
  border-radius: 10px;
  background: var(--primary);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.3s var(--transition);
}

.upload-btn:hover {
  background: var(--primary-deep);
  transform: translateY(-1px);
  box-shadow: 0 6px 24px rgba(245, 124, 0, 0.25);
}

.upload-btn:active { transform: translateY(0); }

/* ─── Options ─── */
.options-row { margin-top: 14px; }

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
  box-shadow: 0 0 8px rgba(245, 124, 0, 0.2);
}

/* ─── Password ─── */
.password-field { margin-top: 10px; }

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
  box-shadow: 0 0 0 3px rgba(245, 124, 0, 0.1);
}

/* ─── Transitions ─── */
.slide-down-enter-active { animation: slideDown 0.3s var(--transition); }
.slide-down-leave-active { animation: slideDown 0.2s var(--transition) reverse; }
@keyframes slideDown {
  from { opacity: 0; transform: translateY(-6px); }
  to { opacity: 1; transform: translateY(0); }
}

.fade-enter-active { animation: fadeIn 0.3s; }
.fade-leave-active { animation: fadeIn 0.2s reverse; }

.error-msg {
  color: var(--red);
  font-size: 13px;
  margin-top: 10px;
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
